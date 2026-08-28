"""Shared canonical serialization and fail-closed workspace path primitives."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SNAPSHOT_ALGORITHM = "sha256-path-snapshot-v1"
HEX64 = frozenset("0123456789abcdef")
REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class EvidenceSafetyError(Exception):
    """Raised when a path or byte-level operation cannot be proven safe."""


@dataclass(frozen=True)
class PathFingerprint:
    path: Path
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int
    attributes: int


@dataclass(frozen=True)
class PathSafetyToken:
    workspace_root: Path
    candidate: Path
    exists: bool
    fingerprints: tuple[PathFingerprint, ...]


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def is_lower_hex64(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in HEX64 for character in value)
    )


def normalize_workspace_relative_path(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise EvidenceSafetyError("invalid_workspace_relative_path")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or value != candidate.as_posix()
        or value == "."
        or "." in candidate.parts
        or ".." in candidate.parts
        or not candidate.parts
        or ":" in candidate.parts[0]
    ):
        raise EvidenceSafetyError("invalid_workspace_relative_path")
    return value


def normalize_scope_paths(values: Any) -> list[str]:
    if not isinstance(values, list):
        raise EvidenceSafetyError("scope_paths_must_be_array")
    normalized = [normalize_workspace_relative_path(value) for value in values]
    if normalized != sorted(normalized) or len(normalized) != len(set(normalized)):
        raise EvidenceSafetyError("scope_paths_must_be_sorted_unique")
    return normalized


def _absolute(path: Path | str) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _is_within(candidate: Path, boundary: Path) -> bool:
    try:
        return os.path.commonpath((os.path.normcase(str(candidate)), os.path.normcase(str(boundary)))) == os.path.normcase(str(boundary))
    except (OSError, ValueError):
        return False


def _is_reparse(details: os.stat_result) -> bool:
    attributes = int(getattr(details, "st_file_attributes", 0))
    return stat.S_ISLNK(details.st_mode) or bool(attributes & REPARSE_ATTRIBUTE)


def _fingerprint(path: Path, details: os.stat_result) -> PathFingerprint:
    return PathFingerprint(
        path=path,
        device=int(details.st_dev),
        inode=int(details.st_ino),
        mode=int(details.st_mode),
        size=int(details.st_size),
        modified_ns=int(details.st_mtime_ns),
        attributes=int(getattr(details, "st_file_attributes", 0)),
    )


def _fingerprint_matches(expected: PathFingerprint, details: os.stat_result) -> bool:
    return expected == _fingerprint(expected.path, details)


def _path_from_anchor(path: Path) -> Iterable[Path]:
    values: list[Path] = []
    current = path
    while True:
        values.append(current)
        if current.parent == current:
            break
        current = current.parent
    return reversed(values)


def safe_workspace_root(value: Path | str) -> Path:
    root = _absolute(value)
    for candidate in _path_from_anchor(root):
        try:
            details = os.lstat(candidate)
        except OSError as error:
            raise EvidenceSafetyError(
                f"workspace_root_lstat_failed:{type(error).__name__}"
            ) from error
        if _is_reparse(details):
            raise EvidenceSafetyError("workspace_root_reparse_rejected")
    try:
        resolved = root.resolve(strict=True)
    except OSError as error:
        raise EvidenceSafetyError(
            f"workspace_root_unreadable:{type(error).__name__}"
        ) from error
    try:
        details = os.lstat(resolved)
    except OSError as error:
        raise EvidenceSafetyError(
            f"workspace_root_lstat_failed:{type(error).__name__}"
        ) from error
    if _is_reparse(details) or not stat.S_ISDIR(details.st_mode):
        raise EvidenceSafetyError("workspace_root_not_plain_directory")
    return resolved


def workspace_candidate(
    workspace_root: Path | str,
    value: Path | str,
) -> tuple[Path, Path]:
    root = safe_workspace_root(workspace_root)
    raw = Path(value)
    candidate = _absolute(raw if raw.is_absolute() else root / raw)
    if not _is_within(candidate, root):
        raise EvidenceSafetyError("path_outside_workspace")
    return root, candidate


def nearest_existing_ancestor_lstat(
    workspace_root: Path | str,
    value: Path | str,
) -> tuple[Path, os.stat_result]:
    root, candidate = workspace_candidate(workspace_root, value)
    current = candidate
    while True:
        try:
            details = os.lstat(current)
        except FileNotFoundError:
            if current == root:
                raise EvidenceSafetyError("workspace_root_missing")
            current = current.parent
            continue
        except OSError as error:
            raise EvidenceSafetyError(
                f"nearest_ancestor_lstat_failed:{type(error).__name__}"
            ) from error
        if _is_reparse(details):
            raise EvidenceSafetyError("nearest_ancestor_reparse_rejected")
        return current, details


def capture_path_safety(
    workspace_root: Path | str,
    value: Path | str,
    *,
    require_exists: bool = False,
    require_file: bool = False,
    require_directory: bool = False,
) -> PathSafetyToken:
    root, candidate = workspace_candidate(workspace_root, value)
    nearest_existing_ancestor_lstat(root, candidate)
    fingerprints: list[PathFingerprint] = []
    current = root
    parts = candidate.relative_to(root).parts
    try:
        details = os.lstat(current)
    except OSError as error:
        raise EvidenceSafetyError(
            f"path_lstat_failed:{type(error).__name__}"
        ) from error
    if _is_reparse(details):
        raise EvidenceSafetyError("path_reparse_rejected")
    fingerprints.append(_fingerprint(current, details))
    exists = True
    for part in parts:
        current = current / part
        try:
            details = os.lstat(current)
        except FileNotFoundError:
            exists = False
            break
        except OSError as error:
            raise EvidenceSafetyError(
                f"path_lstat_failed:{type(error).__name__}"
            ) from error
        if _is_reparse(details):
            raise EvidenceSafetyError("path_reparse_rejected")
        fingerprints.append(_fingerprint(current, details))
    if require_exists and not exists:
        raise EvidenceSafetyError("required_path_missing")
    if exists:
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as error:
            raise EvidenceSafetyError(
                f"path_resolve_failed:{type(error).__name__}"
            ) from error
        if not _is_within(resolved, root):
            raise EvidenceSafetyError("resolved_path_outside_workspace")
        terminal = fingerprints[-1]
        if require_file and not stat.S_ISREG(terminal.mode):
            raise EvidenceSafetyError("required_regular_file")
        if require_directory and not stat.S_ISDIR(terminal.mode):
            raise EvidenceSafetyError("required_directory")
    elif require_file or require_directory:
        raise EvidenceSafetyError("required_path_missing")
    return PathSafetyToken(root, candidate, exists, tuple(fingerprints))


def recheck_path_safety(token: PathSafetyToken) -> None:
    for expected in token.fingerprints:
        try:
            details = os.lstat(expected.path)
        except OSError as error:
            raise EvidenceSafetyError(
                f"path_toctou_changed:{type(error).__name__}"
            ) from error
        if _is_reparse(details) or not _fingerprint_matches(expected, details):
            raise EvidenceSafetyError("path_toctou_changed")
    if token.exists:
        return
    last_existing = token.fingerprints[-1].path
    missing_parts = token.candidate.relative_to(last_existing).parts
    if not missing_parts:
        raise EvidenceSafetyError("path_toctou_existence_changed")
    first_missing = last_existing / missing_parts[0]
    try:
        os.lstat(first_missing)
    except FileNotFoundError:
        return
    except OSError as error:
        raise EvidenceSafetyError(
            f"path_toctou_changed:{type(error).__name__}"
        ) from error
    raise EvidenceSafetyError("path_toctou_existence_changed")


def safe_read_bytes(workspace_root: Path | str, value: Path | str) -> bytes:
    token = capture_path_safety(
        workspace_root,
        value,
        require_exists=True,
        require_file=True,
    )
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(token.candidate, flags)
    except OSError as error:
        raise EvidenceSafetyError(
            f"safe_read_open_failed:{type(error).__name__}"
        ) from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not _fingerprint_matches(
            token.fingerprints[-1], before
        ):
            raise EvidenceSafetyError("safe_read_identity_changed")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if not _fingerprint_matches(token.fingerprints[-1], after):
            raise EvidenceSafetyError("safe_read_changed_during_read")
    finally:
        os.close(descriptor)
    recheck_path_safety(token)
    return b"".join(chunks)


def safe_mkdirs(workspace_root: Path | str, value: Path | str) -> Path:
    root, candidate = workspace_candidate(workspace_root, value)
    current = root
    for part in candidate.relative_to(root).parts:
        next_path = current / part
        token = capture_path_safety(root, next_path)
        if token.exists:
            if not stat.S_ISDIR(token.fingerprints[-1].mode):
                raise EvidenceSafetyError("mkdir_component_not_directory")
        else:
            parent = capture_path_safety(
                root,
                current,
                require_exists=True,
                require_directory=True,
            )
            recheck_path_safety(parent)
            try:
                os.mkdir(next_path)
            except OSError as error:
                raise EvidenceSafetyError(
                    f"mkdir_failed:{type(error).__name__}"
                ) from error
            capture_path_safety(
                root,
                next_path,
                require_exists=True,
                require_directory=True,
            )
        current = next_path
    return candidate


def _line_bytes(line: bytes) -> bytes:
    if not isinstance(line, bytes) or not line or b"\n" in line or b"\r" in line:
        raise EvidenceSafetyError("single_line_bytes_required")
    return line + b"\n"


def safe_create_line(
    workspace_root: Path | str,
    value: Path | str,
    line: bytes,
) -> PathSafetyToken:
    token = capture_path_safety(workspace_root, value)
    if token.exists:
        raise EvidenceSafetyError("exclusive_file_already_exists")
    recheck_path_safety(token)
    data = _line_bytes(line)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(token.candidate, flags, 0o600)
    except OSError as error:
        raise EvidenceSafetyError(
            f"exclusive_create_failed:{type(error).__name__}"
        ) from error
    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode):
            raise EvidenceSafetyError("created_path_not_regular_file")
        written = os.write(descriptor, data)
        if written != len(data):
            raise EvidenceSafetyError("partial_line_write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return capture_path_safety(
        workspace_root,
        token.candidate,
        require_exists=True,
        require_file=True,
    )


def safe_append_line(
    workspace_root: Path | str,
    value: Path | str,
    line: bytes,
) -> PathSafetyToken:
    token = capture_path_safety(
        workspace_root,
        value,
        require_exists=True,
        require_file=True,
    )
    recheck_path_safety(token)
    data = _line_bytes(line)
    flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(token.candidate, flags)
    except OSError as error:
        raise EvidenceSafetyError(
            f"append_open_failed:{type(error).__name__}"
        ) from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not _fingerprint_matches(
            token.fingerprints[-1], before
        ):
            raise EvidenceSafetyError("append_identity_changed")
        written = os.write(descriptor, data)
        if written != len(data):
            raise EvidenceSafetyError("partial_line_write")
        os.fsync(descriptor)
        after = os.fstat(descriptor)
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or after.st_size != before.st_size + len(data)
        ):
            raise EvidenceSafetyError("append_postwrite_identity_changed")
    finally:
        os.close(descriptor)
    return capture_path_safety(
        workspace_root,
        token.candidate,
        require_exists=True,
        require_file=True,
    )


def safe_unlink_regular(workspace_root: Path | str, value: Path | str) -> None:
    token = capture_path_safety(
        workspace_root,
        value,
        require_exists=True,
        require_file=True,
    )
    recheck_path_safety(token)
    try:
        os.unlink(token.candidate)
    except OSError as error:
        raise EvidenceSafetyError(
            f"safe_unlink_failed:{type(error).__name__}"
        ) from error


def validate_work_id(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > 512
        or any(ord(character) < 32 for character in value)
    ):
        raise EvidenceSafetyError("invalid_work_id")
    return value


def hashed_work_path(workspace_root: Path | str, work_id: Any) -> Path:
    root = safe_workspace_root(workspace_root)
    work = validate_work_id(work_id)
    digest = hashlib.sha256(work.encode("utf-8")).hexdigest()
    return root / "work" / "orchestration_evidence" / digest


def evidence_log_path(workspace_root: Path | str, work_id: Any) -> Path:
    return hashed_work_path(workspace_root, work_id) / "events.jsonl"


def build_snapshot_payload(
    workspace_root: Path | str,
    scope_paths: list[str],
) -> dict[str, Any]:
    root = safe_workspace_root(workspace_root)
    paths = normalize_scope_paths(scope_paths)
    entries: list[dict[str, Any]] = []
    for value in paths:
        candidate = root.joinpath(*PurePosixPath(value).parts)
        token = capture_path_safety(root, candidate)
        if not token.exists:
            recheck_path_safety(token)
            entries.append({"path": value, "state": "absent"})
            continue
        raw = safe_read_bytes(root, candidate)
        entries.append(
            {
                "path": value,
                "sha256": bytes_sha256(raw),
                "size": len(raw),
                "state": "file",
            }
        )
    return {
        "algorithm": SNAPSHOT_ALGORITHM,
        "path_snapshot": entries,
        "scope_paths": paths,
    }


def snapshot_identity(payload: Any) -> str:
    if not isinstance(payload, dict) or set(payload) != {
        "algorithm",
        "path_snapshot",
        "scope_paths",
    }:
        raise EvidenceSafetyError("snapshot_schema_invalid")
    if payload.get("algorithm") != SNAPSHOT_ALGORITHM:
        raise EvidenceSafetyError("snapshot_algorithm_invalid")
    paths = normalize_scope_paths(payload.get("scope_paths"))
    entries = payload.get("path_snapshot")
    if not isinstance(entries, list) or [
        entry.get("path") if isinstance(entry, dict) else None for entry in entries
    ] != paths:
        raise EvidenceSafetyError("snapshot_path_alignment_invalid")
    for entry in entries:
        state = entry.get("state")
        if state == "file":
            if (
                set(entry) != {"path", "sha256", "size", "state"}
                or not is_lower_hex64(entry.get("sha256"))
                or type(entry.get("size")) is not int
                or entry["size"] < 0
            ):
                raise EvidenceSafetyError("snapshot_file_entry_invalid")
        elif state == "absent":
            if set(entry) != {"path", "state"}:
                raise EvidenceSafetyError("snapshot_absent_entry_invalid")
        else:
            raise EvidenceSafetyError("snapshot_state_invalid")
    return payload_sha256(payload)
