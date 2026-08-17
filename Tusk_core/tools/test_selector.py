import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path


def load_map(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"schema_version", "component", "focused_rules", "component_tests", "full_tests"}
    if set(data) != required or data["schema_version"] != 1:
        raise ValueError("invalid test map")
    return data


def expand(root, patterns):
    selected = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file():
                selected.add(path.relative_to(root).as_posix())
    return sorted(selected)


def select(root, mapping, stage, changed):
    if stage == "focused":
        selected = set()
        unmatched = []
        for raw in changed:
            path = Path(raw).as_posix().removeprefix("./")
            matches = [rule for rule in mapping["focused_rules"] if any(fnmatch.fnmatch(path, pattern) for pattern in rule["patterns"])]
            if not matches:
                unmatched.append(path)
            for rule in matches:
                selected.update(rule["tests"])
        if unmatched or not selected:
            return "component", expand(root, mapping["component_tests"]), "unmapped_change", unmatched
        return "focused", sorted(selected), "mapped_change", []
    patterns = mapping["component_tests"] if stage == "component" else mapping["full_tests"]
    return stage, expand(root, patterns), "explicit_stage", []


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--map", dest="map_path", type=Path, required=True)
    parser.add_argument("--stage", choices=("focused", "component", "full"), required=True)
    parser.add_argument("--changed", nargs="*", default=[])
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve(strict=True)
    mapping = load_map(args.map_path.resolve(strict=True))
    effective, tests, reason, unmatched = select(root, mapping, args.stage, args.changed)
    exit_code = None
    if args.run:
        exit_code = subprocess.run([sys.executable, "-m", "unittest", *tests], cwd=root).returncode
    result = {"requested_stage": args.stage, "effective_stage": effective, "tests": tests, "reason": reason, "unmatched": unmatched, "exit_code": exit_code}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if exit_code in (None, 0) else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
