from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


KINDS = {"observation", "improvement", "pattern", "authority_proposal"}
SCOPES = {"core", "extension", "project"}
TRANSITIONS = {
    "observed": {"candidate", "rejected"},
    "candidate": {"verified", "rejected", "stale"},
    "verified": {"proposed", "stale"},
    "proposed": {"adopted", "rejected", "stale"},
    "adopted": {"stale"},
    "rejected": {"candidate"},
    "stale": {"candidate", "rejected"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def store_path(workspace: Path) -> Path:
    root = workspace.resolve()
    if not root.is_dir():
        raise FileNotFoundError("workspace does not exist")
    return root / "work" / "inq" / "registry.json"


def load(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "items": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("items"), list):
        raise ValueError("invalid InQ registry")
    return data


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".inq-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def find_item(data: dict, inq_id: str) -> dict:
    matches = [item for item in data["items"] if item.get("inq_id") == inq_id]
    if len(matches) != 1:
        raise ValueError("InQ item not found or duplicated")
    return matches[0]


def add_item(data: dict, args: argparse.Namespace) -> dict:
    if not re.fullmatch(r"INQ-[A-Z0-9][A-Z0-9._-]{2,63}", args.inq_id):
        raise ValueError("invalid InQ id")
    if any(item.get("inq_id") == args.inq_id for item in data["items"]):
        raise ValueError("duplicate InQ id")
    if args.kind not in KINDS or args.scope not in SCOPES or not args.summary.strip():
        raise ValueError("invalid InQ item")
    now = utc_now()
    item = {
        "inq_id": args.inq_id,
        "kind": args.kind,
        "scope": args.scope,
        "summary": args.summary.strip(),
        "target_authority": args.target_authority or None,
        "evidence": list(dict.fromkeys(args.evidence or [])),
        "state": "observed",
        "created_at_utc": now,
        "updated_at_utc": now,
        "reviewed_by": [],
        "decision_reason": None,
    }
    data["items"].append(item)
    return item


def transition_item(data: dict, args: argparse.Namespace, authority_map: dict) -> dict:
    item = find_item(data, args.inq_id)
    current = item["state"]
    if args.state not in TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid transition: {current} -> {args.state}")
    evidence = list(dict.fromkeys(item["evidence"] + (args.evidence or [])))
    reviewers = list(dict.fromkeys(item["reviewed_by"] + (args.reviewer or [])))
    if args.state == "verified" and (not evidence or not reviewers):
        raise ValueError("verified requires evidence and reviewer")
    if args.state == "proposed":
        authorities = {row["canonical"] for row in authority_map.get("authorities", [])}
        if not item.get("target_authority") or item["target_authority"] not in authorities:
            raise ValueError("proposed requires a registered target authority")
    if args.state == "adopted" and (not reviewers or not args.reason):
        raise ValueError("adopted requires reviewer and decision reason")
    item["evidence"] = evidence
    item["reviewed_by"] = reviewers
    item["state"] = args.state
    item["decision_reason"] = args.reason or item.get("decision_reason")
    item["updated_at_utc"] = utc_now()
    return item


def main() -> int:
    parser = argparse.ArgumentParser(prog="tusk-inq")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--authority-map", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add")
    add.add_argument("--id", dest="inq_id", required=True)
    add.add_argument("--kind", required=True, choices=sorted(KINDS))
    add.add_argument("--scope", required=True, choices=sorted(SCOPES))
    add.add_argument("--summary", required=True)
    add.add_argument("--target-authority")
    add.add_argument("--evidence", action="append")
    transition = sub.add_parser("transition")
    transition.add_argument("--id", dest="inq_id", required=True)
    transition.add_argument("--state", required=True, choices=sorted(TRANSITIONS))
    transition.add_argument("--evidence", action="append")
    transition.add_argument("--reviewer", action="append")
    transition.add_argument("--reason")
    sub.add_parser("list")
    args = parser.parse_args()
    store = store_path(args.workspace)
    map_path = args.authority_map.resolve()
    if not map_path.is_file():
        raise FileNotFoundError("authority map not found")
    authority_map = json.loads(map_path.read_text(encoding="utf-8"))
    data = load(store)
    if args.command == "add":
        result = add_item(data, args)
        atomic_write(store, data)
    elif args.command == "transition":
        result = transition_item(data, args, authority_map)
        atomic_write(store, data)
    else:
        result = data
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
