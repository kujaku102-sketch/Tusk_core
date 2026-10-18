from copy import deepcopy
import re

from . import contracts as c


OPERATIONS = ('external_app', 'persistent_settings', 'persistent_data', 'migration', 'release', 'distribution',
              'installer', 'update_or_uninstall', 'destructive_or_irreversible', 'security_boundary',
              'broad_user_data')
SURFACES = ('security_boundary', 'authentication', 'secrets', 'distribution_installer', 'destructive_operation',
            'user_data', 'persistent_schema', 'process_stop', 'external_app')
EFFECTS = ('create', 'modify', 'delete', 'read_only')
WRITES = ('create', 'modify', 'delete')
OPERATION_FLOORS = {'persistent_settings': 'P2', 'external_app': 'P3', 'persistent_data': 'P3', 'migration': 'P3',
                    'release': 'P4', 'distribution': 'P4', 'installer': 'P4', 'update_or_uninstall': 'P4',
                    'destructive_or_irreversible': 'P4', 'security_boundary': 'P4', 'broad_user_data': 'P4'}
SURFACE_FLOORS = {'security_boundary': 'P4', 'authentication': 'P4', 'secrets': 'P4', 'distribution_installer': 'P4',
                  'destructive_operation': 'P4', 'user_data': 'P3', 'persistent_schema': 'P3', 'process_stop': 'P3',
                  'external_app': 'P3'}


def _rank(risk):
    return c.PROFILE['risks'].index(risk)


def _flags(value, names):
    return type(value) is dict and set(value) == set(names) and all(type(item) is bool for item in value.values())


def check_classification(scope, value):
    c.require(type(value) is dict and set(value) == {'components', 'paths', 'operations', 'surfaces'},
              'classification_invalid')
    components = value['components']
    c.require(type(components) is list and components and len(components) == len(set(components)) and
              all(type(item) is str and item for item in components), 'classification_invalid')
    paths = value['paths']
    c.require(type(paths) is list and all(type(item) is dict and set(item) == {'path', 'component', 'effect'}
                                          for item in paths) and [item['path'] for item in paths] == scope,
              'classification_invalid')
    c.require(all(item['component'] in components and item['effect'] in EFFECTS for item in paths),
              'classification_invalid')
    c.require(_flags(value['operations'], OPERATIONS) and _flags(value['surfaces'], SURFACES), 'classification_invalid')
    surfaces, operations = value['surfaces'], value['operations']
    c.require(surfaces['external_app'] == operations['external_app'] and
              surfaces['security_boundary'] == operations['security_boundary'] and
              surfaces['destructive_operation'] == operations['destructive_or_irreversible'] and
              (not surfaces['distribution_installer'] or any(
                  operations[key] for key in ('release', 'distribution', 'installer', 'update_or_uninstall'))),
              'classification_conflict')


def check_detected(value):
    c.require(type(value) is dict and set(value) == {'components', 'operations', 'surfaces', 'rules'},
              'classification_invalid')
    c.require(type(value['components']) is list and all(type(item) is str and item for item in value['components']) and
              _flags(value['operations'], OPERATIONS) and _flags(value['surfaces'], SURFACES), 'classification_invalid')
    c.require(type(value['rules']) is list and all(
        type(item) is dict and set(item) == {'kind', 'key', 'rule', 'pattern', 'path'} and
        all(type(part) is str for part in item.values()) for item in value['rules']), 'classification_invalid')


def _glob(pattern):
    out, index = '', 0
    while index < len(pattern):
        if pattern.startswith('**/', index):
            out += '(?:.*/)?'
            index += 3
        elif pattern.startswith('**', index):
            out += '.*'
            index += 2
        elif pattern[index] == '*':
            out += '[^/]*'
            index += 1
        elif pattern[index] == '?':
            out += '[^/]'
            index += 1
        else:
            out += re.escape(pattern[index])
            index += 1
    return out


def _first_segment(path):
    return path.split('/', 1)[0] if '/' in path else '.'


def detect(scope, content):
    """Apply the profile rules to scope paths and bytes (content(path) -> bytes or None). Only raises flags."""
    rules = c.PROFILE['classification_rules']
    c.require(rules['component'] == {'by': 'first_path_segment'}, 'classification_rules_invalid')
    texts = {}
    for path in scope:
        raw = content(path)
        try:
            texts[path] = None if raw is None else raw.decode('utf-8')
        except UnicodeError:
            texts[path] = None
    result = {'components': sorted({_first_segment(path) for path in scope}),
              'operations': {key: False for key in OPERATIONS},
              'surfaces': {key: False for key in SURFACES}, 'rules': []}
    for section, kind, names in (('operations', 'operation', OPERATIONS), ('surfaces', 'surface', SURFACES)):
        for key in names:
            rule = rules[section].get(key)
            if rule is None:
                continue
            for path in scope:
                for pattern in rule.get('path_glob', []):
                    if re.fullmatch(_glob(pattern), path):
                        result[section][key] = True
                        result['rules'].append({'kind': kind, 'key': key, 'rule': 'path_glob',
                                                'pattern': pattern, 'path': path})
                for pattern in rule.get('content', []):
                    if texts[path] is not None and pattern in texts[path]:
                        result[section][key] = True
                        result['rules'].append({'kind': kind, 'key': key, 'rule': 'content',
                                                'pattern': pattern, 'path': path})
    return result


def detect_snapshot(scope, snapshot, get):
    files = {item['path']: item for item in snapshot['files']}
    return detect(scope, lambda path: None if c.is_absent(files[path]) else get(files[path]['sha256']))


def _scope_rank(pairs):
    writes = [component for effect, component in pairs if effect in WRITES]
    if not writes:
        return 0
    if len(set(writes)) > 1:
        return 3
    return 1 if len(writes) == 1 else 2


def compute_floor(classification, detected):
    operations = {key: classification['operations'][key] or detected['operations'][key] for key in OPERATIONS}
    surfaces = {key: classification['surfaces'][key] or detected['surfaces'][key] for key in SURFACES}
    declared = [(item['effect'], item['component']) for item in classification['paths']]
    found = [(item['effect'], _first_segment(item['path'])) for item in classification['paths']]
    rank = max([_scope_rank(declared), _scope_rank(found)] +
               [_rank(OPERATION_FLOORS[key]) for key, flag in operations.items() if flag and key in OPERATION_FLOORS] +
               [_rank(SURFACE_FLOORS[key]) for key, flag in surfaces.items() if flag])
    return c.PROFILE['risks'][rank], any(surfaces.values())


def compute_corrections(classification, detected):
    result = []
    for section, kind, floors, names in (('operations', 'operation', OPERATION_FLOORS, OPERATIONS),
                                         ('surfaces', 'surface', SURFACE_FLOORS, SURFACES)):
        for key in names:
            if detected[section][key] and not classification[section][key]:
                hits = [f"{item['path']}:{item['rule']}:{item['pattern']}" for item in detected['rules']
                        if item['kind'] == kind and item['key'] == key]
                result.append({'rule': f'detected_{kind}:{key}', 'required': floors.get(key, 'P0'),
                               'evidence': '; '.join(hits)})
    return result


def effect_baseline_mismatch(classification, baseline):
    files = {item['path']: item for item in baseline['files']}
    return [item['path'] for item in classification['paths']
            if c.is_absent(files[item['path']]) != (item['effect'] == 'create')]


def effect_result_mismatch(classification, baseline, snapshot):
    before = {item['path']: item for item in baseline['files']}
    after = {item['path']: item for item in snapshot['files']}
    bad = []
    for item in classification['paths']:
        old, new = before[item['path']], after[item['path']]
        if item['effect'] == 'read_only':
            if c.is_absent(old) or c.is_absent(new) or (old['size'], old['sha256']) != (new['size'], new['sha256']):
                bad.append(item['path'])
        elif item['effect'] == 'modify' and c.is_absent(new):
            bad.append(item['path'])
    return bad


def compute_unfulfilled(classification, snapshot):
    after = {item['path']: item for item in snapshot['files']}
    result = []
    for item in classification['paths']:
        absent = c.is_absent(after[item['path']])
        if item['effect'] == 'create' and absent:
            result.append({'path': item['path'], 'effect': 'create', 'message': '無いので作れ'})
        elif item['effect'] == 'delete' and not absent:
            result.append({'path': item['path'], 'effect': 'delete', 'message': '残っているので消せ'})
    return result


def plan_payload(request, source, scope, requirements, *, implementer, owner, classification, detected,
                 intensity='LOW', risk='P0', stage='local', checks=None, validate_source=True):
    c.require(type(request) is dict and set(request) == {'source_ref', 'text'} and
              all(type(value) is str and value for value in request.values()), 'request_origin')
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
    check_classification(scope, classification)
    check_detected(detected)
    floor, protected = compute_floor(classification, detected)
    c.require(_rank(risk) >= _rank(floor), 'risk_below_floor')
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
            'independent_review': independent, 'protected': protected,
            'classification': deepcopy(classification), 'detected': deepcopy(detected), 'floor': floor,
            'corrections': compute_corrections(classification, detected)}


def initial_state():
    return {'status': 'new', 'plan': None, 'plan_ref': None, 'result': None, 'result_ref': None,
            'verified': [], 'reviews': {}, 'approvals': [], 'revoked': [], 'failures': [],
            'corrections': 0, 'corrections_total': 0, 'generation': 0, 'work_id': None,
            'launches': 0, 'execution_seconds': 0, 'pending': None,
            'checkpoint': None, 'restore': None, 'development_failures': 0, 'unfulfilled': []}


def reduce(history):
    state = initial_state()
    for event in history:
        kind, payload = event['type'], event['payload']
        if kind in ('PLAN', 'RECOVERY', 'SUCCESSOR'):
            corrections = state['corrections'] if kind == 'SUCCESSOR' else 0
            state.update(status='planned', plan=payload['plan'], plan_ref=event['event_hash'],
                         result=None, result_ref=None, verified=[], reviews={}, approvals=[],
                         restore=None, generation=event['generation'], work_id=event['work_id'], unfulfilled=[],
                         corrections=corrections)
            if kind == 'PLAN':
                state['checkpoint'] = event
        elif kind == 'OPEN':
            state['status'] = 'running'
        elif kind == 'RESULT':
            state.update(status='result', unfulfilled=payload['unfulfilled'], result=payload['snapshot'], result_ref=event['event_hash'],
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
                         plan=payload['plan'], plan_ref=event['event_hash'], unfulfilled=[])
        elif kind == 'CHECKPOINT':
            state['checkpoint'] = event
        elif kind == 'RESTORE':
            state['restore'] = event
        elif kind == 'RESERVE':
            state['launches'] += 1
            if payload['timeout_seconds'] is not None:
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
