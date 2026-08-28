"""Commander-controlled append-only orchestration evidence recorder."""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

try:
    from orchestration_evidence_validator import validate_approval_submission, validate_submission
    from orchestration_evidence_common import (
        EvidenceSafetyError,
        bytes_sha256,
        canonical_json_bytes,
        capture_path_safety,
        evidence_log_path,
        is_lower_hex64,
        payload_sha256,
        safe_append_line,
        safe_create_line,
        safe_mkdirs,
        safe_read_bytes,
        safe_unlink_regular,
        safe_workspace_root,
    )
except ModuleNotFoundError:
    from tools.orchestration_evidence_validator import validate_approval_submission, validate_submission
    from tools.orchestration_evidence_common import (
        EvidenceSafetyError,
        bytes_sha256,
        canonical_json_bytes,
        capture_path_safety,
        evidence_log_path,
        is_lower_hex64,
        payload_sha256,
        safe_append_line,
        safe_create_line,
        safe_mkdirs,
        safe_read_bytes,
        safe_unlink_regular,
        safe_workspace_root,
    )


SCHEMA_VERSION = 3
ENVELOPE_TYPE = "orchestration_evidence"
ENVELOPE_FIELDS = {
    "schema_version",
    "envelope_type",
    "status",
    "sequence",
    "work_id",
    "attempt_id",
    "record_type",
    "record_id",
    "record_sha256",
    "record",
    "producer_actor_id",
    "recorder_actor_id",
    "created_at_utc",
    "previous_envelope_sha256",
    "findings",
}
RECORD_ID_FIELDS = {
    "approval": "approval_id",
    "attempt": "attempt_id",
    "orchestration_setup": "orchestration_setup_id",
    "recovery_input": "recovery_input_id",
    "baseline_promotion": "baseline_promotion_id",
    "actor_binding": "binding_id",
    "identity": "identity_record_id",
    "implementation_result": "implementation_result_id",
    "handoff": "handoff_id",
    "transition": "transition_id",
    "state_transition": "state_transition_id",
}
class EvidenceLogError(Exception):
    """Raised when an existing log or requested write must fail closed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC Z timestamp required")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("UTC Z timestamp required") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("UTC Z timestamp required")
    return parsed


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _finding(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "detail": detail}


def _record_identity(record: Any) -> tuple[str | None, str | None]:
    if not isinstance(record, dict):
        return None, None
    record_type = record.get("record_type")
    id_field = RECORD_ID_FIELDS.get(record_type)
    record_id = record.get(id_field) if id_field else None
    return (
        record_type if _nonempty(record_type) else None,
        record_id if _nonempty(record_id) else None,
    )


def _storage_key(record: Any) -> tuple[Any, ...]:
    record_type, record_id = _record_identity(record)
    if not isinstance(record, dict):
        return (record_type, None, None, None, record_id)
    if record_type in {"approval", "attempt"}:
        return (record_type, record.get("work_id"), record.get("attempt_id"), record_id)
    return (
        record_type, record.get("work_id"), record.get("attempt_id"),
        record.get("generation"), record_id,
    )


def _validate_approval(record: Any, expected_work_id: str) -> dict[str, Any]:
    findings = validate_approval_submission(record, expected_work_id)
    if findings:
        raise EvidenceLogError(findings[0]["code"])
    assert isinstance(record, dict)
    return record


def _validate_envelope_shape(envelope: Any) -> None:
    if not isinstance(envelope, dict):
        raise EvidenceLogError("envelope_not_object")
    if envelope.get("schema_version") != SCHEMA_VERSION:
        code = "legacy_schema_rejected" if envelope.get("schema_version") in {1, 2} else "unsupported_schema_version"
        raise EvidenceLogError(code)
    if set(envelope) != ENVELOPE_FIELDS or envelope.get("envelope_type") != ENVELOPE_TYPE:
        raise EvidenceLogError("envelope_schema_invalid")
    if envelope.get("status") not in {"accepted", "rejected"}:
        raise EvidenceLogError("envelope_status_invalid")
    if type(envelope.get("sequence")) is not int or envelope["sequence"] < 0:
        raise EvidenceLogError("envelope_sequence_invalid")
    for field in (
        "work_id",
        "attempt_id",
        "producer_actor_id",
        "recorder_actor_id",
    ):
        if not _nonempty(envelope.get(field)):
            raise EvidenceLogError(f"envelope_{field}_invalid")
    if not is_lower_hex64(envelope.get("record_sha256")):
        raise EvidenceLogError("envelope_record_sha256_invalid")
    previous = envelope.get("previous_envelope_sha256")
    if previous is not None and not is_lower_hex64(previous):
        raise EvidenceLogError("envelope_previous_sha256_invalid")
    parse_utc(envelope.get("created_at_utc"))
    findings = envelope.get("findings")
    if not isinstance(findings, list) or any(
        not isinstance(item, dict)
        or set(item) != {"code", "detail"}
        or not _nonempty(item.get("code"))
        or not _nonempty(item.get("detail"))
        for item in findings
    ):
        raise EvidenceLogError("envelope_findings_invalid")
    if envelope["status"] == "accepted" and findings:
        raise EvidenceLogError("accepted_envelope_has_findings")
    if envelope["status"] == "rejected" and not findings:
        raise EvidenceLogError("rejected_envelope_requires_findings")
    record_type, record_id = _record_identity(envelope.get("record"))
    if envelope.get("record_type") != record_type or envelope.get("record_id") != record_id:
        raise EvidenceLogError("envelope_record_identity_mismatch")
    if payload_sha256(envelope.get("record")) != envelope["record_sha256"]:
        raise EvidenceLogError("envelope_record_payload_mismatch")


def parse_envelope_stream(raw: bytes) -> list[dict[str, Any]]:
    if not raw or not raw.endswith(b"\n"):
        raise EvidenceLogError("partial_or_empty_evidence_log")
    lines = raw.splitlines()
    if not lines or any(not line for line in lines):
        raise EvidenceLogError("blank_evidence_line_rejected")
    envelopes: list[dict[str, Any]] = []
    previous_hash: str | None = None
    previous_time: datetime | None = None
    for sequence, line in enumerate(lines):
        try:
            decoded = line.decode("utf-8")
            envelope = json.loads(decoded)
        except (UnicodeError, json.JSONDecodeError) as error:
            raise EvidenceLogError(
                f"unreadable_evidence_line:{sequence}"
            ) from error
        _validate_envelope_shape(envelope)
        if envelope["sequence"] != sequence:
            raise EvidenceLogError("non_contiguous_envelope_sequence")
        if envelope["previous_envelope_sha256"] != previous_hash:
            raise EvidenceLogError("envelope_hash_chain_mismatch")
        current_time = parse_utc(envelope["created_at_utc"])
        if previous_time is not None and current_time < previous_time:
            raise EvidenceLogError("envelope_utc_moved_backward")
        previous_hash = payload_sha256(envelope)
        previous_time = current_time
        envelopes.append(envelope)
    genesis = envelopes[0]
    if (
        genesis["sequence"] != 0
        or genesis["status"] != "accepted"
        or genesis["record_type"] != "approval"
    ):
        raise EvidenceLogError("accepted_approval_genesis_required")
    approval = _validate_approval(genesis["record"], genesis["work_id"])
    if (
        genesis["attempt_id"] != approval["attempt_id"]
        or genesis["producer_actor_id"] != approval["commander_actor_id"]
        or genesis["recorder_actor_id"] != approval["commander_actor_id"]
    ):
        raise EvidenceLogError("genesis_approval_envelope_mismatch")
    for envelope in envelopes:
        if (
            envelope["work_id"] != approval["work_id"]
            or envelope["attempt_id"] != approval["attempt_id"]
            or envelope["recorder_actor_id"] != approval["commander_actor_id"]
        ):
            raise EvidenceLogError("envelope_approval_scope_mismatch")
    return envelopes


def _make_envelope(
    *,
    approval: dict[str, Any],
    record: Any,
    status: str,
    sequence: int,
    producer_actor_id: str,
    recorder_actor_id: str,
    previous_envelope_sha256: str | None,
    findings: list[dict[str, str]],
) -> dict[str, Any]:
    record_type, record_id = _record_identity(record)
    return {
        "schema_version": SCHEMA_VERSION,
        "envelope_type": ENVELOPE_TYPE,
        "status": status,
        "sequence": sequence,
        "work_id": approval["work_id"],
        "attempt_id": approval["attempt_id"],
        "record_type": record_type,
        "record_id": record_id,
        "record_sha256": payload_sha256(record),
        "record": record,
        "producer_actor_id": producer_actor_id,
        "recorder_actor_id": recorder_actor_id,
        "created_at_utc": utc_now(),
        "previous_envelope_sha256": previous_envelope_sha256,
        "findings": findings,
    }


def _load_json_object(workspace_root: Path, path: Path) -> dict[str, Any]:
    raw = safe_read_bytes(workspace_root, path)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise EvidenceSafetyError("input_json_unreadable") from error
    if not isinstance(value, dict):
        raise EvidenceSafetyError("input_json_object_required")
    return value


@contextmanager
def _exclusive_lock(workspace_root: Path, log_path: Path) -> Iterator[None]:
    lock_path = log_path.with_name("events.lock")
    lock_payload = canonical_json_bytes(
        {"pid": os.getpid(), "created_at_utc": utc_now()}
    )
    safe_create_line(workspace_root, lock_path, lock_payload)
    try:
        yield
    finally:
        safe_unlink_regular(workspace_root, lock_path)


def initialize_log(
    workspace_root: Path | str,
    work_id: str,
    approval_path: Path | str,
    recorder_actor_id: str,
) -> dict[str, Any]:
    root = safe_workspace_root(workspace_root)
    if not _nonempty(recorder_actor_id):
        raise EvidenceLogError("recorder_actor_id_required")
    approval = _validate_approval(
        _load_json_object(root, Path(approval_path)), work_id
    )
    if recorder_actor_id != approval["commander_actor_id"]:
        raise EvidenceLogError("commander_recorder_mismatch")
    log_path = evidence_log_path(root, work_id)
    safe_mkdirs(root, log_path.parent)
    with _exclusive_lock(root, log_path):
        if capture_path_safety(root, log_path).exists:
            raw = safe_read_bytes(root, log_path)
            parse_envelope_stream(raw)
            raise EvidenceLogError("evidence_log_already_initialized")
        envelope = _make_envelope(
            approval=approval,
            record=approval,
            status="accepted",
            sequence=0,
            producer_actor_id=recorder_actor_id,
            recorder_actor_id=recorder_actor_id,
            previous_envelope_sha256=None,
            findings=[],
        )
        safe_create_line(root, log_path, canonical_json_bytes(envelope))
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "accepted",
        "sequence": 0,
        "work_id": work_id,
        "attempt_id": approval["attempt_id"],
        "log_path": log_path.relative_to(root).as_posix(),
        "envelope_sha256": payload_sha256(envelope),
        "record_sha256": envelope["record_sha256"],
        "findings": [],
    }


def append_record(
    workspace_root: Path | str,
    work_id: str,
    attempt_id: str,
    record_path: Path | str,
    producer_actor_id: str,
    recorder_actor_id: str,
    expected_sequence: int,
) -> dict[str, Any]:
    root = safe_workspace_root(workspace_root)
    if (
        not _nonempty(producer_actor_id)
        or not _nonempty(recorder_actor_id)
        or type(expected_sequence) is not int
        or expected_sequence < 1
    ):
        raise EvidenceLogError("writer_identity_or_sequence_invalid")
    record = _load_json_object(root, Path(record_path))
    log_path = evidence_log_path(root, work_id)
    with _exclusive_lock(root, log_path):
        raw = safe_read_bytes(root, log_path)
        envelopes = parse_envelope_stream(raw)
        approval = envelopes[0]["record"]
        if (
            work_id != approval["work_id"]
            or attempt_id != approval["attempt_id"]
        ):
            raise EvidenceLogError("explicit_attempt_scope_mismatch")
        if recorder_actor_id != approval["commander_actor_id"]:
            raise EvidenceLogError("commander_recorder_mismatch")
        next_sequence = envelopes[-1]["sequence"] + 1
        if expected_sequence != next_sequence:
            raise EvidenceLogError("stale_expected_sequence")
        requested_key = _storage_key(record)
        accepted: dict[tuple[Any, ...], dict[str, Any]] = {}
        for envelope in envelopes:
            if envelope["status"] != "accepted":
                continue
            key = _storage_key(envelope["record"])
            previous = accepted.get(key)
            if previous is not None:
                if previous["record_sha256"] != envelope["record_sha256"]:
                    raise EvidenceLogError("accepted_record_conflict_in_existing_log")
                continue
            accepted[key] = envelope
        previous = accepted.get(requested_key)
        requested_sha = payload_sha256(record)
        if previous is not None and previous["record_sha256"] == requested_sha:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "collapsed_replay",
                "sequence": previous["sequence"],
                "work_id": work_id,
                "attempt_id": attempt_id,
                "log_path": log_path.relative_to(root).as_posix(),
                "envelope_sha256": payload_sha256(previous),
                "record_sha256": requested_sha,
                "findings": [],
            }
        findings = validate_submission(envelopes, record, producer_actor_id)
        if previous is not None:
            findings.append(
                _finding(
                    "record_id_conflict",
                    "an accepted record already owns this record identity",
                )
            )
        status = "rejected" if findings else "accepted"
        envelope = _make_envelope(
            approval=approval,
            record=record,
            status=status,
            sequence=next_sequence,
            producer_actor_id=producer_actor_id,
            recorder_actor_id=recorder_actor_id,
            previous_envelope_sha256=payload_sha256(envelopes[-1]),
            findings=findings,
        )
        safe_append_line(root, log_path, canonical_json_bytes(envelope))
        reread = safe_read_bytes(root, log_path)
        parsed = parse_envelope_stream(reread)
        if payload_sha256(parsed[-1]) != payload_sha256(envelope):
            raise EvidenceLogError("append_reread_mismatch")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "sequence": next_sequence,
        "work_id": work_id,
        "attempt_id": attempt_id,
        "log_path": log_path.relative_to(root).as_posix(),
        "envelope_sha256": payload_sha256(envelope),
        "record_sha256": requested_sha,
        "findings": findings,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init")
    init.add_argument("--workspace-root", type=Path, required=True)
    init.add_argument("--work-id", required=True)
    init.add_argument("--approval", type=Path, required=True)
    init.add_argument("--recorder-actor-id", required=True)
    append = subparsers.add_parser("append")
    append.add_argument("--workspace-root", type=Path, required=True)
    append.add_argument("--work-id", required=True)
    append.add_argument("--attempt-id", required=True)
    append.add_argument("--record", type=Path, required=True)
    append.add_argument("--producer-actor-id", required=True)
    append.add_argument("--recorder-actor-id", required=True)
    append.add_argument("--expected-sequence", type=int, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "init":
            result = initialize_log(
                args.workspace_root,
                args.work_id,
                args.approval,
                args.recorder_actor_id,
            )
        else:
            result = append_record(
                args.workspace_root,
                args.work_id,
                args.attempt_id,
                args.record,
                args.producer_actor_id,
                args.recorder_actor_id,
                args.expected_sequence,
            )
        exit_code = 2 if result["status"] == "rejected" else 0
    except EvidenceLogError as error:
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "rejected",
            "sequence": None,
            "findings": [_finding("evidence_log_rejected", str(error))],
        }
        exit_code = 2
    except EvidenceSafetyError as error:
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "waiting_human",
            "sequence": None,
            "findings": [_finding("unsafe_or_unreadable_input", str(error))],
        }
        exit_code = 3
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
