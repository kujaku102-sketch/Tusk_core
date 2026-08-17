from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath

PROTECTED_TERMS = {"auth", "credential", "secret", "migration", "license", "notice", ".github"}


def normalize_target(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe target: {value}")
    return path.as_posix()


def is_protected(target: str, cache: dict) -> bool:
    lowered = target.casefold()
    if any(term in lowered for term in PROTECTED_TERMS):
        return True
    return any(target == value or target.startswith(value.rstrip("/") + "/") for value in cache.get("protected_paths", []))


def split_groups(targets: list[str], maximum: int = 3) -> list[list[str]]:
    grouped: dict[str, list[str]] = {}
    for target in targets:
        parts = PurePosixPath(target).parts
        key = parts[0] if len(parts) > 1 else "root"
        grouped.setdefault(key, []).append(target)
    buckets: list[list[str]] = [[] for _ in range(min(maximum, len(grouped)))]
    for index, key in enumerate(sorted(grouped)):
        buckets[index % len(buckets)].extend(sorted(grouped[key]))
    return [bucket for bucket in buckets if bucket]


def create_plan(cache: dict, objective: str, targets: list[str], acceptance_test: str) -> dict:
    clean = sorted(set(normalize_target(value) for value in targets))
    if not clean:
        return {"schema_version": 1, "route": "STOP", "reason": "no targets", "slices": []}
    if any(is_protected(value, cache) for value in clean):
        return {"schema_version": 1, "route": "STOP", "reason": "protected scope", "slices": []}
    groups = split_groups(clean)
    route = "DIRECT" if len(groups) == 1 else "SPLIT"
    readable = sorted(set(cache.get("important_files", [])) | set(clean))
    slices = []
    for index, writable in enumerate(groups, 1):
        slices.append({
            "slice_id": f"slice-{index:02d}",
            "objective": objective,
            "readable_paths": readable,
            "writable_paths": writable,
            "input_contract": {"context_cache_git_head": cache.get("git_head")},
            "output_contract": {"schema": "schemas/agent_result.schema.json"},
            "dependencies": [],
            "acceptance_test": acceptance_test,
            "forbidden_changes": ["paths outside writable_paths", "credentials", "destructive migration"],
        })
    return {"schema_version": 1, "route": route, "reason": "responsibility groups", "slices": slices}


def assert_disjoint(slices: list[dict]) -> None:
    owner: dict[str, str] = {}
    for item in slices:
        for path in item["writable_paths"]:
            if path in owner:
                raise ValueError(f"F003 overlapping write scope: {path}")
            owner[path] = item["slice_id"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--targets", nargs="+", required=True)
    parser.add_argument("--acceptance-test", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cache = json.loads(args.cache.read_text(encoding="utf-8"))
    plan = create_plan(cache, args.objective, args.targets, args.acceptance_test)
    assert_disjoint(plan["slices"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"route": plan["route"], "slice_count": len(plan["slices"])}, ensure_ascii=False))
    return 5 if plan["route"] == "STOP" else 0


if __name__ == "__main__":
    raise SystemExit(main())
