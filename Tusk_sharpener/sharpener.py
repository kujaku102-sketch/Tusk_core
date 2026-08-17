from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "SHARPENER-CHECKS.json").read_text(encoding="utf-8"))
CODE_RE = re.compile(r"^\|\s*([FM]\d{3})\s*\|\s*([^|]+?)\s*\|")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def issue(check_id, code, detail, path=None, repairable=False, severity="error"):
    return {"check_id": check_id, "code": code, "severity": severity,
            "path": str(path) if path else None, "detail": detail,
            "repairable": repairable}


def safe_relative(root: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe path")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlink path")
    return current


def check_authority(root: Path):
    output = []
    path = root / "AUTHORITY-MAP.json"
    try:
        data = load_json(path)
    except Exception as exc:
        return [issue("reference_consistency", "AUTHORITY_MAP_INVALID", str(exc), path)]
    concepts, owners = set(), {}
    for row in data.get("authorities", []):
        concept, canonical = row.get("concept"), row.get("canonical")
        if not concept or not canonical:
            output.append(issue("reference_consistency", "AUTHORITY_ENTRY_INVALID", "concept/canonical is required", path))
            continue
        if concept in concepts:
            output.append(issue("authority_conflicts", "AUTHORITY_CONCEPT_DUPLICATE", concept, path))
        concepts.add(concept)
        for value in [canonical, *row.get("redirects", [])]:
            if value in owners and owners[value] != concept:
                output.append(issue("authority_conflicts", "AUTHORITY_PATH_CONFLICT", f"{value}: {owners[value]} / {concept}", path))
            owners[value] = concept
            try:
                target = safe_relative(root, value)
            except ValueError as exc:
                output.append(issue("reference_consistency", "AUTHORITY_PATH_UNSAFE", str(exc), value))
                continue
            if not target.is_file():
                output.append(issue("reference_consistency", "AUTHORITY_REFERENCE_MISSING", value, target))
    return output


def check_runtime_scope(root: Path):
    output = []
    if (root / "MD_SCOPE_RULES.md").exists():
        output.append(issue("reference_consistency", "RETIRED_SCOPE_AUTHORITY_ACTIVE", "MD_SCOPE_RULES.md must remain retired", root / "MD_SCOPE_RULES.md"))
    authority_path = root / "AUTHORITY-MAP.json"
    try:
        authority = load_json(authority_path)
        if any(row.get("concept") == "markdown_scope" for row in authority.get("authorities", [])):
            output.append(issue("authority_conflicts", "RETIRED_SCOPE_AUTHORITY_MAPPED", "markdown_scope", authority_path))
    except Exception:
        pass
    active_documents = [root / "AGENTS.md", root.parent / "AGENTS.md"]
    extensions_root = root.parent / "extensions"
    if extensions_root.is_dir():
        for extension in extensions_root.iterdir():
            if not extension.is_dir() or extension.is_symlink():
                continue
            agent = extension / "AGENTS.md"
            manifest = extension / "EXTENSION-MANIFEST.json"
            active_documents.append(agent)
            if not manifest.is_file():
                output.append(issue("manifest_catalog", "EXTENSION_MANIFEST_MISSING", extension.name, manifest))
                continue
            try:
                contract = load_json(manifest).get("runtime_scope", {})
            except Exception as exc:
                output.append(issue("manifest_catalog", "EXTENSION_MANIFEST_INVALID", str(exc), manifest))
                continue
            required_sources = {"activation", "current_task", "current_spec", "git_diff", "validated_context_cache"}
            if contract.get("workspace_required") is not True or not required_sources.issubset(set(contract.get("derived_from", []))):
                output.append(issue("manifest_catalog", "RUNTIME_SCOPE_DERIVATION_INVALID", extension.name, manifest))
            if not contract.get("owned_paths") or not contract.get("excluded_paths"):
                output.append(issue("manifest_catalog", "RUNTIME_SCOPE_PATHS_MISSING", extension.name, manifest))
    for document in active_documents:
        if not document.is_file():
            continue
        for line_number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
            if "MD_SCOPE_RULES.md" in line:
                output.append(issue("reference_consistency", "RETIRED_SCOPE_REFERENCE", line.strip(), f"{document}:{line_number}"))
            if "Work Packet" in line and "作らない" not in line:
                output.append(issue("reference_consistency", "RETIRED_WORK_PACKET_REFERENCE", line.strip(), f"{document}:{line_number}"))
    return output


def check_manifest_catalog(root: Path):
    output = []
    manifest_path = root / "DISTRIBUTION-MANIFEST.json"
    try:
        manifest = load_json(manifest_path)
    except Exception as exc:
        return [issue("manifest_catalog", "MANIFEST_INVALID", str(exc), manifest_path)]
    seen = set()
    for row in manifest.get("managed_files", []):
        value = row.get("path", "")
        if value in seen:
            output.append(issue("manifest_catalog", "MANIFEST_PATH_DUPLICATE", value, manifest_path))
            continue
        seen.add(value)
        try:
            target = safe_relative(root, value)
        except ValueError as exc:
            output.append(issue("manifest_catalog", "MANIFEST_PATH_UNSAFE", str(exc), value))
            continue
        if not target.is_file():
            output.append(issue("manifest_catalog", "MANIFEST_FILE_MISSING", value, target))
        elif sha256(target) != row.get("sha256"):
            output.append(issue("manifest_catalog", "MANIFEST_SHA_MISMATCH", value, target, True))
    catalog_path = root / "extensions.json"
    try:
        catalog = load_json(catalog_path)
        ids, entries = set(), set()
        for row in catalog.get("extensions", []):
            extension_id, entry = row.get("id"), row.get("entry")
            if not extension_id or not entry:
                output.append(issue("manifest_catalog", "CATALOG_ENTRY_INVALID", "id/entry is required", catalog_path))
            if extension_id in ids or entry in entries:
                output.append(issue("manifest_catalog", "CATALOG_ENTRY_DUPLICATE", f"{extension_id}: {entry}", catalog_path))
            ids.add(extension_id)
            entries.add(entry)
    except Exception as exc:
        output.append(issue("manifest_catalog", "CATALOG_INVALID", str(exc), catalog_path))
    return output


def check_error_codes(root: Path):
    path = root / "ERROR_CODES.md"
    if not path.is_file():
        return [issue("error_codes", "ERROR_REGISTRY_MISSING", "ERROR_CODES.md", path)]
    codes, names, output = set(), set(), []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = CODE_RE.match(line)
        if not match:
            continue
        code, name = match.group(1), match.group(2).strip().casefold()
        if code in codes:
            output.append(issue("error_codes", "ERROR_CODE_DUPLICATE", code, f"{path}:{line_number}"))
        if name in names:
            output.append(issue("error_codes", "ERROR_NAME_DUPLICATE", name, f"{path}:{line_number}"))
        codes.add(code)
        names.add(name)
    if not codes:
        output.append(issue("error_codes", "ERROR_REGISTRY_EMPTY", "no F/M registry rows", path))
    return output


def check_test_map(root: Path):
    path = root / "TEST-MAP.json"
    try:
        data = load_json(path)
    except Exception as exc:
        return [issue("test_map", "TEST_MAP_INVALID", str(exc), path)]
    output, patterns = [], set()
    for row in data.get("focused_rules", []):
        for pattern in row.get("patterns", []):
            if pattern in patterns:
                output.append(issue("test_map", "TEST_PATTERN_DUPLICATE", pattern, path))
            patterns.add(pattern)
        for test in row.get("tests", []):
            try:
                target = safe_relative(root, test)
            except ValueError as exc:
                output.append(issue("test_map", "TEST_PATH_UNSAFE", str(exc), test))
                continue
            if not target.is_file():
                output.append(issue("test_map", "TEST_FILE_MISSING", test, target))
    return output


def check_cache(workspace: Path | None):
    if workspace is None:
        return []
    index_path = workspace / "work" / "cache_index.json"
    if not index_path.exists():
        return []
    try:
        data = load_json(index_path)
    except Exception as exc:
        return [issue("cache_freshness", "CACHE_INDEX_INVALID", str(exc), index_path)]
    output = []
    now = datetime.now(timezone.utc).timestamp()
    stale_seconds = CONFIG["cache_stale_days"] * 86400
    for row in data.get("entries", []):
        try:
            target = safe_relative(workspace, row.get("path", ""))
        except ValueError as exc:
            output.append(issue("cache_freshness", "CACHE_PATH_UNSAFE", str(exc), row.get("path")))
            continue
        if not target.is_file():
            output.append(issue("cache_freshness", "CACHE_ENTRY_MISSING", row.get("path"), target))
            continue
        if row.get("sha256") and sha256(target) != row["sha256"]:
            output.append(issue("cache_freshness", "CACHE_SHA_MISMATCH", row.get("path"), target))
        if now - target.stat().st_mtime > stale_seconds:
            output.append(issue("cache_freshness", "CACHE_STALE", row.get("path"), target, severity="warning"))
    return output


def run_check(root: Path, workspace: Path | None):
    root = root.resolve()
    issues = check_authority(root) + check_runtime_scope(root) + check_manifest_catalog(root) + check_error_codes(root) + check_test_map(root) + check_cache(workspace.resolve() if workspace else None)
    hard = [item for item in issues if item["severity"] == "error"]
    return {"schema_version": 1, "status": "healthy" if not hard else "unhealthy",
            "checked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "target": str(root), "checks": [row["id"] for row in CONFIG["checks"]],
            "issues": issues, "repairable_count": sum(bool(item["repairable"]) for item in issues),
            "human_review_count": sum(not item["repairable"] for item in hard)}


def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def atomic_text(path: Path, text: str):
    descriptor, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def repair_manifest(root: Path):
    path = root / "DISTRIBUTION-MANIFEST.json"
    original = path.read_text(encoding="utf-8")
    data = load_json(path)
    seen, resolved = set(), []
    for row in data.get("managed_files", []):
        value = row.get("path", "")
        if value in seen:
            raise ValueError(f"duplicate manifest path: {value}")
        seen.add(value)
        target = safe_relative(root, value)
        if not target.is_file():
            raise ValueError(f"missing manifest file: {value}")
        resolved.append((row, target))
    updated = original
    for row, target in resolved:
        old_hash = row.get("sha256", "")
        new_hash = sha256(target)
        pattern = re.compile(r'("path"\s*:\s*' + re.escape(json.dumps(row["path"])) + r'\s*,\s*"sha256"\s*:\s*")' + re.escape(old_hash) + r'(")')
        updated, count = pattern.subn(r"\g<1>" + new_hash + r"\2", updated, count=1)
        if count != 1:
            raise ValueError(f"manifest row cannot be updated safely: {row['path']}")
    atomic_text(path, updated)
    return {"status": "repaired", "action": "manifest_hashes", "updated": len(resolved)}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sharpener")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check")
    check.add_argument("--target", required=True)
    check.add_argument("--workspace")
    check.add_argument("--output")
    repair = commands.add_parser("repair")
    repair.add_argument("--target", required=True)
    repair.add_argument("--action", choices=["manifest_hashes"], required=True)
    report = commands.add_parser("report")
    report.add_argument("--input", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            result = run_check(Path(args.target), Path(args.workspace) if args.workspace else None)
            if args.output:
                atomic_json(Path(args.output), result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["status"] == "healthy" else 2
        if args.command == "repair":
            result = repair_manifest(Path(args.target).resolve())
            print(json.dumps(result, ensure_ascii=False))
            return 0
        data = load_json(Path(args.input))
        result = {"status": data.get("status"), "needs_human_review": [item for item in data.get("issues", []) if not item.get("repairable")]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not result["needs_human_review"] else 3
    except Exception as exc:
        print(json.dumps({"status": "error", "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
