from copy import deepcopy

from . import contracts as c


class ProtocolRegistry:
    def __init__(self):
        self._protocols = {}

    def register(self, kind, *, validate, project=None):
        c.require(type(kind) is str and kind and callable(validate) and
                  (project is None or callable(project)), 'protocol_registration_invalid')
        c.require(kind not in self._protocols, 'protocol_registration_conflict')
        self._protocols[kind] = validate, project

    def validate(self, payload, history):
        c.require(type(payload.get('kind')) is str and payload['kind'] in self._protocols,
                  'protocol_unregistered')
        validator, _ = self._protocols[payload['kind']]
        c.require(validator(deepcopy(payload), deepcopy(history)) is True, 'protocol_rejected')

    def project(self, events):
        result = {}
        for kind, (_, projector) in self._protocols.items():
            selected = [event for event in events if event['type'] == 'CUSTOM' and event['payload'].get('kind') == kind]
            if selected and projector is not None:
                result[kind] = projector(deepcopy(selected))
        return result
