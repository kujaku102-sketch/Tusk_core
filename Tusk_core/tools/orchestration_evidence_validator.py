"""Read-only schema-v3 validator for trusted orchestration evidence."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from orchestration_evidence_common import (
        EvidenceSafetyError,
        build_snapshot_payload,
        bytes_sha256,
        canonical_json_bytes,
        evidence_log_path,
        is_lower_hex64,
        normalize_scope_paths,
        normalize_workspace_relative_path,
        payload_sha256,
        safe_read_bytes,
        safe_workspace_root,
        snapshot_identity,
    )
except ModuleNotFoundError:
    from tools.orchestration_evidence_common import (
        EvidenceSafetyError,
        build_snapshot_payload,
        bytes_sha256,
        canonical_json_bytes,
        evidence_log_path,
        is_lower_hex64,
        normalize_scope_paths,
        normalize_workspace_relative_path,
        payload_sha256,
        safe_read_bytes,
        safe_workspace_root,
        snapshot_identity,
    )


SCHEMA_VERSION = 3
VALIDATOR_NAME = "orchestration_evidence_validator_v3"
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
STAGES = (
    "pre_skim",
    "design",
    "commander_window",
    "implementation",
    "post_skim",
    "final_review",
    "design_receipt",
)
EDGES = tuple(zip(STAGES, STAGES[1:]))
ROLE_BY_STAGE = {
    "pre_skim": "skim",
    "design": "design",
    "commander_window": "commander",
    "implementation": "implementer",
    "post_skim": "skim",
    "final_review": "final_reviewer",
    "design_receipt": "design",
}
WORK_STATES = {
    "running",
    "needs_review",
    "waiting_human",
    "needs_human_review",
    "completed",
    "abandoned",
}
PROTECTED_SURFACES = {
    "security_boundary",
    "authentication",
    "secrets",
    "distribution_installer",
    "destructive_operation",
    "user_data",
    "persistent_schema",
    "process_stop",
    "external_app",
}
IMPLEMENTATION_INTENSITIES = {"LOW", "MID", "HIGH", "MAX"}
PROCESS_LEVELS = {"P0", "P1", "P2", "P3", "P4"}
APPROVAL_FIELDS = {
    "schema_version",
    "record_type",
    "work_id",
    "attempt_id",
    "approval_id",
    "implementation_intensity",
    "process_level",
    "protected_surfaces",
    "scope_paths",
    "commander_actor_id",
    "spec",
    "created_at_utc",
}
ATTEMPT_FIELDS = {
    "schema_version",
    "record_type",
    "work_id",
    "attempt_id",
    "approval_ref",
    "created_at_utc",
}
ORCHESTRATION_SETUP_FIELDS = {
    "schema_version",
    "record_type",
    "work_id",
    "attempt_id",
    "generation",
    "orchestration_setup_id",
    "approval_ref",
    "previous_setup_ref",
    "recovery_input_ref",
    "baseline_promotion_ref",
    "baseline_identity_record_ref",
    "actor_bindings_id",
    "created_at_utc",
}
RECOVERY_INPUT_FIELDS = {
    "schema_version", "record_type", "work_id", "attempt_id", "generation",
    "recovery_input_id", "source_generation", "source_result_ref",
    "recovery_kind", "failure_evidence_refs", "recovery_bundle_ref", "created_at_utc",
}
BASELINE_PROMOTION_FIELDS = {
    "schema_version", "record_type", "work_id", "attempt_id", "generation",
    "baseline_promotion_id", "recovery_input_ref",
    "source_result_identity_record_ref", "target_baseline_identity_record_ref",
    "created_at_utc",
}
ACTOR_BINDING_FIELDS = {
    "schema_version",
    "record_type",
    "work_id",
    "attempt_id",
    "generation",
    "actor_bindings_id",
    "binding_id",
    "stage",
    "actor_role",
    "actor_id",
    "created_at_utc",
}
IDENTITY_FIELDS = {
    "schema_version",
    "record_type",
    "work_id",
    "attempt_id",
    "generation",
    "identity_record_id",
    "epoch",
    "snapshot_payload",
    "snapshot_sha256",
    "producer",
    "predecessor_identity_record_ref",
    "created_at_utc",
}
IMPLEMENTATION_RESULT_FIELDS = {
    "schema_version",
    "record_type",
    "work_id",
    "attempt_id",
    "generation",
    "implementation_result_id",
    "baseline_identity_record_ref",
    "result_identity_record_ref",
    "created_at_utc",
}
HANDOFF_FIELDS = {
    "schema_version",
    "record_type",
    "work_id",
    "attempt_id",
    "generation",
    "handoff_id",
    "source_stage",
    "target_stage",
    "actor_bindings_id",
    "source_binding_id",
    "target_binding_id",
    "recipient_actor_role",
    "recipient_binding_id",
    "spec",
    "affected_paths",
    "decision",
    "payload",
    "evidence_refs",
    "unresolved",
    "run_id",
    "supersedes_handoff_ref",
    "created_at_utc",
}
TRANSITION_FIELDS = {
    "schema_version",
    "record_type",
    "work_id",
    "attempt_id",
    "generation",
    "transition_id",
    "previous_transition_ref",
    "source",
    "target",
    "actor_bindings_id",
    "source_binding_id",
    "target_binding_id",
    "identity_record_ref",
    "handoff_id",
    "created_at_utc",
}
STATE_TRANSITION_FIELDS = {
    "schema_version",
    "record_type",
    "work_id",
    "attempt_id",
    "generation",
    "state_transition_id",
    "previous_state_transition_ref",
    "from_state",
    "to_state",
    "reason",
    "spec",
    "identity_record_ref",
    "created_at_utc",
}
FIELDS_BY_TYPE = {
    "approval": APPROVAL_FIELDS,
    "attempt": ATTEMPT_FIELDS,
    "orchestration_setup": ORCHESTRATION_SETUP_FIELDS,
    "recovery_input": RECOVERY_INPUT_FIELDS,
    "baseline_promotion": BASELINE_PROMOTION_FIELDS,
    "actor_binding": ACTOR_BINDING_FIELDS,
    "identity": IDENTITY_FIELDS,
    "implementation_result": IMPLEMENTATION_RESULT_FIELDS,
    "handoff": HANDOFF_FIELDS,
    "transition": TRANSITION_FIELDS,
    "state_transition": STATE_TRANSITION_FIELDS,
}
ID_FIELD_BY_TYPE = {
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
PAYLOAD_FIELDS_BY_EDGE = {
    ("pre_skim", "design"): {
        "orchestration_setup_ref",
        "baseline_identity_record_ref",
        "routing_record",
        "candidates",
    },
    ("design", "commander_window"): {
        "baseline_identity_record_ref",
        "changes_by_path",
        "forbidden_paths",
        "implementation_contract",
        "success_conditions",
        "rollback_plan",
        "required_tests",
    },
    ("commander_window", "implementation"): {
        "baseline_identity_record_ref",
        "design_handoff_id",
        "implementation_contract",
        "approval_id",
    },
    ("implementation", "post_skim"): {
        "implementation_result_ref",
        "changed_paths",
        "static_checks",
    },
    ("post_skim", "final_review"): {
        "implementation_result_ref",
        "reviewed_identity_record_ref",
        "design_handoff_id",
        "design_coverage",
        "candidates",
        "unplanned_changes",
    },
    ("final_review", "design_receipt"): {
        "reviewed_identity_record_ref",
        "post_skim_handoff_id",
        "verdict",
        "findings",
        "corrections",
    },
}
TERMINAL_PAYLOAD_FIELDS = {
    "reviewed_identity_record_ref",
    "final_review_handoff_id",
    "disposition",
    "reason",
}
TARGETS = STAGES + ("test_gate",)


class UnsafeInputError(Exception):
    """Raised when evidence bytes cannot be consumed safely."""


class Event:
    __slots__ = ("record", "sequence", "envelope")

    def __init__(
        self,
        record: dict[str, Any],
        sequence: int,
        envelope: dict[str, Any],
    ) -> None:
        self.record = record
        self.sequence = sequence
        self.envelope = envelope


class Findings:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []
        self._seen: set[tuple[str, str | None, str, bool, bool]] = set()

    def add(
        self,
        code: str,
        detail: str,
        record_ref: str | None = None,
        *,
        blocking: bool = True,
        unsafe: bool = False,
    ) -> None:
        key = (code, record_ref, detail, blocking, unsafe)
        if key in self._seen:
            return
        self._seen.add(key)
        finding: dict[str, Any] = {
            "code": code,
            "detail": detail,
            "blocking": blocking,
        }
        if record_ref is not None:
            finding["record_ref"] = record_ref
        if unsafe:
            finding["unsafe"] = True
        self.items.append(finding)

    def merge(self, other: "Findings", *, blocking: bool | None = None) -> None:
        for item in other.items:
            self.add(
                item["code"],
                item["detail"],
                item.get("record_ref"),
                blocking=item["blocking"] if blocking is None else blocking,
                unsafe=bool(item.get("unsafe")),
            )

    @property
    def blocking(self) -> bool:
        return any(item["blocking"] for item in self.items)

    @property
    def unsafe(self) -> bool:
        return any(item.get("unsafe") for item in self.items if item["blocking"])


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed


def _normal_path(value: Any) -> bool:
    try:
        normalize_workspace_relative_path(value)
    except EvidenceSafetyError:
        return False
    return True


def _sorted_unique_strings(value: Any, allowed: set[str] | None = None) -> bool:
    if not isinstance(value, list) or any(not _nonempty(item) for item in value):
        return False
    if value != sorted(value) or len(value) != len(set(value)):
        return False
    return allowed is None or all(item in allowed for item in value)


def validate_approval_submission(record: Any, expected_work_id: str) -> list[dict[str, str]]:
    """Return schema-v3 genesis approval findings for recorder initialization."""
    if not isinstance(record, dict):
        return [{"code": "approval_schema_invalid", "detail": "approval must be an object"}]
    version = record.get("schema_version")
    if version != SCHEMA_VERSION:
        code = "legacy_schema_rejected" if version in {1, 2} else "unsupported_schema_version"
        return [{"code": code, "detail": "approval schema_version must equal 3"}]
    findings: list[dict[str, str]] = []
    if set(record) != APPROVAL_FIELDS or record.get("record_type") != "approval":
        findings.append({"code": "approval_schema_invalid", "detail": "approval fields are not exact"})
        return findings
    for field in ("work_id", "attempt_id", "approval_id", "commander_actor_id"):
        if not _nonempty(record.get(field)):
            findings.append({"code": "approval_field_invalid", "detail": f"{field} must be non-empty"})
    if record.get("implementation_intensity") not in IMPLEMENTATION_INTENSITIES:
        findings.append({"code": "approval_intensity_invalid", "detail": "implementation_intensity enum is invalid"})
    if record.get("process_level") not in PROCESS_LEVELS:
        findings.append({"code": "approval_process_level_invalid", "detail": "process_level enum is invalid"})
    if record.get("work_id") != expected_work_id:
        findings.append({"code": "approval_work_mismatch", "detail": "approval work_id differs"})
    if not _sorted_unique_strings(record.get("protected_surfaces"), PROTECTED_SURFACES):
        findings.append({"code": "approval_surfaces_invalid", "detail": "protected surfaces are invalid"})
    try:
        normalize_scope_paths(record.get("scope_paths"))
    except EvidenceSafetyError:
        findings.append({"code": "approval_scope_invalid", "detail": "scope paths are invalid"})
    if not _normal_path(record.get("spec")):
        findings.append({"code": "approval_spec_invalid", "detail": "spec path is invalid"})
    if _utc(record.get("created_at_utc")) is None:
        findings.append({"code": "approval_utc_invalid", "detail": "created_at_utc is invalid"})
    return findings


def _event_ref(event: Event) -> str:
    record_type = event.record.get("record_type")
    id_field = ID_FIELD_BY_TYPE.get(record_type)
    value = event.record.get(id_field) if id_field else None
    return str(value) if _nonempty(value) else f"sequence:{event.sequence}"


def _attempt_matches(record: dict[str, Any], attempt: dict[str, Any]) -> bool:
    return (
        record.get("work_id") == attempt.get("work_id")
        and record.get("attempt_id") == attempt.get("attempt_id")
    )


def _scope_matches(record: dict[str, Any], attempt: dict[str, Any], generation: int | None = None) -> bool:
    return _attempt_matches(record, attempt) and (
        generation is None or record.get("generation") == generation
    )


def _record_key(record: dict[str, Any]) -> tuple[Any, ...] | None:
    record_type = record.get("record_type")
    id_field = ID_FIELD_BY_TYPE.get(record_type)
    if id_field is None:
        return None
    values = (record.get("work_id"), record.get("attempt_id"), record.get(id_field))
    if record_type not in {"approval", "attempt"}:
        values = (
            record.get("work_id"), record.get("attempt_id"),
            record.get("generation"), record.get(id_field),
        )
    if any(value is None or isinstance(value, (dict, list)) for value in values):
        return None
    return (record_type, *values)


def _validate_approval_shape(record: dict[str, Any], findings: Findings, ref: str) -> None:
    for item in validate_approval_submission(record, record.get("work_id") if isinstance(record, dict) else ""):
        findings.add(item["code"], item["detail"], ref)


def _validate_envelopes(
    envelopes: list[Any],
    findings: Findings,
) -> tuple[list[Event], dict[str, Any] | None]:
    accepted: list[Event] = []
    previous_hash: str | None = None
    previous_time: datetime | None = None
    genesis_approval: dict[str, Any] | None = None
    for expected_sequence, raw in enumerate(envelopes):
        if not isinstance(raw, dict):
            findings.add(
                "legacy_raw_record_rejected",
                "each JSONL row must be an envelope object",
                f"sequence:{expected_sequence}",
            )
            continue
        if "envelope_type" not in raw and "record_type" in raw:
            findings.add(
                "legacy_raw_record_rejected",
                "legacy raw orchestration records are not migrated",
                f"sequence:{expected_sequence}",
            )
            continue
        ref = f"sequence:{expected_sequence}"
        if raw.get("schema_version") != SCHEMA_VERSION:
            code = "legacy_schema_rejected" if raw.get("schema_version") in {1, 2} else "unsupported_schema_version"
            findings.add(code, "envelope must use schema version 3", ref)
            continue
        if set(raw) != ENVELOPE_FIELDS or raw.get("envelope_type") != ENVELOPE_TYPE:
            findings.add("envelope_schema", "envelope fields are not exact", ref)
            continue
        sequence = raw.get("sequence")
        if sequence != expected_sequence:
            findings.add("envelope_sequence", "envelope sequence is not contiguous", ref)
        if raw.get("previous_envelope_sha256") != previous_hash:
            findings.add("envelope_hash_chain", "previous envelope hash is invalid", ref)
        created = _utc(raw.get("created_at_utc"))
        if created is None:
            findings.add("envelope_utc", "envelope UTC is invalid", ref)
        elif previous_time is not None and created < previous_time:
            findings.add("envelope_utc", "envelope UTC moved backward", ref)
        status = raw.get("status")
        envelope_findings = raw.get("findings")
        if status not in {"accepted", "rejected"}:
            findings.add("envelope_status", "envelope status is invalid", ref)
        if not isinstance(envelope_findings, list) or any(
            not isinstance(item, dict)
            or set(item) != {"code", "detail"}
            or not _nonempty(item.get("code"))
            or not _nonempty(item.get("detail"))
            for item in (envelope_findings if isinstance(envelope_findings, list) else [])
        ):
            findings.add("envelope_findings", "envelope findings are invalid", ref)
            envelope_findings = []
        if status == "accepted" and envelope_findings:
            findings.add("envelope_findings", "accepted envelope has findings", ref)
        if status == "rejected" and not envelope_findings:
            findings.add("envelope_findings", "rejected envelope lacks findings", ref)
        record = raw.get("record")
        record_type = record.get("record_type") if isinstance(record, dict) else None
        id_field = ID_FIELD_BY_TYPE.get(record_type)
        record_id = record.get(id_field) if isinstance(record, dict) and id_field else None
        if raw.get("record_type") != record_type or raw.get("record_id") != record_id:
            findings.add("envelope_record_identity", "envelope record identity is invalid", ref)
        if not is_lower_hex64(raw.get("record_sha256")) or raw.get("record_sha256") != payload_sha256(record):
            findings.add("envelope_record_sha256", "record payload hash is invalid", ref)
        if not _nonempty(raw.get("producer_actor_id")) or not _nonempty(raw.get("recorder_actor_id")):
            findings.add("envelope_writer", "producer and recorder IDs are required", ref)
        if status == "rejected":
            for item in envelope_findings:
                findings.add(
                    f"rejected:{item['code']}",
                    item["detail"],
                    ref,
                    blocking=False,
                )
        elif status == "accepted" and isinstance(record, dict):
            accepted.append(Event(record, expected_sequence, raw))
        previous_hash = payload_sha256(raw)
        if created is not None:
            previous_time = created
    if not envelopes:
        findings.add("approval_genesis_missing", "evidence log is empty")
        return accepted, None
    if accepted:
        first = accepted[0]
        if first.sequence != 0 or first.record.get("record_type") != "approval":
            findings.add("approval_genesis_missing", "accepted approval must be sequence 0")
        else:
            genesis_approval = first.record
            _validate_approval_shape(genesis_approval, findings, _event_ref(first))
            if (
                first.envelope.get("producer_actor_id") != genesis_approval.get("commander_actor_id")
                or first.envelope.get("recorder_actor_id") != genesis_approval.get("commander_actor_id")
            ):
                findings.add("approval_genesis_scope", "genesis writer or approval ref differs", _event_ref(first))
    else:
        findings.add("approval_genesis_missing", "no accepted approval envelope exists")
    if genesis_approval is not None:
        for event in accepted:
            envelope = event.envelope
            if (
                envelope.get("work_id") != genesis_approval.get("work_id")
                or envelope.get("attempt_id") != genesis_approval.get("attempt_id")
                or envelope.get("recorder_actor_id") != genesis_approval.get("commander_actor_id")
            ):
                findings.add("approval_envelope_scope", "accepted envelope escaped genesis scope", _event_ref(event))
    return accepted, genesis_approval


def _deduplicate_records(
    events: list[Event], findings: Findings
) -> dict[str, list[Event]]:
    by_type = {record_type: [] for record_type in FIELDS_BY_TYPE}
    seen: dict[tuple[Any, ...], tuple[bytes, Event]] = {}
    for event in events:
        record = event.record
        ref = _event_ref(event)
        record_type = record.get("record_type")
        local_post = record_type == "handoff" and record.get("source_stage") == "post_skim"
        def add(code: str, detail: str) -> None:
            findings.add(code, detail, ref, blocking=not local_post)
        if record.get("schema_version") != SCHEMA_VERSION:
            code = "legacy_schema_rejected" if record.get("schema_version") in {1, 2} else "unsupported_schema_version"
            add(code, "accepted record schema must equal 3")
            continue
        if record_type not in FIELDS_BY_TYPE:
            add("record_type", "accepted record type is unknown")
            continue
        expected = FIELDS_BY_TYPE[record_type]
        if set(record) != expected:
            add("record_schema", f"missing={sorted(expected - set(record))}; extra={sorted(set(record) - expected)}")
            continue
        if _utc(record.get("created_at_utc")) is None:
            add("record_utc", "record UTC is invalid")
            continue
        if record_type not in {"approval", "attempt"} and not _nonnegative_int(record.get("generation")):
            add("record_generation", "generation must be a nonnegative integer")
            continue
        key = _record_key(record)
        id_field = ID_FIELD_BY_TYPE[record_type]
        if key is None or not _nonempty(record.get("work_id")) or not _nonempty(record.get("attempt_id")) or not _nonempty(record.get(id_field)):
            add("record_identity", "record identity fields are invalid")
            continue
        canonical = canonical_json_bytes(record)
        previous = seen.get(key)
        if previous is not None:
            if previous[0] == canonical:
                continue
            add("record_id_conflict", "accepted record ID has conflicting payload")
            continue
        seen[key] = (canonical, event)
        by_type[record_type].append(event)
    return by_type


def _validate_attempt(event: Event, approval: Event, findings: Findings) -> None:
    record = event.record
    ref = _event_ref(event)
    for field in ("work_id", "attempt_id", "approval_ref"):
        if not _nonempty(record.get(field)):
            findings.add("attempt_field", f"{field} must be non-empty", ref)
    approval_record = approval.record
    pairs = (
        ("work_id", "work_id"),
        ("attempt_id", "attempt_id"),
        ("approval_ref", "approval_id"),
    )
    for attempt_field, approval_field in pairs:
        if record.get(attempt_field) != approval_record.get(approval_field):
            findings.add("approval_scope_mismatch", f"{attempt_field} differs from approval", ref)
    if event.sequence <= approval.sequence:
        findings.add("attempt_append_order", "attempt must follow genesis approval", ref)


def _validate_bindings(
    attempt: Event,
    events: list[Event],
    findings: Findings,
) -> dict[str, Event]:
    chosen = [
        event
        for event in events
        if _scope_matches(event.record, attempt.record)
        and event.record.get("actor_bindings_id") == attempt.record.get("actor_bindings_id")
    ]
    if len(chosen) != len(STAGES):
        findings.add("binding_coverage", "binding set must contain exactly seven records")
    by_stage: dict[str, Event] = {}
    binding_ids: set[str] = set()
    for event in chosen:
        record = event.record
        ref = _event_ref(event)
        stage = record.get("stage")
        if stage not in STAGES or stage in by_stage:
            findings.add("binding_coverage", "binding stage is invalid or duplicated", ref)
            continue
        by_stage[stage] = event
        if record.get("actor_role") != ROLE_BY_STAGE[stage]:
            findings.add("binding_role", "stage-to-role binding is not exact", ref)
        if not _nonempty(record.get("binding_id")) or record.get("binding_id") in binding_ids:
            findings.add("binding_id", "binding ID is empty or duplicated", ref)
        binding_ids.add(record.get("binding_id"))
        if not _nonempty(record.get("actor_id")):
            findings.add("binding_actor", "actor ID is required", ref)
        if event.sequence >= attempt.sequence:
            findings.add("binding_setup_order", "binding must precede attempt setup", ref)
    if set(by_stage) == set(STAGES):
        if by_stage["design"].record["actor_id"] != by_stage["design_receipt"].record["actor_id"]:
            findings.add("design_actor_mismatch", "design stages must share one design actor")
        actors: dict[str, set[str]] = {}
        for event in by_stage.values():
            actors.setdefault(event.record["actor_id"], set()).add(event.record["actor_role"])
        for actor_id, roles in actors.items():
            if len(roles) > 1:
                findings.add("cross_role_actor_reuse", "actor is bound across roles", actor_id)
    return by_stage


def _validate_identity_event(
    event: Event,
    findings: Findings,
    workspace_root: Path | None = None,
) -> str | None:
    record = event.record
    ref = _event_ref(event)
    if not is_lower_hex64(record.get("snapshot_sha256")):
        findings.add("identity_sha256", "snapshot SHA must be lowercase 64hex", ref)
        return None
    try:
        computed = snapshot_identity(record.get("snapshot_payload"))
    except EvidenceSafetyError as error:
        findings.add("snapshot_schema", str(error), ref)
        return None
    if computed != record.get("snapshot_sha256"):
        findings.add("identity_snapshot_mismatch", "snapshot SHA differs from payload", ref)
    if record.get("epoch") == "baseline":
        generation = record.get("generation")
        expected_producer = "orchestration_setup" if generation == 0 else "baseline_promotion"
        predecessor = record.get("predecessor_identity_record_ref")
        if record.get("producer") != expected_producer or (generation == 0 and predecessor is not None) or (generation > 0 and not _nonempty(predecessor)):
            findings.add("baseline_identity_shape", "baseline identity shape is invalid", ref)
    elif record.get("epoch") == "result":
        if record.get("producer") != "implementation" or not _nonempty(record.get("predecessor_identity_record_ref")):
            findings.add("result_identity_shape", "result identity shape is invalid", ref)
    else:
        findings.add("identity_epoch", "identity epoch is invalid", ref)
    if workspace_root is None:
        return computed
    try:
        live = build_snapshot_payload(
            workspace_root,
            record["snapshot_payload"]["scope_paths"],
        )
        live_sha = snapshot_identity(live)
    except EvidenceSafetyError as error:
        findings.add(
            "current_snapshot_unsafe",
            str(error),
            ref,
            unsafe=True,
        )
        return None
    if live != record["snapshot_payload"] or live_sha != record["snapshot_sha256"]:
        findings.add("current_snapshot_mismatch", "current snapshot differs from R", ref)
    return live_sha


def _validate_handoff_shape(
    event: Event,
    attempt: Event,
    bindings: dict[str, Event],
    findings: Findings,
) -> None:
    record = event.record
    ref = _event_ref(event)
    source = record.get("source_stage")
    target = record.get("target_stage")
    if source not in STAGES:
        findings.add("handoff_edge", "handoff source is invalid", ref)
        return
    if record.get("actor_bindings_id") != attempt.record.get("actor_bindings_id"):
        findings.add("handoff_binding_set", "handoff binding set differs", ref)
    source_binding = bindings.get(source)
    if source_binding is None or record.get("source_binding_id") != source_binding.record.get("binding_id"):
        findings.add("handoff_source_binding", "source binding lookup failed", ref)
    elif event.envelope.get("producer_actor_id") != source_binding.record.get("actor_id"):
        findings.add("handoff_producer", "envelope producer is not source-stage actor", ref)
    payload = record.get("payload")
    if not isinstance(payload, dict):
        findings.add("handoff_payload", "handoff payload must be an object", ref)
        payload = {}
    if source == "design_receipt":
        commander = bindings.get("commander_window")
        if target is not None or record.get("target_binding_id") is not None:
            findings.add("terminal_reentry", "terminal receipt targets a stage", ref)
        if (
            record.get("recipient_actor_role") != "commander"
            or commander is None
            or record.get("recipient_binding_id") != commander.record.get("binding_id")
        ):
            findings.add("terminal_recipient", "terminal recipient is not commander", ref)
        if set(payload) != TERMINAL_PAYLOAD_FIELDS:
            findings.add("handoff_payload", "terminal payload fields are not exact", ref)
        elif payload.get("disposition") not in {"accept", "needs_rework", "stop"} or not _nonempty(payload.get("reason")):
            findings.add("terminal_payload", "terminal disposition or reason is invalid", ref)
    else:
        edge = (source, target)
        if edge not in EDGES:
            findings.add("handoff_edge", "handoff is not a consecutive edge", ref)
        target_binding = bindings.get(target)
        if target_binding is None or record.get("target_binding_id") != target_binding.record.get("binding_id"):
            findings.add("handoff_target_binding", "target binding lookup failed", ref)
        if record.get("recipient_actor_role") is not None or record.get("recipient_binding_id") is not None:
            findings.add("handoff_recipient", "non-terminal recipient fields must be null", ref)
        if edge in PAYLOAD_FIELDS_BY_EDGE and set(payload) != PAYLOAD_FIELDS_BY_EDGE[edge]:
            findings.add("handoff_payload", "edge payload fields are not exact", ref)
    if source == "post_skim":
        if not _nonempty(record.get("run_id")):
            findings.add("post_skim_run_id", "post-skim run ID is required", ref)
        supersedes = record.get("supersedes_handoff_ref")
        if supersedes is not None and not _nonempty(supersedes):
            findings.add("post_skim_supersedes", "supersedes ref is invalid", ref)
    elif record.get("run_id") is not None or record.get("supersedes_handoff_ref") is not None:
        findings.add("handoff_run_fields", "run fields are reserved for post-skim", ref)
    if not _normal_path(record.get("spec")):
        findings.add("handoff_spec", "handoff spec path is unsafe", ref)
    try:
        normalize_scope_paths(record.get("affected_paths"))
    except EvidenceSafetyError:
        findings.add("handoff_paths", "affected paths are unsafe", ref)
    evidence_refs = record.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs or any(not _nonempty(item) for item in evidence_refs):
        findings.add("handoff_evidence_refs", "evidence refs are required", ref)
    unresolved = record.get("unresolved")
    if not isinstance(unresolved, list):
        findings.add("handoff_unresolved", "unresolved must be an array", ref)
    elif unresolved:
        findings.add("unresolved_blocker", "handoff contains unresolved blockers", ref)


def _linear_chain(
    events: list[Event],
    id_field: str,
    previous_field: str,
    findings: Findings,
    prefix: str,
) -> list[Event]:
    if not events:
        findings.add(f"{prefix}_missing", f"{prefix} chain is missing")
        return []
    by_id = {event.record[id_field]: event for event in events}
    roots = [event for event in events if event.record.get(previous_field) is None]
    children: dict[str, list[Event]] = {}
    for event in events:
        parent = event.record.get(previous_field)
        if parent is not None:
            if parent not in by_id:
                findings.add(f"{prefix}_previous_missing", "previous record is missing", _event_ref(event))
            children.setdefault(parent, []).append(event)
    if len(roots) != 1:
        findings.add(f"{prefix}_root", f"{prefix} chain must have one root")
        return []
    if any(len(values) > 1 for values in children.values()):
        findings.add(f"{prefix}_branch", f"{prefix} chain may not branch")
    ordered: list[Event] = []
    current = roots[0]
    seen: set[str] = set()
    while True:
        current_id = current.record[id_field]
        if current_id in seen:
            findings.add(f"{prefix}_cycle", f"{prefix} chain contains a cycle", current_id)
            break
        seen.add(current_id)
        ordered.append(current)
        next_values = children.get(current_id, [])
        if not next_values:
            break
        next_event = next_values[0]
        if next_event.sequence <= current.sequence or _utc(next_event.record["created_at_utc"]) < _utc(current.record["created_at_utc"]):
            findings.add(f"{prefix}_append_order", f"{prefix} chain moved backward", _event_ref(next_event))
        current = next_event
    if seen != set(by_id):
        findings.add(f"{prefix}_coverage", f"{prefix} chain is disconnected")
    return ordered


def _base_result(target: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validator": VALIDATOR_NAME,
        "work": None,
        "attempt": None,
        "generation": None,
        "target": target,
        "valid": False,
        "state": "needs_review",
        "evidence_sequence": None,
        "evidence_log_sha256": None,
        "current_snapshot_sha256": None,
        "selected_refs": {},
        "findings": [],
        "validation_receipt": None,
        "validation_receipt_sha256": None,
    }


def _required_edge_count(target: str) -> int:
    return {
        "pre_skim": 0, "design": 1, "commander_window": 2,
        "implementation": 3, "post_skim": 4, "final_review": 5,
        "design_receipt": 6, "test_gate": 6,
    }[target]


def _checkpoint_record_index(record: dict[str, Any]) -> int | None:
    record_type = record.get("record_type")
    if record_type == "handoff":
        source = record.get("source_stage")
        if source == "design_receipt":
            return 7
        return STAGES.index(source) if source in STAGES else None
    if record_type == "transition":
        source = record.get("source")
        return STAGES.index(source) if source in STAGES else None
    if record_type == "identity" and record.get("epoch") == "result":
        return 3
    if record_type == "implementation_result":
        return 3
    if record_type == "state_transition":
        return 7
    return None


def _project_checkpoint_events(events: list[Event], target: str, current_generation: int, findings: Findings) -> list[Event]:
    required_edges = _required_edge_count(target)
    projected: list[Event] = []
    always = {"approval", "attempt", "orchestration_setup", "recovery_input", "baseline_promotion", "actor_binding"}
    for event in events:
        record_type = event.record.get("record_type")
        index = _checkpoint_record_index(event.record)
        include = record_type in always or (record_type == "identity" and event.record.get("epoch") == "baseline")
        if _nonnegative_int(event.record.get("generation")) and event.record.get("generation") < current_generation:
            include = True
        if index is not None and not (_nonnegative_int(event.record.get("generation")) and event.record.get("generation") < current_generation):
            include = (index < required_edges) or (target == "test_gate" and index == 7)
        elif record_type not in FIELDS_BY_TYPE:
            include = True
        if include:
            projected.append(event)
        else:
            findings.add("future_record_excluded", "later checkpoint record is nonblocking for requested prefix", _event_ref(event), blocking=False)
    return projected


def _validate_record_causality(
    event: Event,
    prior_events: list[Event],
    approval: Event,
    findings: Findings,
) -> None:
    """Validate one record only against records admitted earlier in the stream."""
    record = event.record
    record_type = record.get("record_type")
    ref = _event_ref(event)
    commander = approval.record.get("commander_actor_id")
    producer = event.envelope.get("producer_actor_id")
    work = record.get("work_id")
    attempt = record.get("attempt_id")
    generation = record.get("generation")

    def matches(candidate: Event, kind: str, id_field: str, value: Any, gen: int | None = generation) -> bool:
        other = candidate.record
        return (
            other.get("record_type") == kind
            and other.get(id_field) == value
            and other.get("work_id") == work
            and other.get("attempt_id") == attempt
            and (kind in {"approval", "attempt"} or gen is None or other.get("generation") == gen)
        )

    def resolve(kind: str, id_field: str, value: Any, gen: int | None = generation) -> Event | None:
        return next((candidate for candidate in reversed(prior_events) if matches(candidate, kind, id_field, value, gen)), None)

    bindings = [candidate for candidate in prior_events if candidate.record.get("record_type") == "actor_binding" and candidate.record.get("work_id") == work and candidate.record.get("attempt_id") == attempt and candidate.record.get("generation") == generation]
    binding_by_stage = {candidate.record.get("stage"): candidate for candidate in bindings}
    implementer = binding_by_stage.get("implementation")
    commander_types = {"attempt", "actor_binding", "orchestration_setup", "recovery_input", "baseline_promotion", "state_transition", "transition"}
    if record_type in commander_types and producer != commander:
        findings.add("causal_producer", "record producer must be approved commander", ref)
    if record_type in {"identity", "implementation_result"}:
        expected = commander if record.get("epoch") == "baseline" else (implementer.record.get("actor_id") if implementer else None)
        if implementer is None and (record_type == "implementation_result" or record.get("epoch") == "result"):
            findings.add("causal_binding_missing", "current implementer binding is missing", ref)
        if producer != expected:
            findings.add("causal_producer", "identity/result producer does not match current binding", ref)
    if record_type == "actor_binding":
        stage = record.get("stage")
        if stage not in STAGES or record.get("actor_role") != ROLE_BY_STAGE.get(stage):
            findings.add("causal_binding_role", "actor binding stage/role is not exact", ref)
        if not all(_nonempty(record.get(field)) for field in ("actor_bindings_id", "binding_id", "actor_id")):
            findings.add("causal_binding_identity", "actor binding IDs are required", ref)

    terminal = next((candidate for candidate in reversed(prior_events) if candidate.record.get("record_type") == "handoff" and candidate.record.get("source_stage") == "design_receipt" and candidate.record.get("work_id") == work and candidate.record.get("attempt_id") == attempt and candidate.record.get("generation") == generation), None)
    if terminal is not None and record_type in {"handoff", "transition", "implementation_result"}:
        findings.add("terminal_reentry", "same-generation handoff/transition/result follows terminal", ref)

    if record_type == "attempt":
        if record.get("approval_ref") != approval.record.get("approval_id"):
            findings.add("causal_approval_ref", "attempt approval reference differs", ref)
    elif record_type == "identity":
        _validate_identity_event(event, findings)
        predecessor = record.get("predecessor_identity_record_ref")
        if record.get("epoch") == "result":
            baseline = resolve("identity", "identity_record_id", predecessor)
            if baseline is None or baseline.record.get("epoch") != "baseline":
                findings.add("result_predecessor_missing", "result identity predecessor B is not admitted", ref)
        elif record.get("epoch") == "baseline" and generation and predecessor is not None:
            source = resolve("identity", "identity_record_id", predecessor, generation - 1)
            if source is None or source.record.get("epoch") != "result":
                findings.add("promotion_predecessor_missing", "promoted B predecessor R is not admitted", ref)
    elif record_type == "implementation_result":
        baseline = resolve("identity", "identity_record_id", record.get("baseline_identity_record_ref"))
        result_identity = resolve("identity", "identity_record_id", record.get("result_identity_record_ref"))
        if baseline is None or baseline.record.get("epoch") != "baseline" or result_identity is None or result_identity.record.get("epoch") != "result" or result_identity.record.get("predecessor_identity_record_ref") != record.get("baseline_identity_record_ref"):
            findings.add("implementation_identity_forward_ref", "implementation result B/R chain is not already admitted", ref)
    elif record_type == "recovery_input":
        source_generation = record.get("source_generation")
        source_result = resolve("implementation_result", "implementation_result_id", record.get("source_result_ref"), source_generation)
        if source_result is None:
            findings.add("recovery_source_forward_ref", "source implementation result is not admitted", ref)
    elif record_type == "baseline_promotion":
        recovery = resolve("recovery_input", "recovery_input_id", record.get("recovery_input_ref"))
        source = resolve("identity", "identity_record_id", record.get("source_result_identity_record_ref"), generation - 1 if isinstance(generation, int) else None)
        target = resolve("identity", "identity_record_id", record.get("target_baseline_identity_record_ref"))
        if recovery is None or source is None or target is None:
            findings.add("promotion_forward_ref", "promotion recovery/source R/target B must already be admitted", ref)
        elif source.record.get("epoch") != "result" or target.record.get("epoch") != "baseline" or target.record.get("predecessor_identity_record_ref") != source.record.get("identity_record_id") or target.record.get("snapshot_payload") != source.record.get("snapshot_payload") or target.record.get("snapshot_sha256") != source.record.get("snapshot_sha256"):
            findings.add("promotion_source_mismatch", "promotion does not preserve exact source R", ref)
        elif (
            recovery.record.get("source_generation") != generation - 1
            or (source_result := resolve(
                "implementation_result",
                "implementation_result_id",
                recovery.record.get("source_result_ref"),
                generation - 1,
            )) is None
            or source_result.record.get("result_identity_record_ref") != source.record.get("identity_record_id")
        ):
            findings.add("promotion_recovery_source_mismatch", "promotion source R differs from the recovery source result", ref)
    elif record_type == "orchestration_setup":
        baseline = resolve("identity", "identity_record_id", record.get("baseline_identity_record_ref"))
        current_bindings = [candidate for candidate in bindings if candidate.record.get("actor_bindings_id") == record.get("actor_bindings_id")]
        if record.get("approval_ref") != approval.record.get("approval_id"):
            findings.add("setup_approval_ref", "setup approval reference differs", ref)
        if baseline is None or len(current_bindings) != len(STAGES) or {candidate.record.get("stage") for candidate in current_bindings} != set(STAGES):
            findings.add("setup_forward_ref", "setup B or complete binding set is not admitted", ref)
        if generation == 0:
            if any(record.get(field) is not None for field in ("previous_setup_ref", "recovery_input_ref", "baseline_promotion_ref")):
                findings.add("setup_generation_zero_refs", "generation zero recovery references must be null", ref)
        else:
            previous = resolve("orchestration_setup", "orchestration_setup_id", record.get("previous_setup_ref"), generation - 1)
            recovery = resolve("recovery_input", "recovery_input_id", record.get("recovery_input_ref"))
            promotion = resolve("baseline_promotion", "baseline_promotion_id", record.get("baseline_promotion_ref"))
            if previous is None or recovery is None or promotion is None:
                findings.add("setup_recovery_forward_ref", "setup predecessor/recovery/promotion is not admitted", ref)
    elif record_type == "handoff":
        setup = next((candidate for candidate in reversed(prior_events) if candidate.record.get("record_type") == "orchestration_setup" and candidate.record.get("work_id") == work and candidate.record.get("attempt_id") == attempt and candidate.record.get("generation") == generation), None)
        handoff_bindings = {
            candidate.record.get("stage"): candidate
            for candidate in bindings
            if setup is not None and candidate.record.get("actor_bindings_id") == setup.record.get("actor_bindings_id")
        }
        source_binding = handoff_bindings.get(record.get("source_stage"))
        target_binding = handoff_bindings.get(record.get("target_stage"))
        if source_binding is None or record.get("source_binding_id") != source_binding.record.get("binding_id"):
            findings.add("handoff_source_binding_missing", "handoff source binding is not admitted", ref)
        elif producer != source_binding.record.get("actor_id"):
            findings.add("handoff_producer", "handoff producer is not bound source actor", ref)
        if record.get("source_stage") == "design_receipt":
            commander_binding = handoff_bindings.get("commander_window")
            if (
                commander_binding is None
                or record.get("target_binding_id") is not None
                or record.get("recipient_binding_id") != commander_binding.record.get("binding_id")
                or record.get("recipient_actor_role") != commander_binding.record.get("actor_role")
            ):
                findings.add("handoff_terminal_binding_missing", "terminal recipient commander binding is not admitted", ref)
        elif (
            target_binding is None
            or record.get("target_binding_id") != target_binding.record.get("binding_id")
            or record.get("recipient_binding_id") is not None
            or record.get("recipient_actor_role") is not None
            or record.get("actor_bindings_id") != target_binding.record.get("actor_bindings_id")
        ):
            findings.add("handoff_target_binding_missing", "handoff target/binding-set reference is not admitted", ref)
        if source_binding is not None and record.get("actor_bindings_id") != source_binding.record.get("actor_bindings_id"):
            findings.add("handoff_binding_set_missing", "handoff source binding set is not admitted", ref)
        if setup is None:
            findings.add("handoff_setup_missing", "handoff generation setup is not admitted", ref)
        else:
            _validate_handoff_shape(event, setup, handoff_bindings, findings)
        source_stage = record.get("source_stage")
        if source_stage in STAGES and source_stage != STAGES[0]:
            previous_edge = EDGES[STAGES.index(source_stage) - 1]
            admitted_transitions = [candidate for candidate in prior_events if candidate.record.get("record_type") == "transition" and candidate.record.get("work_id") == work and candidate.record.get("attempt_id") == attempt and candidate.record.get("generation") == generation]
            previous_transition = admitted_transitions[-1] if admitted_transitions else None
            if previous_transition is None or (previous_transition.record.get("source"), previous_transition.record.get("target")) != previous_edge:
                findings.add("handoff_previous_transition_missing", "prior authority transition is not admitted", ref)
            else:
                current_utc = _utc(record.get("created_at_utc"))
                previous_utc = _utc(previous_transition.record.get("created_at_utc"))
                if current_utc is not None and previous_utc is not None and current_utc < previous_utc:
                    findings.add("handoff_utc_regression", "handoff UTC precedes prior transition", ref)
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        refs: list[tuple[str, str, Any, int | None]] = []
        if source_stage == "pre_skim":
            refs.append(("orchestration_setup", "orchestration_setup_id", payload.get("orchestration_setup_ref"), generation))
        elif source_stage == "commander_window":
            refs.append(("handoff", "handoff_id", payload.get("design_handoff_id"), generation))
        elif source_stage == "implementation":
            refs.append(("implementation_result", "implementation_result_id", payload.get("implementation_result_ref"), generation))
        elif source_stage == "post_skim":
            refs.extend((("implementation_result", "implementation_result_id", payload.get("implementation_result_ref"), generation), ("identity", "identity_record_id", payload.get("reviewed_identity_record_ref"), generation), ("handoff", "handoff_id", payload.get("design_handoff_id"), generation)))
        elif source_stage == "final_review":
            refs.extend((("identity", "identity_record_id", payload.get("reviewed_identity_record_ref"), generation), ("handoff", "handoff_id", payload.get("post_skim_handoff_id"), generation)))
        elif source_stage == "design_receipt":
            refs.extend((("identity", "identity_record_id", payload.get("reviewed_identity_record_ref"), generation), ("handoff", "handoff_id", payload.get("final_review_handoff_id"), generation)))
        if any(resolve(kind, id_field, value, gen) is None for kind, id_field, value, gen in refs):
            findings.add("handoff_forward_ref", "handoff references an unadmitted record", ref)
    elif record_type == "transition":
        handoff = resolve("handoff", "handoff_id", record.get("handoff_id"))
        setup = next((candidate for candidate in reversed(prior_events) if candidate.record.get("record_type") == "orchestration_setup" and candidate.record.get("work_id") == work and candidate.record.get("attempt_id") == attempt and candidate.record.get("generation") == generation), None)
        transition_bindings = {
            candidate.record.get("stage"): candidate
            for candidate in bindings
            if setup is not None and candidate.record.get("actor_bindings_id") == setup.record.get("actor_bindings_id")
        }
        source_binding = transition_bindings.get(record.get("source"))
        target_binding = transition_bindings.get(record.get("target"))
        previous_ref = record.get("previous_transition_ref")
        previous = None if previous_ref is None else resolve("transition", "transition_id", previous_ref)
        siblings = [candidate for candidate in prior_events if candidate.record.get("record_type") == "transition" and candidate.record.get("previous_transition_ref") == previous_ref and candidate.record.get("work_id") == work and candidate.record.get("attempt_id") == attempt and candidate.record.get("generation") == generation]
        if handoff is None or (previous_ref is not None and previous is None):
            findings.add("transition_forward_ref", "transition handoff/previous record is not admitted", ref)
        elif handoff.record.get("source_stage") != record.get("source") or handoff.record.get("target_stage") != record.get("target"):
            findings.add("transition_handoff_mismatch", "transition edge differs from admitted handoff", ref)
        edge = (record.get("source"), record.get("target"))
        if edge in EDGES:
            edge_index = EDGES.index(edge)
            admitted_transitions = [candidate for candidate in prior_events if candidate.record.get("record_type") == "transition" and candidate.record.get("work_id") == work and candidate.record.get("attempt_id") == attempt and candidate.record.get("generation") == generation]
            expected_previous = admitted_transitions[-1] if admitted_transitions else None
            if edge_index and (
                expected_previous is None
                or (expected_previous.record.get("source"), expected_previous.record.get("target")) != EDGES[edge_index - 1]
            ):
                findings.add("transition_previous_missing", "preceding authority transition is not the latest admitted transition", ref)
            if not edge_index and expected_previous is not None:
                findings.add("transition_root_not_first", "first authority transition must precede every later transition", ref)
            expected_previous_id = expected_previous.record.get("transition_id") if expected_previous else None
            if previous_ref != expected_previous_id:
                findings.add("transition_previous_not_latest", "transition predecessor is not the preceding authority transition", ref)
        current_utc = _utc(record.get("created_at_utc"))
        handoff_utc = _utc(handoff.record.get("created_at_utc")) if handoff is not None else None
        previous_utc = _utc(previous.record.get("created_at_utc")) if previous is not None else None
        if current_utc is not None and handoff_utc is not None and current_utc < handoff_utc:
            findings.add("transition_utc_regression", "transition UTC precedes its handoff", ref)
        if current_utc is not None and previous_utc is not None and current_utc < previous_utc:
            findings.add("transition_utc_regression", "transition UTC precedes its predecessor", ref)
        if (
            source_binding is None
            or target_binding is None
            or record.get("source_binding_id") != source_binding.record.get("binding_id")
            or record.get("target_binding_id") != target_binding.record.get("binding_id")
            or record.get("actor_bindings_id") != source_binding.record.get("actor_bindings_id")
            or record.get("actor_bindings_id") != target_binding.record.get("actor_bindings_id")
        ):
            findings.add("transition_binding_missing", "transition bindings are not admitted", ref)
        if record.get("identity_record_ref") is not None and resolve("identity", "identity_record_id", record.get("identity_record_ref")) is None:
            findings.add("transition_identity_forward_ref", "transition identity is not admitted", ref)
        if siblings:
            findings.add("transition_branch", "transition chain branches", ref)
    elif record_type == "state_transition":
        previous_ref = record.get("previous_state_transition_ref")
        previous = None if previous_ref is None else next((candidate for candidate in reversed(prior_events) if candidate.record.get("record_type") == "state_transition" and candidate.record.get("state_transition_id") == previous_ref and candidate.record.get("work_id") == work and candidate.record.get("attempt_id") == attempt), None)
        siblings = [candidate for candidate in prior_events if candidate.record.get("record_type") == "state_transition" and candidate.record.get("previous_state_transition_ref") == previous_ref and candidate.record.get("work_id") == work and candidate.record.get("attempt_id") == attempt]
        if previous_ref is not None and previous is None:
            findings.add("state_forward_ref", "state predecessor is not admitted", ref)
        if record.get("identity_record_ref") is not None and resolve("identity", "identity_record_id", record.get("identity_record_ref")) is None:
            findings.add("state_identity_forward_ref", "state identity is not admitted", ref)
        if record.get("to_state") not in WORK_STATES or not _nonempty(record.get("reason")) or not _normal_path(record.get("spec")):
            findings.add("state_transition_payload", "state transition payload is invalid", ref)
        if siblings:
            findings.add("state_transition_branch", "state transition chain branches", ref)


def _validate_causal_sequence(events: list[Event], approval: Event, findings: Findings) -> None:
    prior: list[Event] = []
    for event in sorted(events, key=lambda item: item.sequence):
        if event.record.get("record_type") != "approval":
            local = Findings()
            _validate_record_causality(event, prior, approval, local)
            is_post = event.record.get("record_type") == "handoff" and event.record.get("source_stage") == "post_skim"
            findings.merge(local, blocking=False if is_post else None)
        prior.append(event)


def _audit_generation_singletons(
    by_type: dict[str, list[Event]],
    attempt: Event,
    findings: Findings,
) -> None:
    """Audit singleton groups in every generation retained by checkpoint projection."""
    groups: list[tuple[str, tuple[Any, ...], Event]] = []
    for event in by_type["orchestration_setup"]:
        if _attempt_matches(event.record, attempt.record):
            groups.append(("setup", (event.record.get("generation"),), event))
    for event in by_type["actor_binding"]:
        if _attempt_matches(event.record, attempt.record):
            groups.append(("binding_stage", (event.record.get("generation"), event.record.get("stage")), event))
    for event in by_type["implementation_result"]:
        if _attempt_matches(event.record, attempt.record):
            groups.append(("implementation_result", (event.record.get("generation"),), event))
    for event in by_type["handoff"]:
        if not _attempt_matches(event.record, attempt.record):
            continue
        source = event.record.get("source_stage")
        if source == "post_skim":
            continue
        kind = "terminal" if source == "design_receipt" else "handoff_edge"
        key = (event.record.get("generation"),) if kind == "terminal" else (event.record.get("generation"), source, event.record.get("target_stage"))
        groups.append((kind, key, event))
    seen: dict[tuple[str, tuple[Any, ...]], Event] = {}
    for kind, key, event in sorted(groups, key=lambda item: item[2].sequence):
        composite = (kind, key)
        previous = seen.get(composite)
        if previous is not None:
            findings.add(
                f"{kind}_singleton",
                "singleton group contains multiple accepted records",
                _event_ref(event),
            )
        else:
            seen[composite] = event


def _evaluate_post_candidates(
    events: list[Event],
    approval: Event,
    generation: int,
    reserved_post_runs: dict[str, int],
) -> tuple[Event | None, dict[int, Findings]]:
    """Evaluate post-skim candidates locally; only a zero-blocking candidate advances latest."""
    scoped = [
        event for event in events
        if event.record.get("work_id") == approval.record.get("work_id")
        and event.record.get("attempt_id") == approval.record.get("attempt_id")
        and event.record.get("generation") == generation
    ]
    setups = [event for event in scoped if event.record.get("record_type") == "orchestration_setup"]
    setup = setups[0] if len(setups) == 1 else None
    binding_events = [event for event in scoped if event.record.get("record_type") == "actor_binding"]
    bindings = {
        event.record.get("stage"): event
        for event in binding_events
        if setup is not None and event.record.get("actor_bindings_id") == setup.record.get("actor_bindings_id")
    }
    implementations = [event for event in scoped if event.record.get("record_type") == "implementation_result"]
    implementation = implementations[0] if len(implementations) == 1 else None
    identities = {
        event.record.get("identity_record_id"): event
        for event in scoped
        if event.record.get("record_type") == "identity"
    }
    result_identity = identities.get(implementation.record.get("result_identity_record_ref")) if implementation is not None else None
    baseline_identity = identities.get(setup.record.get("baseline_identity_record_ref")) if setup is not None else None
    design_candidates = [event for event in scoped if event.record.get("record_type") == "handoff" and event.record.get("source_stage") == "design"]
    design = design_candidates[0] if len(design_candidates) == 1 else None
    candidates = sorted(
        (event for event in scoped if event.record.get("record_type") == "handoff" and event.record.get("source_stage") == "post_skim"),
        key=lambda event: event.sequence,
    )
    latest: Event | None = None
    local_by_sequence: dict[int, Findings] = {}
    for event in candidates:
        local = Findings()
        local_by_sequence[event.sequence] = local
        if setup is None:
            local.add("post_skim_setup", "post-skim generation setup does not resolve exactly", _event_ref(event))
        else:
            _validate_handoff_shape(event, setup, bindings, local)
        if event.record.get("affected_paths") != approval.record.get("scope_paths"):
            local.add("handoff_snapshot_scope", "handoff scope differs from approval", _event_ref(event))
        payload = event.record.get("payload") if isinstance(event.record.get("payload"), dict) else {}
        if (
            implementation is None
            or baseline_identity is None
            or result_identity is None
            or result_identity.record.get("epoch") != "result"
            or implementation.record.get("baseline_identity_record_ref") != baseline_identity.record.get("identity_record_id")
            or result_identity.record.get("predecessor_identity_record_ref") != baseline_identity.record.get("identity_record_id")
            or result_identity.record.get("producer") != "implementation"
        ):
            local.add("post_skim_current_result", "current implementation result/R does not resolve exactly", _event_ref(event))
        elif (
            payload.get("implementation_result_ref") != implementation.record.get("implementation_result_id")
            or payload.get("reviewed_identity_record_ref") != result_identity.record.get("identity_record_id")
        ):
            local.add("post_skim_current_result", "candidate does not reference current implementation result/R", _event_ref(event))
        if design is None or payload.get("design_handoff_id") != design.record.get("handoff_id"):
            local.add("post_skim_design_ref", "candidate does not reference the current design handoff", _event_ref(event))
        run_id = event.record.get("run_id")
        if not _nonempty(run_id):
            local.add("post_skim_run_id_invalid", "post-skim run ID is required", _event_ref(event))
        elif reserved_post_runs.get(run_id, 0) != 1:
            local.add("post_skim_run_id_reused", "post-skim run ID is not uniquely reserved", _event_ref(event))
        prior = [candidate for candidate in events if candidate.sequence < event.sequence]
        _validate_record_causality(event, prior, approval, local)
        if any(candidate.record.get("record_type") == "transition" and candidate.record.get("work_id") == event.record.get("work_id") and candidate.record.get("attempt_id") == event.record.get("attempt_id") and candidate.record.get("generation") == generation and (candidate.record.get("source"), candidate.record.get("target")) == ("post_skim", "final_review") for candidate in prior):
            local.add("post_skim_closed", "post-skim transition already closed candidate admission", _event_ref(event))
        expected_supersedes = latest.record.get("handoff_id") if latest is not None else None
        if event.record.get("supersedes_handoff_ref") != expected_supersedes:
            local.add("post_skim_latest_valid", "candidate does not supersede latest valid post-skim", _event_ref(event))
        if latest is not None:
            current_utc = _utc(event.record.get("created_at_utc"))
            latest_utc = _utc(latest.record.get("created_at_utc"))
            if current_utc is None or latest_utc is None or current_utc <= latest_utc:
                local.add("post_skim_utc_not_newer", "post-skim UTC must be strictly newer than latest valid", _event_ref(event))
        if not local.blocking:
            latest = event
    return latest, local_by_sequence


def _validate_setup_generation(
    setup: Event,
    by_type: dict[str, list[Event]],
    approval: Event,
    findings: Findings,
) -> tuple[Event | None, Event | None]:
    record = setup.record
    ref = _event_ref(setup)
    generation = record["generation"]
    for field in ("work_id", "attempt_id", "orchestration_setup_id", "approval_ref", "baseline_identity_record_ref", "actor_bindings_id"):
        if not _nonempty(record.get(field)):
            findings.add("setup_field", f"{field} must be non-empty", ref)
    if record.get("approval_ref") != approval.record.get("approval_id"):
        findings.add("setup_approval_ref", "setup approval reference differs", ref)
    identities = {
        e.record["identity_record_id"]: e for e in by_type["identity"]
        if _scope_matches(e.record, record, generation)
    }
    baseline = identities.get(record.get("baseline_identity_record_ref"))
    if baseline is None:
        findings.add("baseline_missing", "setup baseline identity is missing", ref)
    recovery: Event | None = None
    promotion: Event | None = None
    if generation == 0:
        if any(record.get(field) is not None for field in (
            "previous_setup_ref", "recovery_input_ref", "baseline_promotion_ref"
        )):
            findings.add("generation_zero_refs", "generation zero recovery references must be null", ref)
        if baseline is not None and (
            baseline.record.get("epoch") != "baseline"
            or baseline.record.get("producer") != "orchestration_setup"
            or baseline.record.get("predecessor_identity_record_ref") is not None
        ):
            findings.add("baseline_identity_shape", "generation zero B producer is invalid", _event_ref(baseline))
    else:
        for field in ("previous_setup_ref", "recovery_input_ref", "baseline_promotion_ref"):
            if not _nonempty(record.get(field)):
                findings.add("recovery_setup_ref", f"{field} is required", ref)
        previous = [e for e in by_type["orchestration_setup"] if
                    _scope_matches(e.record, record, generation - 1)
                    and e.record.get("orchestration_setup_id") == record.get("previous_setup_ref")]
        recoveries = [e for e in by_type["recovery_input"] if
                      _scope_matches(e.record, record, generation)
                      and e.record.get("recovery_input_id") == record.get("recovery_input_ref")]
        promotions = [e for e in by_type["baseline_promotion"] if
                      _scope_matches(e.record, record, generation)
                      and e.record.get("baseline_promotion_id") == record.get("baseline_promotion_ref")]
        if len(previous) != 1:
            findings.add("previous_setup_ref", "previous setup must resolve in generation N-1", ref)
        if len(recoveries) != 1:
            findings.add("recovery_input_ref", "same-generation recovery input must resolve", ref)
        else:
            recovery = recoveries[0]
        if len(promotions) != 1:
            findings.add("baseline_promotion_ref", "same-generation baseline promotion must resolve", ref)
        else:
            promotion = promotions[0]
        if recovery is not None:
            rr = recovery.record
            if rr.get("source_generation") != generation - 1 or rr.get("recovery_kind") not in {"rework", "resume", "revise"}:
                findings.add("recovery_input_generation", "recovery must advance source generation by one", _event_ref(recovery))
            if not _nonempty(rr.get("source_result_ref")) or not _nonempty(rr.get("recovery_bundle_ref")):
                findings.add("recovery_input_refs", "recovery source result and bundle are required", _event_ref(recovery))
            source_results = [e for e in by_type["implementation_result"] if
                              _scope_matches(e.record, record, generation - 1)
                              and e.record.get("implementation_result_id") == rr.get("source_result_ref")]
            if len(source_results) != 1:
                findings.add("recovery_source_result", "recovery source result must resolve in generation N-1", _event_ref(recovery))
            refs = rr.get("failure_evidence_refs")
            if not isinstance(refs, list) or any(not _nonempty(x) for x in refs):
                findings.add("recovery_evidence_refs", "failure evidence refs must be strings", _event_ref(recovery))
        if promotion is not None:
            pr = promotion.record
            if recovery is None or pr.get("recovery_input_ref") != recovery.record.get("recovery_input_id"):
                findings.add("promotion_recovery_ref", "promotion recovery ref differs", _event_ref(promotion))
            source = next((e for e in by_type["identity"] if
                           _scope_matches(e.record, record, generation - 1)
                           and e.record.get("identity_record_id") == pr.get("source_result_identity_record_ref")), None)
            target = next((e for e in by_type["identity"] if
                           _scope_matches(e.record, record, generation)
                           and e.record.get("identity_record_id") == pr.get("target_baseline_identity_record_ref")), None)
            if source is None or source.record.get("generation") != generation - 1 or source.record.get("epoch") != "result":
                findings.add("promotion_source_result", "promotion source must be prior-generation R", _event_ref(promotion))
            if target is None or target is not baseline or target.record.get("epoch") != "baseline":
                findings.add("promotion_target_baseline", "promotion target must be current B", _event_ref(promotion))
            if source is not None and target is not None:
                source_results = [e for e in by_type["implementation_result"] if _scope_matches(e.record, record, generation - 1) and e.record.get("implementation_result_id") == (recovery.record.get("source_result_ref") if recovery else None)]
                if len(source_results) != 1 or source_results[0].record.get("result_identity_record_ref") != source.record.get("identity_record_id"):
                    findings.add("recovery_source_r_mismatch", "recovery source result does not resolve to promotion source R", _event_ref(promotion))
                if target.record.get("snapshot_payload") != source.record.get("snapshot_payload") or target.record.get("snapshot_sha256") != source.record.get("snapshot_sha256"):
                    findings.add("promotion_snapshot_mismatch", "new B must preserve prior R full snapshot exactly", _event_ref(promotion))
                if target.record.get("predecessor_identity_record_ref") != source.record.get("identity_record_id") or target.record.get("producer") != "baseline_promotion":
                    findings.add("promotion_identity_shape", "new B predecessor and producer are invalid", _event_ref(target))
    return baseline, recovery


def _validate_checkpoint(
    root: Path,
    by_type: dict[str, list[Event]],
    approval: Event,
    attempt: Event,
    generation: int,
    target: str,
    findings: Findings,
    selected_refs: dict[str, Any],
    reserved_post_runs: dict[str, int],
) -> tuple[Event | None, dict[str, Any] | None, str | None, str | None]:
    setups = [e for e in by_type["orchestration_setup"] if _scope_matches(e.record, attempt.record, generation)]
    if len(setups) != 1:
        findings.add("setup_coverage", "current generation must have exactly one setup")
        return None, None, None, None
    setup = setups[0]
    baseline, recovery = _validate_setup_generation(setup, by_type, approval, findings)
    selected_refs["orchestration_setup_id"] = setup.record.get("orchestration_setup_id")
    if recovery is not None:
        selected_refs["recovery_input_id"] = recovery.record.get("recovery_input_id")
    bindings = _validate_bindings(setup, by_type["actor_binding"], findings)
    if baseline is not None:
        _validate_identity_event(baseline, findings)
        if baseline.record.get("snapshot_payload", {}).get("scope_paths") != approval.record.get("scope_paths"):
            findings.add("baseline_scope", "B snapshot scope differs from approval", _event_ref(baseline))
        selected_refs["baseline_identity_record_id"] = baseline.record.get("identity_record_id")
    identities = {e.record["identity_record_id"]: e for e in by_type["identity"] if _scope_matches(e.record, attempt.record, generation)}
    implementations = [e for e in by_type["implementation_result"] if _scope_matches(e.record, attempt.record, generation)]
    if len(implementations) > 1:
        findings.add("implementation_result_singleton", "generation may contain only one implementation result")
    implementation = implementations[0] if len(implementations) == 1 else None
    result_identity: Event | None = None
    if implementation is not None:
        if implementation.record.get("baseline_identity_record_ref") != (baseline.record.get("identity_record_id") if baseline else None):
            findings.add("implementation_baseline_ref", "implementation result does not reference current B", _event_ref(implementation))
        result_identity = identities.get(implementation.record.get("result_identity_record_ref"))
        if result_identity is None:
            findings.add("result_identity_missing", "implementation R is missing", _event_ref(implementation))
        else:
            _validate_identity_event(result_identity, findings)
            if result_identity.record.get("snapshot_payload", {}).get("scope_paths") != approval.record.get("scope_paths"):
                findings.add("result_scope", "R snapshot scope differs from approval", _event_ref(result_identity))
            if result_identity.record.get("epoch") != "result" or result_identity.record.get("producer") != "implementation" or result_identity.record.get("predecessor_identity_record_ref") != (baseline.record.get("identity_record_id") if baseline else None):
                findings.add("result_identity_shape", "R producer or predecessor is invalid", _event_ref(result_identity))
            selected_refs["result_identity_record_id"] = result_identity.record.get("identity_record_id")
            selected_refs["implementation_result_id"] = implementation.record.get("implementation_result_id")
    handoffs = [e for e in by_type["handoff"] if _scope_matches(e.record, attempt.record, generation)]
    for event in handoffs:
        if event.record.get("source_stage") == "post_skim":
            continue
        local = Findings()
        _validate_handoff_shape(event, setup, bindings, local)
        if event.record.get("affected_paths") != approval.record.get("scope_paths"):
            local.add("handoff_snapshot_scope", "handoff scope differs from approval", _event_ref(event))
        findings.merge(local)
    checkpoint_events = sorted(
        (event for values in by_type.values() for event in values),
        key=lambda event: event.sequence,
    )
    latest_post, post_local_findings = _evaluate_post_candidates(
        checkpoint_events,
        approval,
        generation,
        reserved_post_runs,
    )
    for event in (event for event in handoffs if event.record.get("source_stage") == "post_skim"):
        local = post_local_findings.get(event.sequence, Findings())
        findings.merge(local, blocking=False)
        if local.blocking:
            findings.add("post_skim_candidate_rejected", "invalid post-skim candidate did not advance latest-valid", _event_ref(event), blocking=False)
    edge_events: list[Event] = []
    for edge in EDGES:
        matches = [e for e in handoffs if (e.record.get("source_stage"), e.record.get("target_stage")) == edge]
        if edge == ("post_skim", "final_review"):
            if latest_post is not None:
                edge_events.append(latest_post)
        elif len(matches) == 1:
            edge_events.append(matches[0])
        elif matches:
            findings.add("handoff_coverage", "non-post-skim edge must be unique", str(edge))
    required_edges = _required_edge_count(target)
    for index in range(required_edges):
        edge = EDGES[index]
        matches = [e for e in edge_events if (e.record.get("source_stage"), e.record.get("target_stage")) == edge]
        if len(matches) != 1:
            findings.add("handoff_prefix_missing", f"required edge is missing: {edge}")
    for event in edge_events:
        index = EDGES.index((event.record.get("source_stage"), event.record.get("target_stage")))
        if index >= required_edges and target != "test_gate":
            findings.add("checkpoint_future_evidence", "accepted evidence extends beyond requested checkpoint", _event_ref(event), blocking=False)
    by_source = {e.record.get("source_stage"): e for e in edge_events}
    baseline_id = baseline.record.get("identity_record_id") if baseline else None
    result_id = result_identity.record.get("identity_record_id") if result_identity else None
    pre = by_source.get("pre_skim")
    if pre is not None:
        payload = pre.record["payload"]
        if payload.get("orchestration_setup_ref") != setup.record.get("orchestration_setup_id") or payload.get("baseline_identity_record_ref") != baseline_id:
            findings.add("pre_skim_refs", "pre-skim setup or B reference differs", _event_ref(pre))
    design = by_source.get("design")
    if design is not None and design.record["payload"].get("baseline_identity_record_ref") != baseline_id:
        findings.add("design_baseline_ref", "design baseline reference differs", _event_ref(design))
    commander = by_source.get("commander_window")
    if commander is not None:
        payload = commander.record["payload"]
        if payload.get("baseline_identity_record_ref") != baseline_id or payload.get("design_handoff_id") != (design.record.get("handoff_id") if design else None) or payload.get("approval_id") != approval.record.get("approval_id"):
            findings.add("commander_refs", "commander handoff references differ", _event_ref(commander))
    implementation_handoff = by_source.get("implementation")
    if implementation_handoff is not None:
        expected_implementation = implementation.record.get("implementation_result_id") if implementation else None
        if implementation_handoff.record["payload"].get("implementation_result_ref") != expected_implementation:
            findings.add("implementation_refs", "implementation handoff/result bridge differs", _event_ref(implementation_handoff))
    final = by_source.get("final_review")
    if final is not None:
        payload = final.record["payload"]
        if payload.get("reviewed_identity_record_ref") != result_id or payload.get("post_skim_handoff_id") != (latest_post.record.get("handoff_id") if latest_post else None) or payload.get("verdict") != "accept":
            findings.add("final_review_refs", "final review does not accept latest current R", _event_ref(final))
        selected_refs["final_review_handoff_id"] = final.record.get("handoff_id")
    transitions = [e for e in by_type["transition"] if _scope_matches(e.record, attempt.record, generation)]
    ordered = _linear_chain(transitions, "transition_id", "previous_transition_ref", findings, "transition") if transitions else []
    if len(ordered) < required_edges:
        findings.add("transition_prefix_missing", "transition prefix is incomplete")
    for index, event in enumerate(ordered):
        if index >= len(EDGES) or (event.record.get("source"), event.record.get("target")) != EDGES[index]:
            findings.add("transition_edge", "transition chain is not the authority prefix", _event_ref(event))
            continue
        handoff = next((h for h in edge_events if (h.record.get("source_stage"), h.record.get("target_stage")) == EDGES[index]), None)
        if handoff is None or event.record.get("handoff_id") != handoff.record.get("handoff_id"):
            findings.add("transition_handoff_ref", "transition handoff reference differs", _event_ref(event))
        source_binding = bindings.get(event.record.get("source"))
        target_binding = bindings.get(event.record.get("target"))
        if event.record.get("actor_bindings_id") != setup.record.get("actor_bindings_id") or source_binding is None or event.record.get("source_binding_id") != source_binding.record.get("binding_id") or target_binding is None or event.record.get("target_binding_id") != target_binding.record.get("binding_id"):
            findings.add("transition_binding_ref", "transition binding references differ", _event_ref(event))
        expected_identity = baseline_id if index < 3 else result_id
        if event.record.get("identity_record_ref") != expected_identity:
            findings.add("transition_identity_ref", "transition identity epoch differs", _event_ref(event))
        if handoff is not None and event.sequence <= handoff.sequence:
            findings.add("transition_causal_order", "transition must follow its handoff", _event_ref(event))
        if handoff is not None:
            handoff_utc = _utc(handoff.record.get("created_at_utc"))
            transition_utc = _utc(event.record.get("created_at_utc"))
            if handoff_utc is not None and transition_utc is not None and transition_utc < handoff_utc:
                findings.add("transition_utc_regression", "transition UTC precedes its handoff", _event_ref(event))
        if index + 1 < len(EDGES):
            next_handoff = next((h for h in edge_events if (h.record.get("source_stage"), h.record.get("target_stage")) == EDGES[index + 1]), None)
            if next_handoff is not None:
                if next_handoff.sequence <= event.sequence:
                    findings.add("handoff_causal_order", "next handoff must follow the preceding transition", _event_ref(next_handoff))
                transition_utc = _utc(event.record.get("created_at_utc"))
                next_utc = _utc(next_handoff.record.get("created_at_utc"))
                if transition_utc is not None and next_utc is not None and next_utc < transition_utc:
                    findings.add("handoff_utc_regression", "next handoff UTC precedes the preceding transition", _event_ref(next_handoff))
    terminal_matches = [e for e in handoffs if e.record.get("source_stage") == "design_receipt"]
    if len(terminal_matches) > 1:
        findings.add("terminal_singleton", "generation may contain only one terminal receipt")
    terminal = terminal_matches[0] if len(terminal_matches) == 1 else None
    if terminal is not None:
        final_transition = ordered[5] if len(ordered) > 5 else None
        if final_transition is None or terminal.sequence <= final_transition.sequence:
            findings.add("terminal_causal_order", "terminal receipt must follow the final transition", _event_ref(terminal))
        elif (
            (terminal_utc := _utc(terminal.record.get("created_at_utc"))) is not None
            and (transition_utc := _utc(final_transition.record.get("created_at_utc"))) is not None
            and terminal_utc < transition_utc
        ):
            findings.add("terminal_utc_regression", "terminal UTC precedes the final transition", _event_ref(terminal))
        for event in [*handoffs, *transitions]:
            if event is not terminal and event.sequence > terminal.sequence:
                findings.add("terminal_reentry", "same-generation stage evidence follows terminal", _event_ref(event))
    if target == "test_gate":
        if terminal is None:
            findings.add("terminal_receipt_missing", "test gate requires one terminal design receipt")
        else:
            payload = terminal.record.get("payload", {})
            final = next((e for e in edge_events if e.record.get("source_stage") == "final_review"), None)
            if payload.get("disposition") != "accept" or payload.get("reviewed_identity_record_ref") != (result_identity.record.get("identity_record_id") if result_identity else None) or payload.get("final_review_handoff_id") != (final.record.get("handoff_id") if final else None):
                findings.add("terminal_receipt_invalid", "terminal receipt does not accept current R/final review", _event_ref(terminal))
            selected_refs["design_receipt_handoff_id"] = terminal.record.get("handoff_id")
    elif terminal is not None:
        findings.add("terminal_reentry", "terminal receipt is only consumed by test_gate", _event_ref(terminal), blocking=False)
    if result_identity is not None and latest_post is not None:
        payload = latest_post.record.get("payload", {})
        if payload.get("reviewed_identity_record_ref") != result_identity.record.get("identity_record_id") or payload.get("implementation_result_ref") != implementation.record.get("implementation_result_id"):
            findings.add("post_skim_result_ref", "latest post-skim does not preserve current R", _event_ref(latest_post))
        selected_refs["post_skim_handoff_id"] = latest_post.record.get("handoff_id")
        selected_refs["post_skim_run_id"] = latest_post.record.get("run_id")
    snapshot_event = baseline if target in {"pre_skim", "design", "commander_window", "implementation"} else result_identity
    if snapshot_event is None:
        findings.add("snapshot_epoch_missing", "checkpoint snapshot identity is missing")
        return None, None, None, recovery.record.get("recovery_bundle_ref") if recovery else None
    live_sha = _validate_identity_event(snapshot_event, findings, root)
    return snapshot_event, snapshot_event.record.get("snapshot_payload"), live_sha, recovery.record.get("recovery_bundle_ref") if recovery else None


def validate_envelopes(
    workspace_root: Path | str,
    envelopes: list[Any],
    expected_work_id: str,
    attempt_id: str,
    target: str,
    *,
    evidence_log_sha256: str | None = None,
    evidence_log_relative_path: str | None = None,
) -> dict[str, Any]:
    result = _base_result(target)
    findings = Findings()
    try:
        root = safe_workspace_root(workspace_root)
    except EvidenceSafetyError as error:
        findings.add("workspace_root_unsafe", str(error), unsafe=True)
        result.update(state="waiting_human", findings=findings.items)
        return result
    if target not in TARGETS or not _nonempty(expected_work_id) or not _nonempty(attempt_id):
        findings.add("target_invalid", "work-id, attempt-id, and checkpoint target are required")
        result["findings"] = findings.items
        return result
    accepted, genesis = _validate_envelopes(envelopes, findings)
    if genesis is not None and (genesis.get("work_id") != expected_work_id or genesis.get("attempt_id") != attempt_id):
        findings.add("expected_scope_mismatch", "expected work/attempt differs from genesis")
    for event in accepted:
        if event.record.get("work_id") != expected_work_id or event.record.get("attempt_id") != attempt_id:
            findings.add("record_scope_escape", "accepted record escaped expected work/attempt", _event_ref(event))
    raw_generation_events = [e for e in accepted if e.record.get("record_type") in {"orchestration_setup", "recovery_input", "baseline_promotion"} and e.record.get("work_id") == expected_work_id and e.record.get("attempt_id") == attempt_id and _nonnegative_int(e.record.get("generation"))]
    raw_generations = sorted({e.record["generation"] for e in raw_generation_events})
    generation = raw_generations[-1] if raw_generations else 0
    projected = _project_checkpoint_events(accepted, target, generation, findings)
    by_type = _deduplicate_records(projected, findings)
    approvals = [e for e in by_type["approval"] if e.record.get("attempt_id") == attempt_id]
    attempts = [e for e in by_type["attempt"] if e.record.get("attempt_id") == attempt_id]
    if len(approvals) != 1 or len(attempts) != 1:
        findings.add("attempt_coverage", "approval and attempt must each resolve exactly once", attempt_id)
        result.update(attempt=attempt_id, findings=findings.items)
        return result
    approval, attempt = approvals[0], attempts[0]
    _validate_attempt(attempt, approval, findings)
    _audit_generation_singletons(by_type, attempt, findings)
    causal_events = sorted(
        (event for values in by_type.values() for event in values),
        key=lambda item: item.sequence,
    )
    _validate_causal_sequence(causal_events, approval, findings)
    generation_events = (
        by_type["orchestration_setup"]
        + by_type["recovery_input"]
        + by_type["baseline_promotion"]
    )
    generations = sorted({e.record.get("generation") for e in generation_events if _attempt_matches(e.record, attempt.record) and _nonnegative_int(e.record.get("generation"))})
    setup_generations = sorted({e.record.get("generation") for e in by_type["orchestration_setup"] if _attempt_matches(e.record, attempt.record) and _nonnegative_int(e.record.get("generation"))})
    if not generations or setup_generations != list(range(generations[-1] + 1)):
        findings.add("generation_chain", "setup generations must be contiguous from zero")
        generation = max(generation, generations[-1] if generations else 0)
    elif generations[-1] != generation:
        findings.add("generation_projection_mismatch", "current generation controls were excluded")
    for event in by_type["state_transition"]:
        if _attempt_matches(event.record, attempt.record) and not _nonnegative_int(event.record.get("generation")):
            findings.add("state_generation", "state transition generation is invalid", _event_ref(event))
    states = [e for e in by_type["state_transition"] if _attempt_matches(e.record, attempt.record)]
    state_ids = [event.record.get("state_transition_id") for event in states]
    if len(state_ids) != len(set(state_ids)):
        findings.add("state_transition_id_reused", "state transition ID is attempt-global and may not repeat")
    if target == "test_gate" and not states:
        findings.add("state_transition_missing", "test gate requires a nonempty state chain")
    if states:
        ordered_states = _linear_chain(states, "state_transition_id", "previous_state_transition_ref", findings, "state_transition")
        identity_ids = {e.record.get("identity_record_id") for e in by_type["identity"] if _attempt_matches(e.record, attempt.record)}
        for index, event in enumerate(ordered_states):
            record = event.record
            if record.get("to_state") not in WORK_STATES or not _nonempty(record.get("reason")) or not _normal_path(record.get("spec")):
                findings.add("state_transition_payload", "state transition payload is invalid", _event_ref(event))
            if index == 0 and record.get("from_state") is not None:
                findings.add("state_transition_root", "first from_state must be null", _event_ref(event))
            if index > 0 and record.get("from_state") != ordered_states[index - 1].record.get("to_state"):
                findings.add("state_transition_causal", "state transition does not inherit prior state", _event_ref(event))
            if record.get("identity_record_ref") is not None and record.get("identity_record_ref") not in identity_ids:
                findings.add("state_transition_identity", "state identity lookup failed", _event_ref(event))
        for previous, current in zip(ordered_states, ordered_states[1:]):
            if current.record.get("generation", -1) < previous.record.get("generation", -1):
                findings.add("state_generation_regression", "state chain generation moved backward", _event_ref(current))
        if target == "test_gate" and ordered_states and ordered_states[-1].record.get("to_state") != "running":
            findings.add("test_gate_state", "current work state is not running", _event_ref(ordered_states[-1]))
        if target == "test_gate" and ordered_states and ordered_states[-1].record.get("generation") != generation:
            findings.add("test_gate_state_generation", "latest state does not belong to current generation", _event_ref(ordered_states[-1]))
    selected_refs: dict[str, Any] = {"approval_id": approval.record.get("approval_id")}
    reserved_post_runs: dict[str, int] = {}
    for envelope in envelopes:
        if not isinstance(envelope, dict) or not isinstance(envelope.get("record"), dict):
            continue
        record = envelope["record"]
        run_id = record.get("run_id")
        if record.get("record_type") == "handoff" and record.get("source_stage") == "post_skim" and _nonempty(run_id):
            reserved_post_runs[run_id] = reserved_post_runs.get(run_id, 0) + 1
    snapshot_event, snapshot_payload, live_sha, recovery_bundle_ref = _validate_checkpoint(
        root, by_type, approval, attempt, generation, target, findings, selected_refs, reserved_post_runs
    )
    if evidence_log_sha256 is None:
        raw = b"".join(canonical_json_bytes(e) + b"\n" for e in envelopes)
        evidence_log_sha256 = bytes_sha256(raw)
    if evidence_log_relative_path is None:
        evidence_log_relative_path = evidence_log_path(root, expected_work_id).relative_to(root).as_posix()
    evidence_sequence = len(envelopes) - 1 if envelopes else None
    valid = not findings.blocking
    receipt = None
    receipt_sha = None
    if valid and snapshot_event is not None and snapshot_payload is not None:
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "receipt_type": "orchestration_validation",
            "validator": VALIDATOR_NAME,
            "work_id": expected_work_id,
            "attempt_id": attempt_id,
            "generation": generation,
            "target": target,
            "evidence_log_path": evidence_log_relative_path,
            "evidence_log_sha256": evidence_log_sha256,
            "evidence_sequence": evidence_sequence,
            "snapshot_identity_record_id": snapshot_event.record["identity_record_id"],
            "snapshot_payload": snapshot_payload,
            "snapshot_sha256": snapshot_event.record["snapshot_sha256"],
            "recovery_bundle_ref": recovery_bundle_ref,
            "selected_refs": selected_refs,
        }
        receipt_sha = payload_sha256(receipt)
    result.update({
        "work": expected_work_id, "attempt": attempt_id,
        "generation": generation, "target": target, "valid": valid,
        "state": "ready_for_test" if valid else ("waiting_human" if findings.unsafe else "needs_review"),
        "evidence_sequence": evidence_sequence, "evidence_log_sha256": evidence_log_sha256,
        "current_snapshot_sha256": live_sha, "selected_refs": selected_refs,
        "findings": findings.items, "validation_receipt": receipt,
        "validation_receipt_sha256": receipt_sha,
    })
    return result


def validate_submission(existing: list[Any], candidate: Any, producer_actor_id: str) -> list[dict[str, str]]:
    """Return deterministic semantic admission findings for one candidate record."""
    findings: list[dict[str, str]] = []
    if not isinstance(candidate, dict):
        return [{"code": "record_not_object", "detail": "record must be an object"}]
    version = candidate.get("schema_version")
    if version != SCHEMA_VERSION:
        code = "legacy_schema_rejected" if version in {1, 2} else "unsupported_schema_version"
        findings.append({"code": code, "detail": "schema_version must equal 3"})
        return findings
    record_type = candidate.get("record_type")
    expected = FIELDS_BY_TYPE.get(record_type)
    if expected is None or set(candidate) != expected:
        findings.append({"code": "record_schema_invalid", "detail": "record fields are not exact"})
        return findings
    if record_type == "approval":
        findings.append({"code": "approval_genesis_only", "detail": "approval may only be the accepted genesis"})
        return findings
    if _utc(candidate.get("created_at_utc")) is None:
        findings.append({"code": "record_utc_invalid", "detail": "created_at_utc is invalid"})
    if not _nonempty(producer_actor_id):
        findings.append({"code": "producer_actor_id_invalid", "detail": "producer actor is required"})
    accepted, genesis = _validate_envelopes(existing, Findings())
    if genesis is None:
        findings.append({"code": "approval_genesis_missing", "detail": "accepted approval genesis is required"})
        return findings
    for field in ("work_id", "attempt_id"):
        if candidate.get(field) != genesis.get(field):
            findings.append({"code": "approval_scope_mismatch", "detail": f"record {field} differs from approval"})
    if record_type in {"attempt", "orchestration_setup"} and candidate.get("approval_ref") != genesis.get("approval_id"):
        findings.append({"code": "approval_reference_mismatch", "detail": "approval_ref differs from genesis"})
    if record_type not in {"approval", "attempt"} and not _nonnegative_int(candidate.get("generation")):
        findings.append({"code": "record_generation_invalid", "detail": "generation must be a nonnegative integer"})
    if record_type == "identity":
        try:
            computed = snapshot_identity(candidate.get("snapshot_payload"))
        except EvidenceSafetyError as error:
            findings.append({"code": "snapshot_schema_invalid", "detail": str(error)})
        else:
            if computed != candidate.get("snapshot_sha256"):
                findings.append({"code": "snapshot_sha256_mismatch", "detail": "snapshot hash differs from full payload"})
            if candidate["snapshot_payload"].get("scope_paths") != genesis.get("scope_paths"):
                findings.append({"code": "approval_scope_mismatch", "detail": "identity scope differs from approval"})
    if record_type == "handoff" and candidate.get("affected_paths") != genesis.get("scope_paths"):
        findings.append({"code": "approval_scope_mismatch", "detail": "handoff scope differs from approval"})
    scoped_generation = [
        event for event in accepted
        if event.record.get("work_id") == candidate.get("work_id")
        and event.record.get("attempt_id") == candidate.get("attempt_id")
        and event.record.get("generation") == candidate.get("generation")
    ]
    if record_type == "orchestration_setup" and any(event.record.get("record_type") == "orchestration_setup" for event in scoped_generation):
        findings.append({"code": "setup_singleton", "detail": "generation already has an orchestration setup"})
    elif record_type == "actor_binding" and any(event.record.get("record_type") == "actor_binding" and event.record.get("stage") == candidate.get("stage") for event in scoped_generation):
        findings.append({"code": "binding_stage_singleton", "detail": "generation already has a binding for this stage"})
    elif record_type == "implementation_result" and any(event.record.get("record_type") == "implementation_result" for event in scoped_generation):
        findings.append({"code": "implementation_result_singleton", "detail": "generation already has an implementation result"})
    elif record_type == "handoff":
        source_stage = candidate.get("source_stage")
        target_stage = candidate.get("target_stage")
        if source_stage == "post_skim":
            if any(event.record.get("record_type") == "transition" and (event.record.get("source"), event.record.get("target")) == ("post_skim", "final_review") for event in scoped_generation):
                findings.append({"code": "post_skim_closed", "detail": "post-skim transition already consumed the latest candidate"})
        elif source_stage == "design_receipt":
            if any(event.record.get("record_type") == "handoff" and event.record.get("source_stage") == "design_receipt" for event in scoped_generation):
                findings.append({"code": "terminal_singleton", "detail": "generation already has a terminal design receipt"})
        elif any(event.record.get("record_type") == "handoff" and event.record.get("source_stage") == source_stage and event.record.get("target_stage") == target_stage for event in scoped_generation):
            findings.append({"code": "handoff_edge_singleton", "detail": "generation already has this non-post handoff edge"})
    if record_type == "state_transition":
        attempt_states = [
            event for event in accepted
            if event.record.get("record_type") == "state_transition"
            and event.record.get("work_id") == candidate.get("work_id")
            and event.record.get("attempt_id") == candidate.get("attempt_id")
        ]
        if any(event.record.get("state_transition_id") == candidate.get("state_transition_id") for event in attempt_states):
            findings.append({"code": "state_transition_id_reused", "detail": "state transition ID is attempt-global"})
        latest_state = max(attempt_states, key=lambda event: event.sequence) if attempt_states else None
        expected_previous = latest_state.record.get("state_transition_id") if latest_state else None
        expected_from = latest_state.record.get("to_state") if latest_state else None
        if candidate.get("previous_state_transition_ref") != expected_previous:
            findings.append({"code": "state_previous_not_latest", "detail": "state predecessor must be the latest accepted state"})
        if candidate.get("from_state") != expected_from:
            findings.append({"code": "state_from_mismatch", "detail": "from_state must inherit the latest accepted to_state"})
        if latest_state is not None:
            current_utc = _utc(candidate.get("created_at_utc"))
            latest_utc = _utc(latest_state.record.get("created_at_utc"))
            if current_utc is not None and latest_utc is not None and current_utc < latest_utc:
                findings.append({"code": "state_utc_regression", "detail": "state UTC precedes the latest accepted state"})
    approval_event = next((event for event in accepted if event.record.get("record_type") == "approval"), None)
    candidate_event = Event(
        candidate,
        len(existing),
        {"producer_actor_id": producer_actor_id},
    )
    reserved_runs: dict[str, int] = {}
    for envelope in existing:
        if not isinstance(envelope, dict) or not isinstance(envelope.get("record"), dict):
            continue
        record = envelope["record"]
        run_id = record.get("run_id")
        if record.get("record_type") == "handoff" and record.get("source_stage") == "post_skim" and _nonempty(run_id):
            reserved_runs[run_id] = reserved_runs.get(run_id, 0) + 1
    if record_type == "handoff" and candidate.get("source_stage") == "post_skim" and _nonempty(candidate.get("run_id")):
        run_id = candidate["run_id"]
        reserved_runs[run_id] = reserved_runs.get(run_id, 0) + 1
    if approval_event is not None and not findings and record_type == "handoff" and candidate.get("source_stage") == "post_skim":
        _, local_by_sequence = _evaluate_post_candidates(
            [*accepted, candidate_event],
            approval_event,
            candidate.get("generation"),
            reserved_runs,
        )
        local = local_by_sequence.get(candidate_event.sequence, Findings())
        findings.extend({"code": item["code"], "detail": item["detail"]} for item in local.items)
    elif approval_event is not None and not findings:
        causal = Findings()
        _validate_record_causality(candidate_event, accepted, approval_event, causal)
        findings.extend({"code": item["code"], "detail": item["detail"]} for item in causal.items)
    if approval_event is not None and record_type == "transition" and (candidate.get("source"), candidate.get("target")) == ("post_skim", "final_review"):
        latest_post, local_by_sequence = _evaluate_post_candidates(
            accepted,
            approval_event,
            candidate.get("generation"),
            reserved_runs,
        )
        referenced = next((event for event in accepted if event.record.get("record_type") == "handoff" and event.record.get("work_id") == candidate.get("work_id") and event.record.get("attempt_id") == candidate.get("attempt_id") and event.record.get("generation") == candidate.get("generation") and event.record.get("handoff_id") == candidate.get("handoff_id")), None)
        if referenced is None or local_by_sequence.get(referenced.sequence, Findings()).blocking:
            findings.append({"code": "post_transition_candidate_invalid", "detail": "post transition references an invalid or missing candidate"})
        elif latest_post is None or candidate.get("handoff_id") != latest_post.record.get("handoff_id"):
            findings.append({"code": "post_transition_candidate_stale", "detail": "post transition does not consume current latest-valid candidate"})
    return findings


def _decode_envelope_stream(raw: bytes) -> list[Any]:
    if not raw or not raw.endswith(b"\n"):
        raise UnsafeInputError("partial_or_empty_evidence_log")
    values: list[Any] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line:
            raise UnsafeInputError(f"blank_evidence_line:{line_number}")
        try:
            values.append(json.loads(line.decode("utf-8")))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise UnsafeInputError(f"unreadable_evidence_line:{line_number}") from error
    return values


def validate_evidence_log(
    workspace_root: Path | str,
    work_id: str,
    attempt_id: str,
    target: str,
) -> dict[str, Any]:
    root = safe_workspace_root(workspace_root)
    path = evidence_log_path(root, work_id)
    raw = safe_read_bytes(root, path)
    envelopes = _decode_envelope_stream(raw)
    return validate_envelopes(
        root,
        envelopes,
        work_id,
        attempt_id,
        target,
        evidence_log_sha256=bytes_sha256(raw),
        evidence_log_relative_path=path.relative_to(root).as_posix(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--work-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--target", required=True, choices=TARGETS)
    args = parser.parse_args(argv)
    try:
        result = validate_evidence_log(args.workspace_root, args.work_id, args.attempt_id, args.target)
        exit_code = 0 if result["valid"] else (3 if result["state"] == "waiting_human" else 2)
    except (EvidenceSafetyError, UnsafeInputError) as error:
        result = _base_result(args.target)
        result["work"] = args.work_id
        result["attempt"] = args.attempt_id
        result["state"] = "waiting_human"
        result["findings"] = [
            {
                "code": "unsafe_or_unreadable_input",
                "detail": str(error),
                "blocking": True,
                "unsafe": True,
            }
        ]
        exit_code = 3
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
