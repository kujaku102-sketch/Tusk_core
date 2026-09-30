import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INTENSITIES = {"LOW", "MID", "HIGH", "MAX"}
SIMPLE_ROLES = {"lead", "skim", "failure_analysis", "handoff"}
MATRIX_ROLES = {"implementation", "review"}
OPTIONAL_MATRIX_ROLES = {"design"}


def load_adapter(name, config_path=None, profile=None):
    if not name or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in name):
        raise ValueError("invalid adapter name")
    config_path = Path(config_path) if config_path else ROOT / name / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1 or config.get("adapter_id") != name:
        raise ValueError("invalid profile config header")
    selected = profile if profile is not None else config.get("active_profile")
    profiles = config.get("profiles")
    if not isinstance(selected, str) or not isinstance(profiles, dict) or selected not in profiles:
        raise ValueError("unknown profile")
    value = profiles[selected]
    if not isinstance(value, str) or not value:
        raise ValueError("invalid profile path")
    path = Path(value)
    if not path.is_absolute():
        path = config_path.parent / path
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_adapter(data)
    if data["adapter_id"] != name:
        raise ValueError("profile adapter mismatch")
    data = dict(data)
    data["selected_profile"] = selected
    return data


def validate_binding(binding):
    required = {"model_alias", "model_env", "reasoning_effort", "access"}
    if set(binding) != required or not all(isinstance(binding[key], str) and binding[key] for key in required):
        raise ValueError("invalid binding")
    if binding["access"] not in {"read_only", "write_limited", "review_only", "transform_only", "orchestrate"}:
        raise ValueError("invalid access")


def validate_adapter(data):
    if data.get("schema_version") not in (1, 2) or not data.get("adapter_id"):
        raise ValueError("invalid adapter header")
    bindings = data.get("bindings", {})
    expected = SIMPLE_ROLES | MATRIX_ROLES
    if data["schema_version"] == 2:
        expected |= OPTIONAL_MATRIX_ROLES
    if set(bindings) != expected:
        raise ValueError("invalid role set")
    for role in SIMPLE_ROLES:
        if role == "lead" and data["schema_version"] == 2 and bindings[role] == {"inherit": "conversation", "access": "orchestrate"}:
            continue
        validate_binding(bindings[role])
    for role in expected - SIMPLE_ROLES:
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
    if bindings["lead"]["access"] != "orchestrate":
        raise ValueError("lead must be orchestrate")
    for role, access in (("implementation", "write_limited"), ("review", "review_only"), ("design", "read_only")):
        if role not in bindings:
            continue
        if any(binding["access"] != access for binding in bindings[role].values()):
            raise ValueError(f"invalid {role} access")


def resolve(adapter, role, intensity=None, config_path=None, profile=None):
    data = load_adapter(adapter, config_path, profile)
    if role in MATRIX_ROLES | OPTIONAL_MATRIX_ROLES:
        if intensity not in INTENSITIES:
            raise ValueError("intensity is required")
        if role not in data["bindings"]:
            raise ValueError("role is not available in this profile")
        binding = dict(data["bindings"][role][intensity])
    elif role in SIMPLE_ROLES:
        if intensity is not None:
            raise ValueError("intensity is not allowed")
        binding = dict(data["bindings"][role])
    else:
        raise ValueError("unknown logical role")
    if binding.get("inherit") == "conversation":
        binding["model"] = None
        binding["reasoning_effort"] = None
    else:
        binding["model"] = os.environ.get(binding["model_env"], binding["model_alias"])
    return {"adapter": data["adapter_id"], "profile": data["selected_profile"], "logical_role": role, "intensity": intensity, **binding}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tusk-role-adapter")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--adapter", choices=["codex", "claude"])
    resolve_parser = commands.add_parser("resolve")
    resolve_parser.add_argument("--adapter", required=True, choices=["codex", "claude"])
    resolve_parser.add_argument("--role", required=True, choices=sorted(SIMPLE_ROLES | MATRIX_ROLES | OPTIONAL_MATRIX_ROLES))
    resolve_parser.add_argument("--intensity", choices=sorted(INTENSITIES))
    for command in (validate, resolve_parser):
        command.add_argument("--config", type=Path)
        command.add_argument("--profile")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            if args.config and not args.adapter:
                raise ValueError("--config requires --adapter")
            names = [args.adapter] if args.adapter else ["codex", "claude"]
            for name in names:
                load_adapter(name, args.config, args.profile)
            print(json.dumps({"status": "ok", "adapters": names}))
            return 0
        print(json.dumps(resolve(args.adapter, args.role, args.intensity, args.config, args.profile), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

