from . import contracts as c
from .workflow import checkpoint_snapshot, plan_payload, reduce


def distinct(left, right):
    return left.casefold() != right.casefold()


def approval(state, ref, action, target):
    values = [event for event in state['approvals'] if event['event_hash'] == ref]
    c.require(len(values) == 1 and ref not in state['revoked'], 'approval_unavailable')
    value = values[0]['payload']
    c.require(value['action'] == action and value['target'] == target and value['plan_ref'] == state['plan_ref'],
              'approval_binding')
    return values[0]


def validate_plan(value):
    expected = plan_payload(value['request'], value['source'], value['scope'], value['requirements'],
                            implementer=value['implementer'], owner=value['owner'], intensity=value['intensity'],
                            risk=value['risk'], stage=value['stage'], checks=value['checks'], protected=value['protected'],
                            validate_source=False)
    c.require(value == expected, 'plan_shape_or_route')


def validate(event, history, store, registry):
    state = reduce(history)
    kind, payload, actor = event['type'], event['payload'], event['actor']
    plan = state['plan']
    c.require(event['generation'] == state['generation'] and event['work_id'] == state['work_id'] or
              kind in ('PLAN', 'RECOVERY', 'SUCCESSOR'), 'work_generation_binding')
    if kind != 'PLAN':
        c.require(plan is not None, 'plan_missing')
    if state['pending'] is not None:
        c.require(kind in ('RECEIPT', 'STOP'), 'pending_execution_unresolved')
    for name in ('baseline', 'snapshot', 'before', 'after'):
        if name in payload:
            c.validate_snapshot(payload[name])
            bound_plan = payload['plan'] if kind == 'PLAN' else plan
            c.require([item['path'] for item in payload[name]['files']] == bound_plan['scope'], 'snapshot_scope')
            if history:
                c.require(payload[name]['root_identity'] == history[0]['payload']['baseline']['root_identity'],
                          'snapshot_root_identity')
            for item in payload[name]['files']:
                raw = store.get(item['sha256'])
                c.require(len(raw) == item['size'], 'snapshot_object_size')
    if kind == 'PLAN':
        c.require(not history and event['generation'] == 0, 'plan_singleton')
        validate_plan(payload['plan'])
        c.require(actor == payload['plan']['owner'], 'plan_owner')
        c.require([item['path'] for item in payload['baseline']['files']] == payload['plan']['scope'], 'baseline_scope')
    elif kind == 'OPEN':
        c.require(state['status'] == 'planned' and actor == plan['implementer'], 'open_state_or_actor')
        c.require(state['development_failures'] < c.PROFILE['limits']['max_development_failures'], 'development_failure_budget')
        if plan['independent_review']:
            c.require('design' in state['reviews'], 'design_review_required')
        if plan['protected'] or plan['risk'] in ('P2', 'P3', 'P4'):
            c.require(any(e['payload']['action'] == 'work' and e['payload']['target'] == state['plan_ref']
                          and e['event_hash'] not in state['revoked'] for e in state['approvals']), 'work_approval_required')
    elif kind == 'RESULT':
        c.require(state['status'] == 'running' and actor == plan['implementer'], 'result_state_or_actor')
        c.require([item['path'] for item in payload['snapshot']['files']] == plan['scope'], 'result_scope')
    elif kind == 'VERIFY':
        c.require(payload['purpose'] in ('development', 'acceptance') and type(payload['passed']) is bool,
                  'verification_shape')
        c.require(payload['check'] in plan['checks'], 'check_not_required')
        report = store.json(payload['report_sha256'])
        c.require(report.get('check') == payload['check'] and report.get('passed') is payload['passed'] and
                  report.get('snapshot_sha256') == payload['snapshot_sha256'] and
                  type(report.get('source_ref')) is str and report['source_ref'], 'report_binding')
        if payload['purpose'] == 'acceptance':
            c.require(state['status'] == 'result' and payload['result_ref'] == state['result_ref'] and
                      payload['snapshot_sha256'] == state['result']['sha256'], 'verification_result_binding')
            c.require(payload['check'] not in state['verified'], 'verification_duplicate')
            if payload['check'] == 'static':
                findings = []
                for requirement in plan['requirements']:
                    item = next(entry for entry in state['result']['files'] if entry['path'] == requirement['path'])
                    raw = store.get(item['sha256'])
                    if 'sha256' in requirement:
                        passed = item['sha256'] == requirement['sha256']
                    else:
                        try:
                            passed = requirement['contains'] in raw.decode('utf-8')
                        except UnicodeError:
                            passed = False
                    if not passed:
                        findings.append(requirement['path'])
                c.require(payload['passed'] is (not findings), 'static_result_forged')
        else:
            c.require(state['status'] == 'running' and payload['result_ref'] is None, 'development_state')
    elif kind == 'REVIEW':
        c.require(payload['phase'] in ('design', 'final') and type(payload['accepted']) is bool and
                  distinct(actor, plan['implementer']), 'review_role')
        c.require(payload['phase'] not in state['reviews'], 'review_singleton')
        target = state['plan_ref'] if payload['phase'] == 'design' else state['result_ref']
        c.require(target is not None and payload['target_ref'] == target and
                  state['status'] == ('planned' if payload['phase'] == 'design' else 'result'), 'review_binding')
    elif kind == 'APPROVAL':
        c.require(actor == plan['owner'] and payload['plan_ref'] == state['plan_ref'] and
                  payload['action'] in ('work', 'execute', 'restore', 'recovery', 'publish', 'activate') and
                  payload['source_ref'] and payload['text'], 'approval_owner_or_scope')
        c.require(state['status'] not in ('abandoned',), 'approval_terminal')
        if payload['action'] in ('publish', 'activate'):
            c.require(state['status'] == 'completed' and plan['stage'] == 'release_candidate' and
                      payload['candidate_sha256'] == state['result']['sha256'], 'publication_candidate_not_ready')
    elif kind == 'CONSUME':
        c.require(actor == plan['owner'] and state['status'] == 'completed' and
                  payload['action'] in ('publish', 'activate'), 'decision_state')
        decision = approval(state, payload['approval_ref'], payload['action'], payload['target'])
        c.require(decision['payload']['candidate_sha256'] == state['result']['sha256'] and
                  payload['candidate_sha256'] == state['result']['sha256'], 'decision_candidate')
        c.require(not any(e['type'] == 'CONSUME' and e['payload']['approval_ref'] == payload['approval_ref'] for e in history),
                  'approval_used')
    elif kind == 'REVOKE':
        c.require(actor == plan['owner'] and any(e['event_hash'] == payload['approval_ref'] for e in state['approvals'])
                  and payload['approval_ref'] not in state['revoked'], 'revoke_binding')
    elif kind == 'CLOSE':
        c.require(payload['disposition'] in ('completed', 'abandoned'), 'close_disposition')
        c.require(state['status'] not in ('completed', 'abandoned') and actor == plan['owner'], 'close_state_or_actor')
        if payload['disposition'] == 'completed':
            c.require(state['status'] == 'result' and set(state['verified']) == set(plan['checks']), 'checks_incomplete')
            if plan['independent_review']:
                c.require('final' in state['reviews'], 'final_review_required')
            c.require(payload['snapshot']['sha256'] == state['result']['sha256'], 'close_stale_result')
    elif kind == 'STOP':
        exhausted_completed = (state['status'] == 'completed' and
                               state['corrections'] >= c.PROFILE['limits']['max_corrections'] and
                               actor == plan['owner'])
        c.require((state['status'] not in ('completed', 'abandoned') or exhausted_completed) and
                  payload['reason'] and actor in (plan['owner'], plan['implementer']), 'stop_state_or_actor')
    elif kind == 'CHECKPOINT':
        c.require(actor == plan['owner'] and state['status'] in ('planned', 'completed'), 'checkpoint_state')
        c.require(payload['grade'] == ('verified' if state['status'] == 'completed' else 'baseline'), 'checkpoint_grade')
        if state['status'] == 'completed':
            c.require(c.same_bytes(payload['snapshot'], state['result']), 'checkpoint_result')
        else:
            origin = next(e for e in reversed(history) if e['type'] in ('PLAN', 'RECOVERY', 'CORRECTION', 'SUCCESSOR'))
            c.require(c.same_bytes(payload['snapshot'], origin['payload']['baseline']), 'checkpoint_baseline')
    elif kind == 'CORRECTION':
        c.require(state['status'] in ('completed', 'stopped') and state['result'] is not None,
                  'correction_requires_result')
        c.require(any(e['type'] == 'CLOSE' and e['work_id'] == state['work_id'] and
                      e['payload']['disposition'] == 'completed' for e in history), 'correction_requires_acceptance')
        c.require(state['corrections'] < c.PROFILE['limits']['max_corrections'], 'correction_limit')
        validate_plan(payload['plan'])
        c.require(payload['plan'] == plan and actor == plan['owner'], 'correction_scope_changed')
    elif kind == 'RESTORE':
        c.require(state['status'] == 'stopped' and state['checkpoint'] is not None and actor == plan['owner'], 'restore_state')
        checkpoint = state['checkpoint']
        c.require(payload['checkpoint_ref'] == checkpoint['event_hash'], 'restore_checkpoint')
        approval(state, payload['approval_ref'], 'restore', checkpoint_snapshot(checkpoint)['sha256'])
        c.require(not any(e['type'] == 'RESTORE' and e['payload']['approval_ref'] == payload['approval_ref'] for e in history),
                  'approval_used')
        c.require(c.same_bytes(payload['after'], checkpoint_snapshot(checkpoint)), 'restore_readback')
        receipt = history[-1]
        c.require(receipt['type'] == 'RECEIPT' and receipt['payload']['completed'], 'restore_receipt_required')
        reservation = next((e for e in history if e['event_hash'] == receipt['payload']['reservation_ref']), None)
        c.require(reservation is not None and reservation['type'] == 'RESERVE' and
                  reservation['payload']['action'] == 'restore' and
                  reservation['payload']['approval_ref'] == payload['approval_ref'] and
                  reservation['payload']['request']['checkpoint_ref'] == payload['checkpoint_ref'] and
                  reservation['payload']['snapshot'] == payload['before'] and
                  receipt['payload']['snapshot'] == payload['after'], 'restore_execution_binding')
    elif kind == 'RECOVERY':
        c.require(state['status'] == 'stopped' and actor == plan['owner'], 'recovery_state')
        c.require(event['generation'] == state['generation'] + 1 and
                  event['generation'] < c.PROFILE['limits']['max_generations'] and event['work_id'] == state['work_id'],
                  'generation_budget_or_identity')
        validate_plan(payload['plan'])
        c.require(all(payload['plan'][key] == plan[key] for key in plan if key != 'request'), 'recovery_scope_changed')
        c.require(payload['failures_sha256'] == c.hashed(state['failures']) and
                  payload['corrections_total'] == state['corrections_total'], 'failure_history_binding')
        if state['corrections'] >= c.PROFILE['limits']['max_corrections']:
            c.require(state['restore'] is not None and c.same_bytes(payload['baseline'], state['restore']['payload']['after']),
                      'generation_restore_required')
        approval(state, payload['approval_ref'], 'recovery', c.hashed(payload['plan']))
    elif kind == 'SUCCESSOR':
        c.require(state['status'] in ('completed', 'abandoned') and event['work_id'] != state['work_id'] and
                  event['generation'] == state['generation'] and actor == plan['owner'], 'successor_state')
        validate_plan(payload['plan'])
        c.require(payload['plan'] == plan and payload['failures_sha256'] == c.hashed(state['failures']) and
                  payload['corrections_total'] == state['corrections_total'], 'successor_scope_or_history')
    elif kind == 'RESERVE':
        action = payload['action']
        c.require(action in ('execute', 'restore'), 'reservation_action')
        c.require(state['status'] == ('running' if action == 'execute' else 'stopped') and
                  actor == (plan['implementer'] if action == 'execute' else plan['owner']), 'execution_state')
        c.require(state['launches'] < c.PROFILE['limits']['max_launches'], 'launch_budget')
        c.require(type(payload['timeout_seconds']) is int and 0 < payload['timeout_seconds'] <=
                  c.PROFILE['limits']['max_execution_seconds'], 'execution_timeout')
        c.require(state['execution_seconds'] + payload['timeout_seconds'] <=
                  c.PROFILE['limits']['max_family_execution_seconds'], 'execution_time_budget')
        c.require(payload['request_sha256'] == c.hashed(payload['request']), 'execution_request_hash')
        target = payload['request_sha256'] if action == 'execute' else checkpoint_snapshot(state['checkpoint'])['sha256']
        if action == 'execute':
            c.require(payload['request'].get('input_snapshot_sha256') == payload['snapshot']['sha256'], 'execution_input_binding')
        else:
            c.require(payload['request'].get('checkpoint_ref') == state['checkpoint']['event_hash'] and
                      payload['request'].get('before_sha256') == payload['snapshot']['sha256'], 'restore_request_binding')
        approval(state, payload['approval_ref'], action, target)
        c.require(not any(e['type'] == 'RESERVE' and e['payload']['approval_ref'] == payload['approval_ref'] for e in history),
                  'approval_used')
    elif kind == 'RECEIPT':
        pending = state['pending']
        c.require(pending is not None and payload['reservation_ref'] == pending['event_hash'] and
                  actor == (plan['implementer'] if pending['payload']['action'] == 'execute' else plan['owner']),
                  'receipt_reservation')
        c.require(type(payload['completed']) is bool and type(payload['duration_seconds']) in (int, float) and
                  0 <= payload['duration_seconds'] <= pending['payload']['timeout_seconds'], 'receipt_duration')
        c.require(payload['request_sha256'] == pending['payload']['request_sha256'], 'receipt_request')
        store.get(payload['report_sha256'])
        if payload['completed']:
            expected = pending['payload']['snapshot'] if pending['payload']['action'] == 'execute' else checkpoint_snapshot(state['checkpoint'])
            c.require(payload['snapshot'] == expected, 'receipt_input_changed')
    elif kind == 'CUSTOM':
        c.require(state['status'] in ('planned', 'running', 'result'), 'custom_terminal')
        registry.validate(payload, history)
    else:
        raise c.ContractError('unsupported_event')
