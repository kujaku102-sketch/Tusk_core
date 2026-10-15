from datetime import datetime, timezone
from pathlib import Path
import uuid

from . import contracts as c
from . import authority
from .protocol_registry import ProtocolRegistry
from .storage import Store, publish, writer_lock
from .workflow import checkpoint_snapshot, plan_payload, reduce

_UNSET = object()


class Recorder:
    def __init__(self, state_root, *, family_id=None, protocols=None):
        self.contract = c.verify_core()
        self.root = c.checked_path(state_root)
        c.require(not self.root.is_relative_to(c.BASE) and not c.BASE.is_relative_to(self.root), 'state_core_overlap')
        self.protocols = ProtocolRegistry() if protocols is None else protocols
        c.require(isinstance(self.protocols, ProtocolRegistry), 'registry_type')
        if not self.root.exists():
            self.root.mkdir(parents=True, exist_ok=False)
            self.family = uuid.uuid4().hex if family_id is None else family_id
            marker = {'schema_version': 5, 'family_id': self.family, 'root_identity': c.identity(self.root),
                      'contract_hash': self.contract}
            publish(self.root / 'owner.json', c.canonical(marker))
            (self.root / 'events').mkdir()
            (self.root / 'objects').mkdir()
        else:
            marker = c.loads(c.read_regular(self.root / 'owner.json', 4096))
            self.family = marker['family_id']
            c.require(family_id is None or family_id == self.family, 'family_mismatch')
        c.require(marker == {'schema_version': 5, 'family_id': self.family,
                            'root_identity': c.identity(self.root), 'contract_hash': self.contract}, 'state_ownership')
        c.require(type(self.family) is str and 0 < len(self.family) <= 128, 'family_id')
        self.owner = marker
        self.store = Store(self.root)

    def _check(self):
        c.require(c.verify_core() == self.contract, 'core_contract_changed')
        c.require(c.read_regular(self.root / 'owner.json', 4096) == c.canonical(self.owner) and
                  c.identity(self.root) == self.owner['root_identity'], 'state_owner_changed')

    def events(self):
        self._check()
        history = []
        directory = c.checked_path(self.root / 'events', directory=True)
        for path in sorted(directory.iterdir()):
            if path.name.startswith('.partial-'):
                continue
            raw = c.read_regular(path, c.PROFILE['limits']['max_object_bytes'])
            event = c.loads(raw)
            c.require(raw == c.canonical(event), 'event_raw_bytes_changed')
            c.require(path.name == f"{len(history):06d}-{event['event_hash']}.json", 'event_filename_or_gap')
            c.validate_envelope(event, history, self.contract)
            authority.validate(event, history, self.store, self.protocols)
            history.append(event)
        return history

    def status(self):
        history = self.events()
        state = reduce(history)
        return {**state, 'head': history[-1]['event_hash'] if history else None,
                'sequence': len(history) - 1, 'family_id': self.family,
                'external_protocols': self.protocols.project(history),
                'actor_authentication': 'local_declarations', 'production_sandbox': False}

    def lookup(self, request_id):
        values = [event for event in self.events() if event['request_id'] == request_id]
        return None if not values else values[0]

    def append(self, kind, payload, *, actor, request_id=None, expected_head=_UNSET,
               work_id=None, generation=None):
        before = self.events()
        observed_head = before[-1]['event_hash'] if before else None
        c.require(expected_head is _UNSET or expected_head == observed_head, 'head_conflict')
        request_id = uuid.uuid4().hex if request_id is None else request_id
        with writer_lock(self.root):
            history = self.events()
            state = reduce(history)
            current_head = history[-1]['event_hash'] if history else None
            old = next((event for event in history if event['request_id'] == request_id), None)
            if old is not None:
                c.require(old['type'] == kind and old['payload'] == payload and old['actor'] == actor and
                          (work_id is None or old['work_id'] == work_id) and
                          (generation is None or old['generation'] == generation), 'request_collision')
                return old
            c.require(current_head == observed_head, 'head_conflict')
            event = {'schema_version': 5, 'family_id': self.family, 'sequence': len(history),
                     'previous_hash': current_head, 'event_id': uuid.uuid4().hex, 'request_id': request_id,
                     'work_id': state['work_id'] if work_id is None else work_id,
                     'generation': state['generation'] if generation is None else generation,
                     'type': kind, 'actor': actor,
                     'timestamp': datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z'),
                     'causal_refs': [] if current_head is None else [current_head],
                     'contract_hash': self.contract, 'payload': payload, 'payload_hash': c.hashed(payload)}
            event['event_hash'] = c.hashed(event)
            c.validate_envelope(event, history, self.contract)
            authority.validate(event, history, self.store, self.protocols)
            bound_plan = payload['plan'] if kind == 'PLAN' else state['plan']
            for name in ('baseline', 'snapshot', 'after'):
                if name in payload:
                    c.require(payload[name] == self._capture(bound_plan), 'submitted_snapshot_not_current')
            if kind == 'OPEN':
                origin = next(e for e in reversed(history) if e['type'] in ('PLAN', 'RECOVERY', 'CORRECTION', 'SUCCESSOR'))
                c.require(self._capture(bound_plan) == origin['payload']['baseline'], 'entry_snapshot_changed')
            if kind == 'CORRECTION':
                c.require(self._capture(bound_plan) == state['result'], 'correction_source_changed')
            if (kind == 'CONSUME' or kind == 'VERIFY' and payload['purpose'] == 'acceptance' or
                    kind == 'REVIEW' and payload['phase'] == 'final' or
                    kind == 'APPROVAL' and payload['action'] in ('publish', 'activate')):
                c.require(self._capture(bound_plan) == state['result'], 'submitted_decision_stale_source')
            target = self.root / 'events' / f"{event['sequence']:06d}-{event['event_hash']}.json"
            publish(target, c.canonical(event))
            c.require(c.loads(c.read_regular(target, c.PROFILE['limits']['max_object_bytes'])) == event, 'event_readback')
            return event

    def _capture(self, plan):
        source = c.checked_path(plan['source'], directory=True)
        c.require(not self.root.is_relative_to(source) and not source.is_relative_to(self.root), 'state_source_overlap')
        first = sorted((self.root / 'events').glob('*.json'))
        if first:
            raw = c.read_regular(first[0], c.PROFILE['limits']['max_object_bytes'])
            origin = c.loads(raw)
            c.require(raw == c.canonical(origin), 'event_raw_bytes_changed')
            c.validate_envelope(origin, [], self.contract)
            c.require(c.identity(source) == origin['payload']['baseline']['root_identity'], 'source_root_identity_changed')
        return c.snapshot(source, plan['scope'], self.store.put)

    def start(self, request, source, scope, requirements, *, implementer, owner,
              intensity='LOW', risk='P0', stage='local', checks=None, protected=False,
              work_id=None, request_id=None):
        plan = plan_payload(request, source, scope, requirements, implementer=implementer, owner=owner,
                            intensity=intensity, risk=risk, stage=stage, checks=checks, protected=protected)
        baseline = self._capture(plan)
        return self.append('PLAN', {'plan': plan, 'baseline': baseline}, actor=owner,
                           work_id=uuid.uuid4().hex if work_id is None else work_id, generation=0, request_id=request_id)

    def open(self, *, actor, request_id=None):
        state = self.status()
        origin = next(event for event in reversed(self.events()) if event['type'] in ('PLAN', 'RECOVERY', 'CORRECTION', 'SUCCESSOR'))
        c.require(self._capture(state['plan']) == origin['payload']['baseline'], 'entry_snapshot_changed')
        return self.append('OPEN', {}, actor=actor, request_id=request_id)

    def result(self, *, actor, request_id=None):
        return self.append('RESULT', {'snapshot': self._capture(self.status()['plan'])}, actor=actor, request_id=request_id)

    def verification(self, check, passed, *, actor, purpose='acceptance', report=None, reason='', request_id=None):
        state = self.status()
        current = self._capture(state['plan'])
        if purpose == 'acceptance':
            c.require(state['result'] is not None and current == state['result'], 'verification_stale_source')
        c.require(type(report) is dict and report.get('check') == check and report.get('passed') is passed and
                  report.get('snapshot_sha256') == current['sha256'] and
                  type(report.get('source_ref')) is str and report['source_ref'], 'report_binding')
        report_sha = self.store.put(c.canonical(report))
        return self.append('VERIFY', {'check': check, 'passed': passed, 'purpose': purpose,
                                     'result_ref': state['result_ref'] if purpose == 'acceptance' else None,
                                     'snapshot_sha256': current['sha256'], 'report_sha256': report_sha,
                                     'reason': reason}, actor=actor, request_id=request_id)

    def verify_static(self, *, actor, purpose='acceptance'):
        state = self.status()
        current = self._capture(state['plan'])
        findings = []
        for requirement in state['plan']['requirements']:
            entry = next(item for item in current['files'] if item['path'] == requirement['path'])
            raw = self.store.get(entry['sha256'])
            if 'sha256' in requirement:
                passed = entry['sha256'] == requirement['sha256']
            else:
                try:
                    passed = requirement['contains'] in raw.decode('utf-8')
                except UnicodeError:
                    passed = False
            if not passed:
                findings.append(requirement['path'])
        return self.verification('static', not findings, actor=actor, purpose=purpose,
                                 report={'check': 'static', 'passed': not findings, 'source_ref': 'core:static-conditions',
                                         'snapshot_sha256': current['sha256'], 'failed_paths': findings},
                                 reason='' if not findings else 'requirements_failed')

    def review(self, phase, *, actor, accepted, source_ref, text):
        state = self.status()
        return self.append('REVIEW', {'phase': phase, 'accepted': accepted,
                                     'target_ref': state['plan_ref'] if phase == 'design' else state['result_ref'],
                                     'source_ref': source_ref, 'text': text}, actor=actor)

    def approve(self, action, target, *, actor, source_ref, text, candidate_sha256=None):
        state = self.status()
        return self.append('APPROVAL', {'action': action, 'target': target, 'plan_ref': state['plan_ref'],
                                       'source_ref': source_ref, 'text': text, 'candidate_sha256': candidate_sha256}, actor=actor)

    def revoke(self, approval_ref, *, actor):
        return self.append('REVOKE', {'approval_ref': approval_ref}, actor=actor)

    def stop(self, reason, *, actor):
        return self.append('STOP', {'reason': reason, 'snapshot': self._capture(self.status()['plan'])}, actor=actor)

    def close(self, *, actor, disposition='completed'):
        return self.append('CLOSE', {'disposition': disposition, 'snapshot': self._capture(self.status()['plan'])}, actor=actor)

    def checkpoint(self, *, actor):
        state = self.status()
        return self.append('CHECKPOINT', {'snapshot': self._capture(state['plan']),
                                          'grade': 'verified' if state['status'] == 'completed' else 'baseline'}, actor=actor)

    def correction(self, *, actor):
        state = self.status()
        c.require(state['result'] is not None and self._capture(state['plan']) == state['result'], 'correction_source_changed')
        return self.append('CORRECTION', {'plan': state['plan'], 'baseline': self._capture(state['plan'])}, actor=actor)

    def recovery_plan(self, request):
        state = self.status()
        plan = dict(state['plan'])
        plan['request'] = request
        return plan

    def recover(self, request, approval_ref, *, actor):
        state = self.status()
        plan = self.recovery_plan(request)
        return self.append('RECOVERY', {'plan': plan, 'baseline': self._capture(plan), 'approval_ref': approval_ref,
                                       'failures_sha256': c.hashed(state['failures']),
                                       'corrections_total': state['corrections_total']}, actor=actor,
                           generation=state['generation'] + 1)

    def prepare_restore(self, approval_ref, *, actor, timeout_seconds):
        state = self.status()
        c.require(state['status'] == 'stopped' and state['pending'] is None and state['checkpoint'] is not None,
                  'restore_state')
        checkpoint = state['checkpoint']
        authority.approval(state, approval_ref, 'restore', checkpoint_snapshot(checkpoint)['sha256'])
        c.require(actor == state['plan']['owner'], 'restore_actor')
        c.require(not any(event['type'] == 'RESTORE' and event['payload']['approval_ref'] == approval_ref
                          for event in self.events()), 'approval_used')
        before = self._capture(state['plan'])
        target = checkpoint_snapshot(checkpoint)
        c.require(before['root_identity'] == target['root_identity'] and
                  [(item['path'], item['identity']) for item in before['files']] ==
                  [(item['path'], item['identity']) for item in target['files']], 'restore_identity_changed')
        request = {'checkpoint_ref': checkpoint['event_hash'], 'before_sha256': before['sha256']}
        return self.append('RESERVE', {'action': 'restore', 'request': request,
                                  'request_sha256': c.hashed(request), 'approval_ref': approval_ref,
                                  'timeout_seconds': timeout_seconds, 'snapshot': before}, actor=actor)

    def confirm_restore(self, reservation_ref, *, actor, duration_seconds, report):
        state = self.status()
        pending = state['pending']
        c.require(pending is not None and pending['event_hash'] == reservation_ref and
                  pending['payload']['action'] == 'restore', 'restore_reservation')
        before = pending['payload']['snapshot']
        after = self._capture(state['plan'])
        c.require(c.same_bytes(after, checkpoint_snapshot(state['checkpoint'])) and
                  [(item['path'], item['identity']) for item in before['files']] ==
                  [(item['path'], item['identity']) for item in after['files']], 'restore_failed')
        self.receipt(reservation_ref, actor=actor, completed=True, duration_seconds=duration_seconds, report=report)
        return self.append('RESTORE', {'checkpoint_ref': state['checkpoint']['event_hash'],
                                       'approval_ref': pending['payload']['approval_ref'],
                                       'before': before, 'after': after}, actor=actor)

    def successor(self, *, actor, work_id=None):
        state = self.status()
        current = self._capture(state['plan'])
        last = self.events()[-1]
        c.require(last['type'] in ('CLOSE', 'CHECKPOINT') and
                  c.same_bytes(current, last['payload']['snapshot']), 'successor_source_changed')
        return self.append('SUCCESSOR', {'plan': state['plan'], 'baseline': current,
                                        'failures_sha256': c.hashed(state['failures']),
                                        'corrections_total': state['corrections_total']}, actor=actor,
                           work_id=uuid.uuid4().hex if work_id is None else work_id)

    def reserve(self, request, approval_ref, *, actor, timeout_seconds=10, request_id=None):
        current = self._capture(self.status()['plan'])
        return self.append('RESERVE', {'action': 'execute', 'request': request, 'request_sha256': c.hashed(request),
                                      'approval_ref': approval_ref, 'timeout_seconds': timeout_seconds,
                                      'snapshot': current}, actor=actor, request_id=request_id)

    def receipt(self, reservation_ref, *, actor, completed, duration_seconds, report, reason=''):
        state = self.status()
        c.require(state['pending'] is not None and state['pending']['event_hash'] == reservation_ref, 'receipt_pending')
        report_sha = self.store.put(c.canonical(report))
        return self.append('RECEIPT', {'reservation_ref': reservation_ref,
                                      'request_sha256': state['pending']['payload']['request_sha256'],
                                      'completed': completed, 'duration_seconds': duration_seconds,
                                      'report_sha256': report_sha, 'reason': reason,
                                      'snapshot': self._capture(state['plan'])}, actor=actor)

    def consume_approval(self, approval_ref, action, target, *, actor):
        state = self.status()
        c.require(state['result'] is not None and self._capture(state['plan']) == state['result'], 'decision_source_changed')
        return self.append('CONSUME', {'approval_ref': approval_ref, 'action': action, 'target': target,
                                      'candidate_sha256': state['result']['sha256']}, actor=actor)

    def custom(self, kind, payload, *, actor):
        c.require('kind' not in payload, 'protocol_kind_override')
        return self.append('CUSTOM', {'kind': kind, **payload}, actor=actor)

    def focus(self):
        state = self.status()
        return {'family_id': self.family, 'work_id': state['work_id'], 'generation': state['generation'],
                'failures': state['failures'], 'corrections_total': state['corrections_total'],
                'launches': state['launches'], 'execution_seconds': state['execution_seconds'],
                'checkpoint_ref': None if state['checkpoint'] is None else state['checkpoint']['event_hash'],
                'pending_ref': None if state['pending'] is None else state['pending']['event_hash'],
                'head': state['head']}
