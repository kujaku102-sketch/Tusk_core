from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import unicodedata

from jsonschema import Draft202012Validator, FormatChecker

BASE = Path(__file__).resolve().parents[1]


class ContractError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise ContractError(reason)


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def loads(raw):
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ContractError('nonfinite_json')))
    except (ValueError, UnicodeError) as exc:
        raise ContractError('invalid_json') from exc


def _normal(value):
    if isinstance(value, str):
        require(unicodedata.normalize('NFC', value) == value, 'non_nfc_text')
    elif isinstance(value, dict):
        for key, item in value.items():
            require(type(key) is str, 'invalid_json_key')
            _normal(key)
            _normal(item)
    elif isinstance(value, list):
        for item in value:
            _normal(item)
    elif value is not None:
        require(type(value) in (int, float, bool), 'invalid_json_type')


def canonical(value):
    _normal(value)
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    except (ValueError, UnicodeError) as exc:
        raise ContractError('noncanonical_json') from exc


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def hashed(value):
    return digest(canonical(value))


PROFILE = loads((BASE / 'config/policy-profile.json').read_bytes())
SCHEMA = loads((BASE / 'schemas/contract.schema.json').read_bytes())
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
CONTRACT_FILES = ('POLICY.md', 'config/policy-profile.json', 'schemas/contract.schema.json',
                  'AUTHORITY-MAP.json', 'DISTRIBUTION-MANIFEST.json')


def contract_hash():
    return hashed({name: digest((BASE / name).read_bytes()) for name in CONTRACT_FILES})


def checked_path(value, *, directory=None):
    path = Path(os.path.abspath(value))
    for current in reversed((path, *path.parents)):
        if current.exists() or current.is_symlink():
            info = current.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'path_link_or_reparse')
    if directory is not None:
        require(path.is_dir() if directory else path.is_file(), 'path_type')
    return path


def identity(path):
    info = checked_path(path).stat()
    return [info.st_dev, info.st_ino]


def relative(value):
    require(type(value) is str and value and '\\' not in value and ':' not in value and '\x00' not in value,
            'invalid_relative_path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value and value not in ('.', '..'), 'noncanonical_path')
    for part in path.parts:
        device = part.split('.', 1)[0].upper()
        require(part not in ('.', '..') and not part.endswith((' ', '.')) and
                device not in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                               *(f'LPT{i}' for i in range(1, 10))}, 'unsafe_path')
        require(part.casefold() not in PROFILE['denied_segments'] and not part.casefold().startswith('.env'), 'protected_path')
    require(path.name.casefold() not in PROFILE['denied_names'] and
            path.suffix.casefold() not in PROFILE['denied_suffixes'], 'secret_path')
    return value


def paths(values):
    require(type(values) is list and 0 < len(values) <= PROFILE['limits']['max_scope_files'], 'scope_size')
    result = sorted(relative(value) for value in values)
    require(len({name.casefold() for name in result}) == len(result), 'scope_alias')
    return result


def read_regular(path, maximum):
    path = checked_path(path, directory=False)
    before = path.stat()
    require(before.st_nlink == 1 and stat.S_ISREG(before.st_mode), 'file_alias_or_type')
    require(before.st_size <= maximum, 'file_size')
    with path.open('rb') as handle:
        info = os.fstat(handle.fileno())
        require([info.st_dev, info.st_ino] == identity(path) and info.st_nlink == 1, 'file_identity_changed')
        raw = handle.read(maximum + 1)
        after = os.fstat(handle.fileno())
    require(len(raw) <= maximum and (info.st_size, info.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
            and [after.st_dev, after.st_ino] == identity(path), 'file_changed_during_read')
    return raw


def is_absent(item):
    return item.get('state') == 'absent'


def snapshot(root, scope, store=None):
    root = checked_path(root, directory=True)
    files = []
    for name in paths(scope):
        path = checked_path(root / name)
        require(path.is_relative_to(root), 'scope_escape')
        require(not path.parent.exists() or path.parent.is_dir(), 'path_type')
        if not path.exists():
            files.append({'path': name, 'state': 'absent'})
            continue
        path = checked_path(path, directory=False)
        raw = read_regular(path, PROFILE['limits']['max_file_bytes'])
        sha = digest(raw)
        if store is not None:
            store(raw)
        files.append({'path': name, 'identity': identity(path), 'size': len(raw), 'sha256': sha})
    value = {'root_identity': identity(root), 'files': files}
    return {**value, 'sha256': hashed(value)}


def validate_snapshot(value):
    require(type(value) is dict and set(value) == {'root_identity', 'files', 'sha256'}, 'snapshot_shape')
    require(value['sha256'] == hashed({key: value[key] for key in ('root_identity', 'files')}), 'snapshot_hash')
    require(type(value['root_identity']) is list and len(value['root_identity']) == 2, 'root_identity_shape')
    scope = paths([item['path'] for item in value['files']])
    require(scope == [item['path'] for item in value['files']], 'snapshot_order')
    for item in value['files']:
        if set(item) == {'path', 'state'}:
            require(item['state'] == 'absent', 'snapshot_entry')
            continue
        require(set(item) == {'path', 'identity', 'size', 'sha256'} and type(item['size']) is int and
                0 <= item['size'] <= PROFILE['limits']['max_file_bytes'] and
                type(item['identity']) is list and len(item['identity']) == 2 and
                isinstance(item['sha256'], str) and len(item['sha256']) == 64, 'snapshot_entry')


def same_bytes(left, right):
    def key(item):
        return (item['path'], None, None) if is_absent(item) else (item['path'], item['size'], item['sha256'])
    return [key(item) for item in left['files']] == [key(item) for item in right['files']]


def restore_blocked(before, target):
    present = {item['path'] for item in before['files'] if not is_absent(item)}
    return any(not is_absent(item) and item['path'] not in present for item in target['files'])


def restore_remove(before, target):
    wanted = {item['path'] for item in target['files'] if is_absent(item)}
    return sorted(item['path'] for item in before['files'] if not is_absent(item) and item['path'] in wanted)


def restore_target(target, remove):
    return hashed({'checkpoint_sha256': target['sha256'], 'remove': remove})


def validate_envelope(event, history, expected_contract):
    require(not list(VALIDATOR.iter_errors(event)), 'event_schema')
    payload_schema = {'$ref': '#/$defs/payloads/' + event['type'], '$defs': SCHEMA['$defs']}
    require(not list(Draft202012Validator(payload_schema, format_checker=FormatChecker()).iter_errors(event['payload'])),
            'payload_schema')
    require(event['contract_hash'] == expected_contract, 'contract_changed')
    require(event['sequence'] == len(history) and event['previous_hash'] ==
            (history[-1]['event_hash'] if history else None), 'sequence_or_head')
    require(event['payload_hash'] == hashed(event['payload']), 'payload_hash')
    require(event['event_hash'] == hashed({key: value for key, value in event.items() if key != 'event_hash'}), 'event_hash')
    require(event['causal_refs'] == ([history[-1]['event_hash']] if history else []), 'causal_refs')
    if history:
        require(event['family_id'] == history[0]['family_id'], 'family_changed')
        require(event['event_id'] not in {old['event_id'] for old in history} and
                event['request_id'] not in {old['request_id'] for old in history}, 'duplicate_identity')
    require(len(history) < PROFILE['limits']['max_events'], 'event_budget_exhausted')


def verify_core():
    manifest = loads((BASE / 'DISTRIBUTION-MANIFEST.json').read_bytes())
    require(manifest['schema_version'] == 5, 'distribution_version')
    expected = {item['path']: item for item in manifest['files'] if item['path'].startswith('Tusk_core/')}
    actual = {'Tusk_core/' + file.relative_to(BASE).as_posix() for file in BASE.rglob('*')
              if file.is_file() and '__pycache__' not in file.parts}
    require(actual == set(expected), 'core_file_set')
    for name, item in expected.items():
        raw = read_regular(BASE / name[len('Tusk_core/'):], PROFILE['limits']['max_object_bytes'])
        if name != 'Tusk_core/DISTRIBUTION-MANIFEST.json':
            require(item['sha256'] == digest(raw), 'core_integrity:' + name)
    return contract_hash()
