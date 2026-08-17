from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


CLASSIFICATIONS = (
    "DUPLICATE_AUTHORITY",
    "DUPLICATE_DEFINITION",
    "CONTRACT_CONFLICT",
    "STALE_RULE",
    "STALE_REFERENCE",
    "ORPHAN_SPEC",
    "OVERLAPPING_SCOPE",
    "MACHINE_RULE_IN_MARKDOWN",
    "UNNECESSARY_DOCUMENT",
)


def load_map(root: Path, map_path: Path) -> dict:
    data = json.loads(map_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("authorities"), list):
        raise ValueError("invalid authority map")
    return data


def issue(kind: str, concept: str, file: str, detail: str) -> dict:
    return {"classification": kind, "concept": concept, "file": file, "detail": detail}


def audit(root: Path, data: dict) -> dict:
    issues: list[dict] = []
    concepts: set[str] = set()
    canonicals: dict[str, str] = {}
    redirects: set[str] = set()
    for row in data["authorities"]:
        concept = row.get("concept")
        canonical = row.get("canonical")
        if not isinstance(concept, str) or not concept or not isinstance(canonical, str) or not canonical:
            issues.append(issue("CONTRACT_CONFLICT", str(concept), str(canonical), "authority row is incomplete"))
            continue
        if concept in concepts:
            issues.append(issue("DUPLICATE_AUTHORITY", concept, canonical, "concept is registered more than once"))
        concepts.add(concept)
        if canonical in canonicals:
            issues.append(issue("OVERLAPPING_SCOPE", concept, canonical, f"canonical is also owned by {canonicals[canonical]}"))
        canonicals[canonical] = concept
        if not (root / canonical).is_file():
            issues.append(issue("STALE_REFERENCE", concept, canonical, "canonical file is missing"))
        for redirect in row.get("redirects", []):
            if redirect in redirects or redirect in canonicals:
                issues.append(issue("DUPLICATE_DEFINITION", concept, redirect, "redirect is owned more than once"))
            redirects.add(redirect)
            path = root / redirect
            if not path.is_file():
                issues.append(issue("STALE_REFERENCE", concept, redirect, "redirect file is missing"))
                continue
            text = path.read_text(encoding="utf-8")
            if canonical not in text:
                issues.append(issue("STALE_RULE", concept, redirect, "redirect does not name its canonical authority"))
    return {
        "schema_version": 1,
        "mode": "read_only_audit",
        "classifications": list(CLASSIFICATIONS),
        "authority_count": len(data["authorities"]),
        "issues": issues,
        "ok": not issues,
    }


def creation_gate(root: Path, data: dict, concept: str, candidate: str, independent: bool) -> dict:
    existing = next((row for row in data["authorities"] if row.get("concept") == concept), None)
    if existing:
        return {"decision": "REUSE_EXISTING", "concept": concept, "canonical": existing["canonical"], "candidate": candidate}
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", concept):
        return {"decision": "REJECT", "concept": concept, "candidate": candidate, "reason": "invalid concept id"}
    if Path(candidate).is_absolute() or ".." in Path(candidate).parts or Path(candidate).suffix.lower() != ".md":
        return {"decision": "REJECT", "concept": concept, "candidate": candidate, "reason": "unsafe candidate path"}
    if not independent:
        return {"decision": "REJECT", "concept": concept, "candidate": candidate, "reason": "independent normative concept not confirmed"}
    if (root / candidate).exists():
        return {"decision": "REJECT", "concept": concept, "candidate": candidate, "reason": "candidate already exists but is unregistered"}
    return {"decision": "ALLOW_NEW_AUTHORITY", "concept": concept, "candidate": candidate}


def main() -> int:
    parser = argparse.ArgumentParser(prog="tusk-authority-auditor")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--map", dest="map_path", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("--output", type=Path)
    gate = sub.add_parser("creation-gate")
    gate.add_argument("--concept", required=True)
    gate.add_argument("--candidate", required=True)
    gate.add_argument("--independent-concept", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    map_path = args.map_path.resolve()
    if root not in map_path.parents or not map_path.is_file():
        raise ValueError("authority map must be an existing file below root")
    data = load_map(root, map_path)
    result = audit(root, data) if args.command == "audit" else creation_gate(root, data, args.concept, args.candidate, args.independent_concept)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.command == "audit" and args.output:
        output = args.output.resolve()
        if root not in output.parents:
            raise ValueError("audit output must stay below root")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    if args.command == "audit":
        return 0 if result["ok"] else 2
    return 0 if result["decision"] in {"REUSE_EXISTING", "ALLOW_NEW_AUTHORITY"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
