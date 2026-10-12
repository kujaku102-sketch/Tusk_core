from . import contracts as c


def request_for(recorder, operation, target):
    c.require(type(operation) is str and operation and type(target) is str and target, 'operation_target')
    state = recorder.status()
    value = recorder._capture(state['plan'])
    return {'operation': operation, 'target': target, 'input_snapshot_sha256': value['sha256']}


def replacement_for(recorder, reservation_ref):
    from .workflow import checkpoint_snapshot
    state = recorder.status()
    pending = state['pending']
    c.require(pending is not None and pending['event_hash'] == reservation_ref and
              pending['payload']['action'] == 'restore', 'restore_reservation')
    value = checkpoint_snapshot(state['checkpoint'])
    return {item['path']: recorder.store.get(item['sha256']) for item in value['files']}
