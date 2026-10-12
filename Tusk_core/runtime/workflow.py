from copy import deepcopy

from . import contracts as c


def plan_payload(request, source, scope, requirements, *, implementer, owner,
                 intensity='LOW', risk='P0', stage='local', checks=None, protected=False, validate_source=True):
    c.require(type(request) is dict and set(request) == {'source_ref', 'text'} and
              all(type(value) is str and value for value in request.values()), 'request_origin')
    c.require(type(protected) is bool, 'protected_flag_type')
    c.require(intensity in c.PROFILE['intensities'] and risk in c.PROFILE['risks'] and
              stage in ('local', 'release_candidate'), 'route_invalid')
    source = c.checked_path(source, directory=True if validate_source else None)
    c.require(not source.is_relative_to(c.BASE) and not c.BASE.is_relative_to(source), 'source_core_overlap')
    scope = c.paths(scope)
    c.require(type(requirements) is list and requirements, 'requirements_missing')
    for item in requirements:
        c.require(type(item) is dict and set(item) in ({'path', 'contains'}, {'path', 'sha256'}) and
                  item['path'] in scope, 'requirement_shape')
        c.require(all(type(value) is str and value for value in item.values()), 'requirement_value')
    checks = ['static'] if checks is None else checks
    c.require(type(checks) is list and checks and len(checks) == len(set(checks)) and
              all(type(value) is str and value for value in checks), 'checks_invalid')
    independent = protected or risk in ('P2', 'P3', 'P4') or stage == 'release_candidate'
    if stage == 'release_candidate':
        c.require({'diff', 'regression', 'package', 'startup'}.issubset(checks), 'release_checks_missing')
    c.require(type(implementer) is str and implementer and type(owner) is str and owner, 'actor_missing')
    return {'request': deepcopy(request), 'source': str(source), 'scope': scope,
            'requirements': deepcopy(requirements), 'implementer': implementer, 'owner': owner,
            'intensity': intensity, 'risk': risk, 'stage': stage, 'checks': list(checks),
            'independent_review': independent, 'protected': bool(protected)}


def initial_state():
    return {'status': 'new', 'plan': None, 'plan_ref': None, 'result': None, 'result_ref': None,
            'verified': [], 'reviews': {}, 'approvals': [], 'revoked': [], 'failures': [],
            'corrections': 0, 'corrections_total': 0, 'generation': 0, 'work_id': None,
            'launches': 0, 'execution_seconds': 0, 'pending': None,
            'checkpoint': None, 'restore': None, 'development_failures': 0}


def reduce(history):
    state = initial_state()
    for event in history:
        kind, payload = event['type'], event['payload']
        if kind in ('PLAN', 'RECOVERY', 'SUCCESSOR'):
            corrections = state['corrections'] if kind == 'SUCCESSOR' else 0
            state.update(status='planned', plan=payload['plan'], plan_ref=event['event_hash'],
                         result=None, result_ref=None, verified=[], reviews={}, approvals=[],
                         restore=None, generation=event['generation'], work_id=event['work_id'],
                         corrections=corrections)
            if kind == 'PLAN':
                state['checkpoint'] = event
        elif kind == 'OPEN':
            state['status'] = 'running'
        elif kind == 'RESULT':
            state.update(status='result', result=payload['snapshot'], result_ref=event['event_hash'],
                         verified=[], reviews={key: value for key, value in state['reviews'].items() if key == 'design'})
        elif kind == 'VERIFY':
            if payload['purpose'] == 'acceptance':
                if payload['passed']:
                    state['verified'].append(payload['check'])
                else:
                    state['status'] = 'stopped'
                    state['failures'].append({'ref': event['event_hash'], 'reason': payload['reason'],
                                              'generation': event['generation'], 'phase': 'post_result'})
            elif not payload['passed']:
                state['development_failures'] += 1
                state['failures'].append({'ref': event['event_hash'], 'reason': payload['reason'],
                                          'generation': event['generation'], 'phase': 'development'})
                if state['development_failures'] >= c.PROFILE['limits']['max_development_failures']:
                    state['status'] = 'stopped'
        elif kind == 'REVIEW':
            if payload['accepted']:
                state['reviews'][payload['phase']] = event
            else:
                state['status'] = 'stopped'
                state['failures'].append({'ref': event['event_hash'], 'reason': 'review_rejected',
                                          'generation': event['generation'], 'phase': payload['phase']})
        elif kind == 'APPROVAL':
            state['approvals'].append(event)
        elif kind == 'REVOKE':
            state['revoked'].append(payload['approval_ref'])
        elif kind == 'STOP':
            state['status'] = 'stopped'
            state['failures'].append({'ref': event['event_hash'], 'reason': payload['reason'],
                                      'generation': event['generation'],
                                      'phase': 'post_result' if state['result'] else 'pre_result'})
        elif kind == 'CLOSE':
            state['status'] = 'completed' if payload['disposition'] == 'completed' else 'abandoned'
            if payload['disposition'] == 'completed':
                state['checkpoint'] = event
        elif kind == 'CORRECTION':
            state['corrections'] += 1
            state['corrections_total'] += 1
            state.update(status='planned', result=None, result_ref=None, verified=[], reviews={}, approvals=[],
                         plan=payload['plan'], plan_ref=event['event_hash'])
        elif kind == 'CHECKPOINT':
            state['checkpoint'] = event
        elif kind == 'RESTORE':
            state['restore'] = event
        elif kind == 'RESERVE':
            state['launches'] += 1
            state['execution_seconds'] += payload['timeout_seconds']
            state['pending'] = event
        elif kind == 'RECEIPT':
            state['pending'] = None
            if not payload['completed']:
                state['status'] = 'stopped'
                state['failures'].append({'ref': event['event_hash'], 'reason': payload['reason'],
                                          'generation': event['generation'], 'phase': 'execution'})
    return state


def checkpoint_snapshot(event):
    return event['payload']['baseline'] if event['type'] == 'PLAN' else event['payload']['snapshot']
