import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INTENSITIES = {"LOW", "MID", "HIGH", "MAX"}
SIMPLE_ROLES = {"lead", "skim", "failure_analysis", "handoff"}
MATRIX_ROLES = {"implementation", "review"}


def load_adapter(name):
    if not name or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in name):
        raise ValueError("invalid adapter name")
    path = ROOT / name / "adapter.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_adapter(data)
    return data


def validate_binding(binding):
    required = {"model_alias", "model_env", "reasoning_effort", "access"}
    if set(binding) != required or not all(isinstance(binding[key], str) and binding[key] for key in required):
        raise ValueError("invalid binding")
    if binding["access"] not in {"read_only", "write_limited", "review_only", "transform_only", "orchestrate"}:
        raise ValueError("invalid access")


def validate_adapter(data):
    if data.get("schema_version") != 1 or not data.get("adapter_id"):
        raise ValueError("invalid adapter header")
    bindings = data.get("bindings", {})
    if set(bindings) != SIMPLE_ROLES | MATRIX_ROLES:
        raise ValueError("invalid role set")
    for role in SIMPLE_ROLES:
        validate_binding(bindings[role])
    for role in MATRIX_ROLES:
        matrix = bindings[role]
        if set(matrix) != INTENSITIES:
            raise ValueError(f"invalid intensity matrix: {role}")
        for binding in matrix.values():
            validate_binding(binding)
    for role in ("skim", "failure_analysis"):
        if bindings[role]["access"] != "read_only":
            raise ValueError(f"{role} must be read_only")
    if bindings["handoff"]["access"] != "transform_only":
        raise ValueError("handoff must be transform_only")


def resolve(adapter, role, intensity=None):
    data = load_adapter(adapter)
    if role in MATRIX_ROLES:
        if intensity not in INTENSITIES:
            raise ValueError("intensity is required")
        binding = dict(data["bindings"][role][intensity])
    elif role in SIMPLE_ROLES:
        if intensity is not None:
            raise ValueError("intensity is not allowed")
        binding = dict(data["bindings"][role])
    else:
        raise ValueError("unknown logical role")
    binding["model"] = os.environ.get(binding["model_env"], binding["model_alias"])
    return {"adapter": data["adapter_id"], "logical_role": role, "intensity": intensity, **binding}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tusk-role-adapter")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--adapter", choices=["codex", "claude"])
    resolve_parser = commands.add_parser("resolve")
    resolve_parser.add_argument("--adapter", required=True, choices=["codex", "claude"])
    resolve_parser.add_argument("--role", required=True, choices=sorted(SIMPLE_ROLES | MATRIX_ROLES))
    resolve_parser.add_argument("--intensity", choices=sorted(INTENSITIES))
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            names = [args.adapter] if args.adapter else ["codex", "claude"]
            for name in names:
                load_adapter(name)
            print(json.dumps({"status": "ok", "adapters": names}))
            return 0
        print(json.dumps(resolve(args.adapter, args.role, args.intensity), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

