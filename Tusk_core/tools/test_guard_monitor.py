# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, TextIO


FORCE_CODES = {
    "F000", "F001", "F002", "F003", "F004", "F005", "F020", "F021", "F022", "F023", "F024", "F025", "F026",
    "F040", "F041", "F042", "F043", "F044", "F045", "F060", "F061", "F062", "F063", "F064", "F065", "F066",
    "F080", "F081", "F082", "F083", "F084", "F100", "F101", "F102", "F103", "F120", "F121", "F122", "F123",
    "F124", "F140", "F141", "F142", "F160", "F161", "F162", "F163", "F180", "F181", "F182",
}
MINOR_CODES = {
    "M000", "M001", "M002", "M020", "M021", "M040", "M041", "M060", "M061", "M080", "M081", "M100", "M101",
    "M120", "M140", "M141", "M160", "M180",
}
LEGACY_CODES = {
    "STALL_30M": "F021", "LOOP_DETECTED": "F022", "PROCESS_LOST": "F020", "PIPELINE_FATAL": "F026",
    "ARTIFACT_INVALID": "F121", "TRANSLATION_FATAL": "F080", "TRANSLATION_SKIP": "M080", "CACHE_CONFLICT": "M141",
    "STYLE_FALLBACK": "M100", "REVIEW_NEEDED": "M120",
}
REQUIRED_FORCE_CODES = {"F020", "F021", "F022", "F023", "F024", "F025", "F026", "F042", "F120", "F121", "F122", "F123", "F124", "F182"}
REQUIRED_MINOR_CODES = {"M020", "M021", "M040", "M041", "M060", "M061", "M080", "M120", "M180"}
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
CODE_RE = re.compile(r"[FM][0-1][0-9]{2}\Z")
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}\Z")
# TUSK_* is canonical. IDTASK_* is accepted only while adapters migrate.
MARKER_RE = re.compile(r"^\[(?:TUSK|IDTASK)_(FORCE_STOP|MINOR_ISSUE|PROGRESS)\]\s*(.*)$", re.IGNORECASE)
FIELD_RE = re.compile(r"([A-Za-z_]+)=([^\s]+)")
TIMESTAMP_RE = re.compile(r"(?<!\d)(?:\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?|\d{2}:\d{2}:\d{2}(?:\.\d+)?)(?!\d)")
SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*(?:bearer\s+)?)[^\s,;]+"),
    re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\b\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\b(?:sk|sess|pat)-[A-Za-z0-9_-]{12,}\b"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("ISO-8601 UTC timestamp required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    return parsed.astimezone(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_command_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def command_line_sha256(value: Any) -> str:
    return hashlib.sha256(normalize_command_line(value).encode("utf-8")).hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
            temporary = Path(stream.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def resolved_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def path_is_reparse(path: Path) -> bool:
    try:
        details = os.lstat(path)
    except OSError:
        return False
    return path.is_symlink() or bool(getattr(details, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def path_has_reparse(path: Path, boundary: Path) -> bool:
    current = path.absolute()
    boundary = boundary.absolute()
    while True:
        if current.exists() and path_is_reparse(current):
            return True
        if current == boundary or current.parent == current:
            return False
        current = current.parent


class SafeWriter:
    def __init__(self, primary: Path, fallback: Path, stderr: TextIO | None = None):
        self.primary = primary
        self.fallback = fallback
        self.stderr = stderr or sys.stderr

    def _fallback_path(self, path: Path) -> Path:
        try:
            relative = path.resolve(strict=False).relative_to(self.primary.resolve(strict=False))
        except ValueError:
            relative = Path(path.name)
        return self.fallback / relative

    def _write(self, operation: Callable[[Path], None], path: Path, kind: str) -> Path | None:
        failures: list[str] = []
        for candidate in (path, self._fallback_path(path)):
            try:
                operation(candidate)
                return candidate
            except Exception as exc:
                failures.append(f"{type(exc).__name__}: {exc}")
        self.stderr.write(json.dumps({"status": "writer_failure", "kind": kind, "path": str(path), "errors": failures}, ensure_ascii=False) + "\n")
        self.stderr.flush()
        return None

    def json(self, path: Path, payload: dict[str, Any]) -> Path | None:
        return self._write(lambda target: atomic_json(target, payload), path, "json")

    def jsonl(self, path: Path, payload: dict[str, Any]) -> Path | None:
        return self._write(lambda target: append_jsonl(target, payload), path, "jsonl")

    def text(self, path: Path, value: str) -> Path | None:
        return self._write(lambda target: atomic_text(target, value), path, "text")


def parse_error_registry(path: Path) -> dict[str, Any]:
    force: set[str] = set()
    minor: set[str] = set()
    legacy: dict[str, str] = {}
    section = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == "### 強制停止":
            section = "force"
            continue
        if line == "### 軽度問題":
            section = "minor"
            continue
        if line.startswith("## 7. 既存コード互換表"):
            section = "legacy"
            continue
        if not line.startswith("|"):
            continue
        cells = [item.strip().strip("`") for item in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if section in {"force", "minor"} and CODE_RE.fullmatch(cells[0]):
            if len(cells) < 3 or not cells[1] or not cells[2]:
                raise ValueError("registry row requires code, name, condition")
            (force if section == "force" else minor).add(cells[0])
        elif section == "legacy" and re.fullmatch(r"[A-Z][A-Z0-9_]+", cells[0]) and CODE_RE.fullmatch(cells[1]):
            legacy[cells[0]] = cells[1]
    if not REQUIRED_FORCE_CODES <= force or not REQUIRED_MINOR_CODES <= minor:
        raise ValueError("ERROR_CODES.md lacks required Tusk Core codes")
    if force & minor or any(target not in force | minor for target in legacy.values()):
        raise ValueError("ERROR_CODES.md registry compatibility mismatch")
    if not set(LEGACY_CODES) <= set(legacy):
        raise ValueError("ERROR_CODES.md lacks required compatibility entries")
    return {"force": force, "minor": minor, "legacy": legacy}


def validate_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    if not RUN_ID_RE.fullmatch(args.run_id) or ".." in args.run_id:
        raise ValueError("invalid run_id")
    if args.poll_seconds not in range(1, 61) or args.stall_seconds != 1800 or args.repeat_threshold < 1:
        raise ValueError("invalid fixed monitor options")
    path_args = [args.workspace, args.allowed_output_root, args.output_dir, args.done_file, args.test_contract, args.process_registry, args.error_registry]
    if not all(item.is_absolute() for item in path_args) or any(not item.is_absolute() for item in args.log_path):
        raise ValueError("absolute paths required")
    workspace = args.workspace.resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError("workspace directory required")
    root = args.allowed_output_root.resolve(strict=False)
    output = args.output_dir.resolve(strict=False)
    done = args.done_file.resolve(strict=False)
    contract = args.test_contract.resolve(strict=False)
    registry = args.process_registry.resolve(strict=False)
    error_registry = args.error_registry.resolve(strict=False)
    fallback = workspace / "work" / "guard_fallback" / args.run_id
    expected = root / args.run_id
    if not resolved_within(root, workspace) or output != expected / "guard" or done.parent != expected or contract.parent != expected or registry.parent != expected:
        raise ValueError("strict run directory layout required")
    if error_registry != workspace / "ERROR_CODES.md":
        raise ValueError("ERROR_CODES.md canonical path required")
    for item in [root, output, done, contract, registry, error_registry, fallback, *args.log_path]:
        if not resolved_within(item, workspace) or path_has_reparse(item, workspace):
            raise ValueError(f"path outside workspace or through reparse point: {item}")
    for source in args.log_path:
        if resolved_within(source, output) or resolved_within(source, fallback):
            raise ValueError("monitor output cannot be a log source")
    if output.exists():
        entries = list(output.iterdir())
        if entries and not (len(entries) == 1 and entries[0].name == "guard_lock.json"):
            raise ValueError("output_dir already exists or is not empty")
    return workspace, root, output, done, fallback


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def stable_load_json(path: Path) -> dict[str, Any]:
    before = path.stat()
    if before.st_size <= 0:
        raise ValueError("empty JSON file")
    value = load_json(path)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("JSON file changed while reading")
    return value


def validate_contract(path: Path, run_id: str) -> dict[str, Any]:
    contract = stable_load_json(path)
    required = {
        "schema_version", "run_id", "started_at_utc", "required_check_ids", "expected_exit_codes", "minor_total_units",
        "required_artifacts", "require_counts", "require_id_set_sha256",
    }
    if contract.get("schema_version") != 1 or contract.get("run_id") != run_id or not required <= contract.keys():
        raise ValueError("invalid test contract")
    started = parse_utc(contract["started_at_utc"])
    if started > datetime.now(timezone.utc):
        raise ValueError("contract start time is in the future")
    checks = contract["required_check_ids"]
    exits = contract["expected_exit_codes"]
    artifacts = contract["required_artifacts"]
    if not isinstance(contract["minor_total_units"], int) or isinstance(contract["minor_total_units"], bool) or contract["minor_total_units"] <= 0:
        raise ValueError("invalid minor_total_units")
    if not isinstance(checks, list) or not checks or len(set(checks)) != len(checks) or not all(isinstance(item, str) and item for item in checks):
        raise ValueError("invalid required_check_ids")
    if not isinstance(exits, list) or not exits or len(set(exits)) != len(exits) or not all(isinstance(item, int) and not isinstance(item, bool) for item in exits):
        raise ValueError("invalid expected_exit_codes")
    if not isinstance(artifacts, list) or not artifacts or len(set(artifacts)) != len(artifacts) or not all(isinstance(item, str) and Path(item).is_absolute() for item in artifacts):
        raise ValueError("invalid required_artifacts")
    if not isinstance(contract["require_counts"], bool) or not isinstance(contract["require_id_set_sha256"], bool):
        raise ValueError("invalid conditional evidence flags")
    contract["_started_epoch"] = started.timestamp()
    contract["_sha256"] = sha256_file(path)
    return contract


def validate_registry(path: Path, run_id: str) -> list[dict[str, Any]]:
    registry = stable_load_json(path)
    if registry.get("schema_version") != 1 or registry.get("run_id") != run_id or not isinstance(registry.get("processes"), list):
        raise ValueError("invalid process registry")
    seen: set[int] = set()
    validated: list[dict[str, Any]] = []
    for item in registry["processes"]:
        required = {"pid", "role", "create_time", "executable_path", "command_line_sha256"}
        if not isinstance(item, dict) or not required <= item.keys() or item.get("role") not in {"supervisor", "worker"}:
            raise ValueError("invalid process identity")
        if not isinstance(item["pid"], int) or isinstance(item["pid"], bool) or item["pid"] <= 0 or item["pid"] in seen:
            raise ValueError("invalid or duplicate process PID")
        if not isinstance(item["create_time"], (str, int, float)) or isinstance(item["create_time"], bool) or not isinstance(item["executable_path"], str) or not Path(item["executable_path"]).is_absolute():
            raise ValueError("invalid process identity fields")
        if not isinstance(item["command_line_sha256"], str) or not SHA256_RE.fullmatch(item["command_line_sha256"]):
            raise ValueError("invalid command line hash")
        normalized = dict(item)
        normalized["create_time"] = canonical_create_time(item["create_time"])
        validated.append(normalized)
        seen.add(item["pid"])
    return validated


def validate_luna_task(args: argparse.Namespace, run_dir: Path) -> dict[str, Any] | None:
    if not args.notify_codex_cli:
        return None
    if args.codex_model != "gpt-5.6-luna" or args.codex_reasoning_effort != "low" or not 1000 <= args.luna_log_limit_chars <= 12000:
        raise ValueError("fixed Luna contract mismatch")
    if args.codex_cli_timeout_seconds <= 0 or not args.luna_thread_id or args.luna_task_file is None:
        raise ValueError("verified Luna task contract required")
    if not args.luna_task_file.is_absolute() or path_has_reparse(args.luna_task_file, args.workspace):
        raise ValueError("absolute non-reparse Luna task path required")
    task_path = args.luna_task_file.resolve(strict=False)
    if task_path.parent != run_dir or task_path.name != "luna_task.json":
        raise ValueError("luna_task.json must be in the run directory")
    task = stable_load_json(task_path)
    required = {"schema_version", "run_id", "task_id", "policy", "evidence"}
    if task.get("schema_version") != 1 or not required <= task.keys() or task.get("run_id") != args.run_id or task.get("task_id") != args.luna_thread_id:
        raise ValueError("invalid Luna task identity")
    if task.get("policy") != args.luna_task_policy or not isinstance(task.get("evidence"), str) or not task["evidence"]:
        raise ValueError("invalid Luna task evidence")
    if task["policy"] == "new_task":
        parse_utc(task.get("created_at_utc"))
    elif task["policy"] == "verified_cleared_task":
        parse_utc(task.get("cleared_at_utc"))
        if task.get("clear_verified") is not True:
            raise ValueError("Luna clear verification required")
    else:
        raise ValueError("invalid Luna task policy")
    return task


def parse_marker(line: str, run_id: str) -> dict[str, str] | None:
    match = MARKER_RE.match(line.strip())
    if not match:
        return None
    values = dict(FIELD_RE.findall(match.group(2)))
    if values.get("run_id") != run_id:
        return None
    values["kind"] = match.group(1).upper()
    values["raw_line"] = line
    return values


def normalize_code(code: str, registry: dict[str, Any] | None = None) -> str:
    legacy = registry["legacy"] if registry else LEGACY_CODES
    return legacy.get(code.upper(), code.upper())


def parse_event(line: str, run_id: str, registry: dict[str, Any]) -> dict[str, str] | None:
    if MARKER_RE.match(line.strip()):
        return parse_marker(line, run_id)
    marker = parse_marker(line, run_id)
    if marker is not None:
        return marker
    for legacy, code in registry["legacy"].items():
        if re.search(rf"(?<![A-Z0-9_]){re.escape(legacy)}(?![A-Z0-9_])", line, re.IGNORECASE):
            kind = "FORCE_STOP" if code.startswith("F") else "MINOR_ISSUE"
            return {
                "kind": kind, "code": code, "component": "legacy", "step": "legacy", "target": f"legacy:{legacy}",
                "reason": line, "detail": line, "raw_line": line, "legacy": "true",
            }
    return None


def validate_issue(marker: dict[str, str], registry: dict[str, Any] | None = None) -> tuple[str, str | None]:
    force = registry["force"] if registry else FORCE_CODES
    minor = registry["minor"] if registry else MINOR_CODES
    code = normalize_code(marker.get("code", ""), registry)
    kind = marker.get("kind", "")
    if kind == "FORCE_STOP":
        if code not in force:
            return code, "unregistered_code_or_severity_mismatch"
        if marker.get("legacy") != "true" and any(not marker.get(field) for field in ("component", "step", "reason")):
            return code, "force_marker_required_field_missing"
        return code, None
    if kind == "MINOR_ISSUE":
        if code not in minor:
            return code, "unregistered_code_or_severity_mismatch"
        if marker.get("legacy") != "true" and any(not marker.get(field) for field in ("component", "step", "target", "detail")):
            return code, "minor_marker_required_field_missing"
        return code, None
    return code, "invalid_issue_kind"


def validate_progress(marker: dict[str, str]) -> bool:
    if any(not marker.get(field) for field in ("component", "step", "current", "total")):
        return False
    if not marker["current"].isdigit() or (marker["total"] != "unknown" and not marker["total"].isdigit()):
        return False
    return marker["total"] == "unknown" or int(marker["current"]) <= int(marker["total"])


def normalize_repetition_text(value: str) -> str:
    return " ".join(TIMESTAMP_RE.sub("<TIME>", value).split())


def issue_fingerprint(marker: dict[str, str]) -> str:
    message = marker.get("reason") or marker.get("detail") or marker.get("raw_line", "")
    return "|".join((marker.get("component", ""), marker.get("step", ""), marker.get("target", ""), normalize_repetition_text(message)))


def minor_threshold_reached(unique_targets: int, event_count: int, total_units: int) -> bool:
    return unique_targets >= (total_units + 4) // 5 or event_count >= 50


def _walk_files(source: Path, excluded: list[Path], workspace: Path) -> Iterable[Path]:
    if path_is_reparse(source) or not resolved_within(source, workspace):
        return
    if source.is_file():
        yield source
        return
    if not source.is_dir():
        return
    for current, directories, files in os.walk(source, followlinks=False):
        current_path = Path(current)
        if path_is_reparse(current_path) or not resolved_within(current_path, workspace):
            directories[:] = []
            continue
        directories[:] = [
            name for name in directories
            if not path_is_reparse(current_path / name)
            and resolved_within(current_path / name, workspace)
            and not any(resolved_within(current_path / name, item) for item in excluded)
        ]
        for name in files:
            path = current_path / name
            if not path_is_reparse(path) and resolved_within(path, workspace):
                yield path


def snapshot_logs(paths: Iterable[Path], excluded: Iterable[Path], workspace: Path | None = None) -> dict[Path, dict[str, Any]]:
    excluded_resolved = [item.resolve(strict=False) for item in excluded]
    result: dict[Path, dict[str, Any]] = {}
    for source in paths:
        boundary = workspace.resolve(strict=False) if workspace is not None else (source.parent if source.is_file() else source).resolve(strict=False)
        for path in _walk_files(source, excluded_resolved, boundary):
            resolved = path.resolve(strict=False)
            if any(resolved_within(resolved, item) for item in excluded_resolved):
                continue
            try:
                details = path.stat()
            except OSError:
                continue
            result[path] = {"identity": (details.st_dev, details.st_ino), "offset": details.st_size, "mtime": details.st_mtime, "buffer": b""}
    return result


def read_new_lines(path: Path, cursor: dict[str, Any]) -> tuple[list[str], dict[str, Any], bool]:
    try:
        details = path.stat()
    except OSError:
        return [], cursor, False
    identity = (details.st_dev, details.st_ino)
    rotated = cursor.get("identity") != identity or details.st_size < cursor.get("offset", 0)
    offset = 0 if rotated else cursor.get("offset", 0)
    buffered = b"" if rotated else cursor.get("buffer", b"")
    try:
        with path.open("rb") as stream:
            stream.seek(offset)
            data = buffered + stream.read()
    except OSError:
        return [], cursor, rotated
    pieces = data.split(b"\n")
    complete = pieces[:-1]
    remaining = pieces[-1]
    lines = [item.rstrip(b"\r").decode("utf-8", errors="replace") for item in complete]
    updated = {"identity": identity, "offset": details.st_size, "mtime": details.st_mtime, "buffer": remaining}
    return lines, updated, rotated


def _evidence_path(item: dict[str, Any], started_epoch: float) -> tuple[bool, str]:
    evidence = item.get("evidence")
    if not isinstance(evidence, str) or not Path(evidence).is_absolute():
        return False, "check_evidence_path"
    path = Path(evidence)
    try:
        if not path.is_file() or path.stat().st_mtime < started_epoch:
            return False, "check_evidence_missing_or_stale"
    except OSError:
        return False, "check_evidence_missing_or_stale"
    return True, ""


def validate_done(done_path: Path, contract_path: Path, contract: dict[str, Any], started_epoch: float, contract_sha256: str | None = None) -> tuple[str | None, dict[str, Any]]:
    try:
        done = stable_load_json(done_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return "F122", {"valid": False, "reason": "invalid_or_unstable_done_json"}
    required = {"schema_version", "run_id", "status", "validated_at_utc", "contract_sha256", "target_exit_codes", "success_conditions", "checks", "artifacts"}
    if not required <= done.keys() or done.get("schema_version") != 1 or done.get("run_id") != contract["run_id"] or done.get("status") != "validated":
        return "F122", {"valid": False, "reason": "done_identity_status_or_fields"}
    try:
        validated_at = parse_utc(done["validated_at_utc"])
    except (TypeError, ValueError):
        return "F122", {"valid": False, "reason": "validated_at_utc"}
    if validated_at.timestamp() < started_epoch or validated_at > datetime.now(timezone.utc):
        return "F122", {"valid": False, "reason": "validated_at_range"}
    fixed_sha = contract_sha256 or contract.get("_sha256") or sha256_file(contract_path)
    if sha256_file(contract_path) != fixed_sha or done.get("contract_sha256") != fixed_sha:
        return "F124", {"valid": False, "reason": "contract_sha256"}
    if done.get("target_exit_codes") != contract["expected_exit_codes"] or not isinstance(done.get("success_conditions"), dict) or done["success_conditions"].get("passed") is not True:
        return "F122", {"valid": False, "reason": "success_conditions_or_exit_codes"}
    check_items = done.get("checks")
    if not isinstance(check_items, list) or not check_items or any(not isinstance(item, dict) for item in check_items):
        return "F122", {"valid": False, "reason": "checks_empty_or_invalid"}
    check_map = {item.get("id"): item for item in check_items if isinstance(item.get("id"), str)}
    if len(check_map) != len(check_items) or not set(contract["required_check_ids"]) <= set(check_map):
        return "F122", {"valid": False, "reason": "required_checks"}
    for check_id in contract["required_check_ids"]:
        item = check_map[check_id]
        evidence_ok, evidence_reason = _evidence_path(item, started_epoch)
        if item.get("passed") is not True or not evidence_ok:
            return "F122", {"valid": False, "reason": evidence_reason or "required_check_failed", "check_id": check_id}
    exit_check = check_map.get("exit_code")
    if exit_check is not None and (not isinstance(exit_check.get("actual"), int) or isinstance(exit_check.get("actual"), bool) or exit_check["actual"] not in contract["expected_exit_codes"]):
        return "F122", {"valid": False, "reason": "target_exit_code"}
    if contract["require_counts"]:
        return "F122", {"valid": False, "reason": "counts_evidence_schema_undefined"}
    if contract["require_id_set_sha256"]:
        return "F122", {"valid": False, "reason": "id_set_evidence_schema_undefined"}
    artifact_items = done.get("artifacts")
    if not isinstance(artifact_items, list) or any(not isinstance(item, dict) for item in artifact_items):
        return "F121", {"valid": False, "reason": "artifact_records"}
    artifacts = {item.get("path"): item for item in artifact_items if isinstance(item.get("path"), str)}
    if len(artifacts) != len(artifact_items) or set(artifacts) != set(contract["required_artifacts"]):
        return "F120", {"valid": False, "reason": "artifact_set"}
    for required_path in contract["required_artifacts"]:
        item = artifacts[required_path]
        path = Path(required_path)
        try:
            updated_at = parse_utc(item.get("updated_at_utc"))
        except (TypeError, ValueError):
            return "F121", {"valid": False, "reason": "artifact_updated_at", "path": required_path}
        if not path.is_file():
            return "F120", {"valid": False, "reason": "artifact_missing", "path": required_path}
        if path.stat().st_mtime < started_epoch or updated_at.timestamp() < started_epoch:
            return "F121", {"valid": False, "reason": "artifact_stale", "path": required_path}
        if not isinstance(item.get("sha256"), str) or not SHA256_RE.fullmatch(item["sha256"]):
            return "F121", {"valid": False, "reason": "artifact_hash_field", "path": required_path}
        if item["sha256"].lower() != sha256_file(path):
            return "F124", {"valid": False, "reason": "artifact_sha256", "path": required_path}
    return None, {"valid": True, "checks": sorted(check_map), "artifacts": sorted(artifacts), "validated_at_utc": done["validated_at_utc"]}


def _normalized_path(value: Any) -> str:
    return os.path.normcase(os.path.normpath(str(value or "")))


def canonical_create_time(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        raise ValueError("invalid process create_time")
    if isinstance(value, (int, float)):
        timestamp = float(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("invalid process create_time")
        try:
            timestamp = float(stripped)
        except ValueError:
            timestamp = parse_utc(stripped).timestamp()
    else:
        raise ValueError("invalid process create_time")
    if not timestamp >= 0 or timestamp == float("inf"):
        raise ValueError("invalid process create_time")
    try:
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError("invalid process create_time") from exc


def identity_matches(record: dict[str, Any], observed: dict[str, Any] | None) -> bool:
    if not observed or record.get("pid") != observed.get("pid"):
        return False
    try:
        if canonical_create_time(record.get("create_time")) != canonical_create_time(observed.get("create_time")):
            return False
    except ValueError:
        return False
    return _normalized_path(record.get("executable_path")) == _normalized_path(observed.get("executable_path")) and str(record.get("command_line_sha256", "")).lower() == str(observed.get("command_line_sha256", "")).lower()


def query_process_snapshot() -> dict[int, dict[str, Any]]:
    expression = "$p=Get-CimInstance Win32_Process | Select-Object @{n='pid';e={[int]$_.ProcessId}},@{n='parent_pid';e={[int]$_.ParentProcessId}},@{n='create_time';e={if($_.CreationDate){$_.CreationDate.ToUniversalTime().ToString('o')}else{$null}}},@{n='executable_path';e={$_.ExecutablePath}},@{n='command_line';e={$_.CommandLine}};$p|ConvertTo-Json -Compress"
    completed = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", expression], capture_output=True, text=True, check=False, timeout=15)
    if completed.returncode != 0:
        raise RuntimeError("CIM process snapshot failed")
    loaded = json.loads(completed.stdout or "[]")
    rows = loaded if isinstance(loaded, list) else [loaded]
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("pid"), int):
            continue
        command_line = row.get("command_line")
        create_time = row.get("create_time")
        try:
            canonical_time = canonical_create_time(create_time)
        except ValueError:
            canonical_time = None
        result[row["pid"]] = {
            "pid": row["pid"], "parent_pid": row.get("parent_pid"), "create_time": canonical_time,
            "executable_path": row.get("executable_path") or "", "command_line_sha256": command_line_sha256(command_line),
            "command_line_known": isinstance(command_line, str) and bool(normalize_command_line(command_line)),
        }
    return result


def process_stop_api(record: dict[str, Any], force: bool) -> dict[str, Any]:
    command = ["taskkill", "/PID", str(record["pid"])]
    if force:
        command.append("/F")
    completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    alive = identity_matches(record, query_process_snapshot().get(record["pid"]))
    return {"requested": True, "force": force, "returncode": completed.returncode, "alive_after": alive, "stderr": completed.stderr[-2000:]}


def safe_stop(record: dict[str, Any], observed: dict[str, Any] | None, stop_api: Callable[[dict[str, Any], bool], dict[str, Any]], observe_api: Callable[[int], dict[str, Any] | None] | None = None, sleep_fn: Callable[[float], None] = time.sleep, grace_seconds: float = 3.0) -> dict[str, Any]:
    if Path(str(record.get("executable_path", ""))).name.casefold() == "indesign.exe":
        return {"pid": record.get("pid"), "status": "excluded_indesign"}
    if not identity_matches(record, observed):
        return {"pid": record.get("pid"), "status": "identity_mismatch"}
    graceful = stop_api(record, False)
    forced = None
    after = observed
    if graceful.get("alive_after"):
        sleep_fn(grace_seconds)
        after = observe_api(record["pid"]) if observe_api else observed
        if not identity_matches(record, after):
            return {"pid": record["pid"], "status": "identity_changed_after_graceful", "graceful": graceful, "force": None, "alive_after": False}
        forced = stop_api(record, True)
        after = observe_api(record["pid"]) if observe_api else (after if forced.get("alive_after") else None)
    elif observe_api:
        after = observe_api(record["pid"])
    alive_after = identity_matches(record, after) if observe_api else bool((forced or graceful).get("alive_after"))
    return {"pid": record["pid"], "status": "residual" if alive_after else "stopped", "graceful": graceful, "force": forced, "alive_after": alive_after}


def _stop_candidates(processes: list[dict[str, Any]], snapshot: dict[int, dict[str, Any]], supervisors_only: bool) -> list[tuple[int, dict[str, Any]]]:
    registered = [item for item in processes if not supervisors_only or item["role"] == "supervisor"]
    roots = [item for item in registered if identity_matches(item, snapshot.get(item["pid"]))]
    if supervisors_only:
        return [(0, dict(item)) for item in sorted(roots, key=lambda value: value["pid"])]
    children: dict[int, list[int]] = {}
    for item in snapshot.values():
        children.setdefault(item.get("parent_pid"), []).append(item["pid"])
    candidates: dict[int, tuple[int, dict[str, Any]]] = {}

    def visit(pid: int, depth: int) -> None:
        for child in children.get(pid, []):
            visit(child, depth + 1)
        observed = snapshot.get(pid)
        if observed is not None and (
            pid in {item["pid"] for item in registered}
            or (
                observed.get("command_line_known") is True
                and isinstance(observed.get("executable_path"), str)
                and Path(observed["executable_path"]).is_absolute()
                and isinstance(observed.get("command_line_sha256"), str)
                and SHA256_RE.fullmatch(observed["command_line_sha256"])
            )
        ):
            current = candidates.get(pid)
            if current is None or depth > current[0]:
                candidates[pid] = (depth, dict(observed))

    for root in roots:
        visit(root["pid"], 0)
    for root in registered:
        depth = candidates[root["pid"]][0] if root["pid"] in candidates else 0
        candidates[root["pid"]] = (depth, dict(root))
    return sorted(candidates.values(), key=lambda item: (-item[0], item[1]["pid"]))


def stop_registered_processes(processes: list[dict[str, Any]], snapshot_fn: Callable[[], dict[int, dict[str, Any]]] = query_process_snapshot, stop_api: Callable[[dict[str, Any], bool], dict[str, Any]] = process_stop_api, sleep_fn: Callable[[float], None] = time.sleep, supervisors_only: bool = False) -> dict[str, Any]:
    initial = snapshot_fn()
    candidates = _stop_candidates(processes, initial, supervisors_only)
    results: list[dict[str, Any]] = []
    for _, record in candidates:
        observed = snapshot_fn().get(record["pid"])
        results.append(safe_stop(record, observed, stop_api, lambda pid: snapshot_fn().get(pid), sleep_fn, 3.0))
    final = snapshot_fn()
    residual = [record["pid"] for _, record in candidates if identity_matches(record, final.get(record["pid"])) and Path(str(record.get("executable_path", ""))).name.casefold() != "indesign.exe"]
    return {"before": [record for _, record in candidates], "results": results, "residual_pids": residual, "supervisors_only": supervisors_only}


def supervisors_alive(processes: list[dict[str, Any]], snapshot: dict[int, dict[str, Any]]) -> bool:
    supervisors = [item for item in processes if item["role"] == "supervisor"]
    return bool(supervisors) and all(identity_matches(item, snapshot.get(item["pid"])) for item in supervisors)


def pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_guard_lock(output_dir: Path, run_id: str) -> tuple[str, dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "guard_lock.json"
    payload = {"schema_version": 1, "run_id": run_id, "pid": os.getpid(), "started_at_utc": utc_now()}
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        try:
            existing = stable_load_json(path)
        except Exception:
            return "stale_or_invalid", {}
        return ("live" if isinstance(existing.get("pid"), int) and pid_is_alive(existing["pid"]) else "stale_or_invalid"), existing
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return "acquired", payload


def redact_secrets(value: str) -> str:
    result = value
    result = SECRET_PATTERNS[0].sub(r"\1[REDACTED]", result)
    result = SECRET_PATTERNS[1].sub(lambda match: f"{match.group(1)}=[REDACTED]", result)
    result = SECRET_PATTERNS[2].sub("[REDACTED]", result)
    return result


def build_luna_prompt(report: dict[str, Any], limit_chars: int = 12000) -> str:
    tail = redact_secrets(str(report.get("last_log_tail", "")))[-limit_chars:]
    selected = {key: report.get(key) for key in ("run_id", "primary_code", "force_codes", "reason", "stop_result")}
    selected["last_log_tail"] = tail
    return redact_secrets("Tusk Core guard force stop. Analyze only; do not modify code.\n\n" + json.dumps(selected, ensure_ascii=False, indent=2))


def notify_codex_cli(*, prompt_path: Path, response_path: Path, notify_status_path: Path, session_id: str, model: str, reasoning_effort: str, codex_exe: str, timeout_seconds: int, writer: SafeWriter | None = None) -> dict[str, Any]:
    executable = shutil.which(codex_exe) or (codex_exe if Path(codex_exe).is_file() else None)
    temporary_response: Path | None = None
    if not executable:
        result = {"status": "failed", "error": "codex executable not found", "checked_at_utc": utc_now()}
    else:
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix="luna_response_", suffix=".tmp", dir=prompt_path.parent)
        os.close(descriptor)
        temporary_response = Path(temporary_name)
        command = [str(executable), "exec", "-s", "read-only", "resume", "-m", model, "-c", f'model_reasoning_effort="{reasoning_effort}"', "-o", str(temporary_response), session_id, "-"]
        try:
            completed = subprocess.run(command, input=prompt_path.read_text(encoding="utf-8"), capture_output=True, text=True, check=False, timeout=timeout_seconds)
            result = {"status": "sent" if completed.returncode == 0 else "failed", "returncode": completed.returncode, "stdout_tail": redact_secrets(completed.stdout[-12000:]), "stderr_tail": redact_secrets(completed.stderr[-12000:])}
            if completed.returncode == 0 and temporary_response.is_file():
                response = temporary_response.read_text(encoding="utf-8", errors="replace")
                (writer.text(response_path, response) if writer else atomic_text(response_path, response))
        except subprocess.TimeoutExpired:
            result = {"status": "timeout"}
        except OSError as exc:
            result = {"status": "failed", "error": str(exc)}
        finally:
            if temporary_response is not None and temporary_response.exists():
                temporary_response.unlink()
    if writer:
        writer.json(notify_status_path, result)
    else:
        atomic_json(notify_status_path, result)
    return result


def start_command_reader(enabled: bool, input_stream: TextIO | None = None) -> queue.Queue[str] | None:
    stream = input_stream if input_stream is not None else sys.stdin
    if not enabled or stream is None:
        return None
    try:
        if not stream.isatty():
            return None
    except (AttributeError, OSError):
        return None
    commands: queue.Queue[str] = queue.Queue()

    def read_commands() -> None:
        while True:
            try:
                value = stream.readline()
            except (OSError, ValueError):
                return
            if value == "":
                return
            commands.put(value.rstrip("\r\n"))

    threading.Thread(target=read_commands, name="tusk-guard-stdin", daemon=True).start()
    return commands


def drain_commands(commands: queue.Queue[str] | None, status: dict[str, Any], output: TextIO | None = None) -> tuple[bool, list[dict[str, Any]]]:
    if commands is None:
        return False, []
    stream = output or sys.stderr
    stop = False
    events: list[dict[str, Any]] = []
    while True:
        try:
            command = commands.get_nowait()
        except queue.Empty:
            break
        checked_at = utc_now()
        if command == "/stop":
            stop = True
            events.append({"event": "command_stop", "command": command, "checked_at_utc": checked_at})
        elif command == "/help":
            stream.write("/help /status /stop\n")
            events.append({"event": "command_help", "command": command, "checked_at_utc": checked_at})
        elif command == "/status":
            stream.write(json.dumps(status, ensure_ascii=False) + "\n")
            events.append({"event": "command_status", "command": command, "checked_at_utc": checked_at})
        else:
            events.append({"event": "command_rejected", "command": command, "checked_at_utc": checked_at})
        stream.flush()
    return stop, events


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--log-path", type=Path, action="append", default=[])
    parser.add_argument("--allowed-output-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--done-file", type=Path, required=True)
    parser.add_argument("--test-contract", type=Path, required=True)
    parser.add_argument("--process-registry", type=Path, required=True)
    parser.add_argument("--error-registry", type=Path, required=True)
    parser.add_argument("--pid", type=int, action="append", default=[])
    parser.add_argument("--pid-policy", choices=("observe", "supervisor_required_until_done"), default="supervisor_required_until_done")
    parser.add_argument("--progress-mode", choices=("structured_only", "legacy_append"), default="structured_only")
    parser.add_argument("--done-mode", choices=("strict_json", "legacy_exists"), default="strict_json")
    parser.add_argument("--interactive-commands", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--stall-seconds", type=int, default=1800)
    parser.add_argument("--repeat-threshold", type=int, default=80)
    parser.add_argument("--stop-on-force", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--notify-codex-cli", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--luna-task-policy", choices=("new_task", "verified_cleared_task"), default="new_task")
    parser.add_argument("--luna-task-file", type=Path)
    parser.add_argument("--luna-thread-id")
    parser.add_argument("--luna-log-limit-chars", type=int, default=12000)
    parser.add_argument("--codex-exe", default="codex")
    parser.add_argument("--codex-model", default="gpt-5.6-luna")
    parser.add_argument("--codex-reasoning-effort", default="low")
    parser.add_argument("--codex-cli-timeout-seconds", type=int, default=300)
    return parser.parse_args(argv)


def _write_monitor_error(writer: SafeWriter, output_dir: Path, error: Any, processes: list[dict[str, Any]] | None = None, failsafe_stop: bool = True) -> None:
    stop_result = None
    if processes and failsafe_stop:
        try:
            stop_result = stop_registered_processes(processes, supervisors_only=True)
        except Exception as stop_error:
            stop_result = {"error": str(stop_error)}
    writer.json(output_dir / "monitor_error.json", {"status": "monitor_error", "error": str(error), "checked_at_utc": utc_now(), "stop_result": stop_result})


def _force_exit(args: argparse.Namespace, writer: SafeWriter, output_dir: Path, processes: list[dict[str, Any]], force: list[tuple[str, str]], minor_events: int, log_tail: str, user_console_stop: bool = False) -> int:
    primary, reason = force[0]
    stop_result = None
    if args.stop_on_force:
        try:
            stop_result = stop_registered_processes(processes)
        except Exception as exc:
            stop_result = {"error": str(exc), "residual_pids": []}
    codes = [code for code, _ in force]
    if stop_result and (stop_result.get("residual_pids") or stop_result.get("error")) and "F024" not in codes:
        codes.append("F024")
    user_requested_stop = user_console_stop and "F182" in codes and not any(code != "F182" for code in codes)
    report = {
        "status": "force_stop", "run_id": args.run_id, "primary_code": primary, "force_codes": codes, "reason": reason,
        "minor_issue_count": minor_events, "observed_pids": args.pid, "registered_processes": processes, "stop_result": stop_result,
        "residual_pids": stop_result.get("residual_pids", []) if stop_result else [], "user_requested_stop": user_requested_stop,
        "user_stop_origin": "user_console" if user_console_stop else None,
        "last_log_tail": log_tail[-args.luna_log_limit_chars:], "checked_at_utc": utc_now(),
    }
    writer.json(output_dir / "force_stop_report.json", report)
    if args.notify_codex_cli and not report["user_requested_stop"]:
        prompt = build_luna_prompt(report, args.luna_log_limit_chars)
        prompt_path = writer.text(output_dir / "luna_report_prompt.md", prompt)
        if prompt_path is not None:
            report["codex_cli_notify"] = notify_codex_cli(
                prompt_path=prompt_path, response_path=output_dir / "luna_response.md", notify_status_path=output_dir / "codex_cli_notify.json",
                session_id=args.luna_thread_id, model=args.codex_model, reasoning_effort=args.codex_reasoning_effort,
                codex_exe=args.codex_exe, timeout_seconds=args.codex_cli_timeout_seconds, writer=writer,
            )
            writer.json(output_dir / "force_stop_report.json", report)
    return 10


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    writer: SafeWriter | None = None
    output_dir: Path | None = None
    processes: list[dict[str, Any]] = []
    try:
        workspace, _, output_dir, done_file, fallback = validate_paths(args)
        writer = SafeWriter(output_dir, fallback)
        error_registry = parse_error_registry(args.error_registry.resolve())
        contract = validate_contract(args.test_contract.resolve(), args.run_id)
        processes = validate_registry(args.process_registry.resolve(), args.run_id)
        if args.pid_policy == "supervisor_required_until_done" and not any(item["role"] == "supervisor" for item in processes):
            raise ValueError("supervisor identity required")
        validate_luna_task(args, output_dir.parent)
        lock_status, lock = acquire_guard_lock(output_dir, args.run_id)
        if lock_status == "live":
            return _force_exit(args, writer, output_dir, processes, [("F023", "live guard lock detected")], 0, json.dumps(lock, ensure_ascii=False))
        if lock_status != "acquired":
            raise ValueError("stale or invalid guard lock")
    except Exception as exc:
        if writer is None or output_dir is None:
            sys.stderr.write(json.dumps({"status": "monitor_error", "error": str(exc), "checked_at_utc": utc_now()}, ensure_ascii=False) + "\n")
            sys.stderr.flush()
        else:
            _write_monitor_error(writer, output_dir, exc, processes)
        return 1
    events_path = output_dir / "guard_events.jsonl"
    writer.jsonl(events_path, {"event": "started", "run_id": args.run_id, "checked_at_utc": utc_now()})
    excluded = [output_dir, fallback, done_file, args.test_contract.resolve(), args.process_registry.resolve()]
    if args.luna_task_file:
        excluded.append(args.luna_task_file.resolve(strict=False))
    cursors = snapshot_logs(args.log_path, excluded, workspace)
    last_progress = time.monotonic()
    minor_targets: set[str] = set()
    minor_events = 0
    minor_threshold_emitted = False
    repeated: tuple[str, int] | None = None
    command_queue = start_command_reader(args.interactive_commands)
    log_tail = ""
    status = {"status": "watching", "run_id": args.run_id, "minor_issue_count": 0, "idle_seconds": 0.0}
    writer.json(output_dir / "guard_status.json", status)
    try:
        while True:
            explicit_force: list[tuple[str, str]] = []
            repeat_force: list[tuple[str, str]] = []
            monitor_errors: list[dict[str, str]] = []
            user_stop, command_events = drain_commands(command_queue, status)
            for event in command_events:
                writer.jsonl(events_path, {"run_id": args.run_id, **event})
            if user_stop:
                explicit_force.append(("F182", "user_requested_stop"))
            current_logs = snapshot_logs(args.log_path, excluded, workspace)
            for path in current_logs:
                lines, cursors[path], rotated = read_new_lines(path, cursors.get(path, {"identity": None, "offset": 0, "buffer": b""}))
                if rotated:
                    writer.jsonl(events_path, {"event": "log_rotated", "run_id": args.run_id, "log": str(path), "checked_at_utc": utc_now()})
                if lines and args.progress_mode == "legacy_append":
                    last_progress = time.monotonic()
                for line in lines:
                    log_tail = (log_tail + line + "\n")[-args.luna_log_limit_chars:]
                    marker = parse_event(line, args.run_id, error_registry)
                    if not marker:
                        continue
                    if marker["kind"] == "PROGRESS":
                        if not validate_progress(marker):
                            monitor_errors.append({"reason": "invalid_progress_marker", "line": line})
                        else:
                            repeated = None
                            if args.progress_mode == "structured_only":
                                last_progress = time.monotonic()
                        continue
                    code, issue = validate_issue(marker, error_registry)
                    if issue:
                        monitor_errors.append({"reason": issue, "line": line})
                        continue
                    if code == "F182":
                        monitor_errors.append({"reason": "F182_console_only", "line": line})
                        continue
                    fingerprint = issue_fingerprint(marker)
                    repeated = (fingerprint, repeated[1] + 1) if repeated and repeated[0] == fingerprint else (fingerprint, 1)
                    if repeated[1] >= args.repeat_threshold:
                        repeat_force = [("F022", "repeated normalized event")]
                    if marker["kind"] == "MINOR_ISSUE":
                        minor_events += 1
                        minor_targets.add(marker["target"])
                        writer.jsonl(output_dir / "minor_issues.jsonl", {"run_id": args.run_id, "code": code, "target": marker["target"], "line": line, "checked_at_utc": utc_now()})
                        if not minor_threshold_emitted and minor_threshold_reached(len(minor_targets), minor_events, contract["minor_total_units"]):
                            explicit_force.append(("F123", "minor threshold exceeded"))
                            minor_threshold_emitted = True
                    else:
                        explicit_force.append((code, line))
            if explicit_force:
                if monitor_errors:
                    _write_monitor_error(writer, output_dir, monitor_errors, processes, failsafe_stop=False)
                return _force_exit(args, writer, output_dir, processes, explicit_force + repeat_force, minor_events, log_tail, user_console_stop=user_stop)
            if monitor_errors:
                _write_monitor_error(writer, output_dir, monitor_errors, processes)
                return 1
            if done_file.exists():
                if args.done_mode == "legacy_exists":
                    done_code, done_result = None, {"valid": True, "mode": "legacy_exists", "product_completion_evidence": False}
                else:
                    done_code, done_result = validate_done(done_file, args.test_contract.resolve(), contract, contract["_started_epoch"], contract["_sha256"])
                if done_code:
                    return _force_exit(args, writer, output_dir, processes, [(done_code, done_result["reason"])], minor_events, log_tail)
                writer.json(output_dir / "guard_summary.json", {"status": "completed", "run_id": args.run_id, "done_validation": done_result, "minor_issue_count": minor_events, "product_completion_decision": "not_made_by_guard", "checked_at_utc": utc_now()})
                writer.jsonl(events_path, {"event": "completed", "run_id": args.run_id, "checked_at_utc": utc_now()})
                return 0
            if args.pid_policy == "supervisor_required_until_done" and not supervisors_alive(processes, query_process_snapshot()):
                return _force_exit(args, writer, output_dir, processes, [("F020", "required supervisor lost")], minor_events, log_tail)
            if time.monotonic() - last_progress >= args.stall_seconds:
                return _force_exit(args, writer, output_dir, processes, [("F021", "progress stalled")], minor_events, log_tail)
            if repeat_force:
                return _force_exit(args, writer, output_dir, processes, repeat_force, minor_events, log_tail)
            status = {"status": "watching", "run_id": args.run_id, "idle_seconds": round(time.monotonic() - last_progress, 1), "minor_issue_count": minor_events, "registered_process_count": len(processes), "checked_at_utc": utc_now()}
            writer.json(output_dir / "guard_status.json", status)
            time.sleep(args.poll_seconds)
    except Exception as exc:
        _write_monitor_error(writer, output_dir, exc, processes)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
