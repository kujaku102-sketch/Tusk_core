import argparse
import json
import sys

from .contracts import ContractError
from .recorder import Recorder


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read common work records.')
    parser.add_argument('operation', choices=('status', 'focus', 'lookup'))
    parser.add_argument('--state', required=True)
    parser.add_argument('--request-id')
    args = parser.parse_args(argv)
    try:
        from pathlib import Path
        if not Path(args.state).is_dir():
            raise ContractError('state_not_found')
        recorder = Recorder(args.state)
        if args.operation == 'lookup':
            if args.request_id is None:
                raise ContractError('request_id_required')
            value = recorder.lookup(args.request_id)
        else:
            value = getattr(recorder, args.operation)()
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
        return 0
    except (ContractError, OSError, KeyError) as exc:
        print(json.dumps({'error': str(exc), 'completed': False}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
