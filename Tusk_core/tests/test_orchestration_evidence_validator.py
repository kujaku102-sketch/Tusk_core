import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = CORE_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))
TOOL_PATH = CORE_ROOT / "tools" / "orchestration_evidence_validator.py"
SPEC = importlib.util.spec_from_file_location("orchestration_evidence_validator", TOOL_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

WORK_ID = "core-orchestration-evidence-fixture"
ATTEMPT_ID = "orchestration-evidence:fixture:1"
APPROVAL_ID = "approval:orchestration-evidence-fixture"
GENERATION = 0
SCOPE_PATHS = ["Tusk_core/target.txt"]
SPEC_PATH = "Tusk_core/specs/CORE_ORCHESTRATION_EVIDENCE_SPEC.md"
SURFACES = []
ACTOR_BINDINGS_ID = "bindings:orchestration-fixture:g0"
ACTORS = {
    "pre_skim": "skim-pre",
    "design": "design",
    "commander_window": "commander",
    "implementation": "implementer",
    "post_skim": "skim-post",
    "final_review": "reviewer",
    "design_receipt": "design",
}


def timestamp(value):
    return f"2026-08-21T00:{value // 60:02d}:{value % 60:02d}Z"


def snapshot_for_bytes(raw):
    payload = {
        "algorithm": "sha256-path-snapshot-v1",
        "path_snapshot": [
            {
                "path": SCOPE_PATHS[0],
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
                "state": "file",
            }
        ],
        "scope_paths": SCOPE_PATHS,
    }
    return payload, VALIDATOR.snapshot_identity(payload)


def approval_record():
    return {
        "schema_version": 3,
        "record_type": "approval",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "approval_id": APPROVAL_ID,
        "implementation_intensity": "LOW",
        "process_level": "P0",
        "protected_surfaces": SURFACES,
        "scope_paths": SCOPE_PATHS,
        "commander_actor_id": ACTORS["commander_window"],
        "spec": SPEC_PATH,
    }


def binding_records():
    return [
        {
            "schema_version": 3,
            "record_type": "actor_binding",
            "work_id": WORK_ID,
            "attempt_id": ATTEMPT_ID,
            "generation": GENERATION,
            "actor_bindings_id": ACTOR_BINDINGS_ID,
            "binding_id": f"binding:{stage}",
            "stage": stage,
            "actor_role": VALIDATOR.ROLE_BY_STAGE[stage],
            "actor_id": ACTORS[stage],
        }
        for stage in VALIDATOR.STAGES
    ]


def identity_record(identity_id, epoch, raw, predecessor, producer):
    payload, digest = snapshot_for_bytes(raw)
    return {
        "schema_version": 3,
        "record_type": "identity",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "generation": GENERATION,
        "identity_record_id": identity_id,
        "epoch": epoch,
        "snapshot_payload": payload,
        "snapshot_sha256": digest,
        "producer": producer,
        "predecessor_identity_record_ref": predecessor,
    }


def attempt_record():
    return {
        "schema_version": 3,
        "record_type": "attempt",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "approval_ref": APPROVAL_ID,
    }


def setup_record():
    return {
        "schema_version": 3,
        "record_type": "orchestration_setup",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "generation": GENERATION,
        "orchestration_setup_id": "setup:orchestration-fixture:g0",
        "approval_ref": APPROVAL_ID,
        "previous_setup_ref": None,
        "recovery_input_ref": None,
        "baseline_promotion_ref": None,
        "baseline_identity_record_ref": "B",
        "actor_bindings_id": ACTOR_BINDINGS_ID,
    }


def handoff_record(source, target, handoff_id, payload, *, run_id=None, supersedes=None):
    terminal = source == "design_receipt"
    return {
        "schema_version": 3,
        "record_type": "handoff",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "generation": GENERATION,
        "handoff_id": handoff_id,
        "source_stage": source,
        "target_stage": target,
        "actor_bindings_id": ACTOR_BINDINGS_ID,
        "source_binding_id": f"binding:{source}",
        "target_binding_id": None if terminal else f"binding:{target}",
        "recipient_actor_role": "commander" if terminal else None,
        "recipient_binding_id": "binding:commander_window" if terminal else None,
        "spec": SPEC_PATH,
        "affected_paths": SCOPE_PATHS,
        "decision": "proceed",
        "payload": payload,
        "evidence_refs": ["evidence:fixture"],
        "unresolved": [],
        "run_id": run_id,
        "supersedes_handoff_ref": supersedes,
    }


def transition_record(index, handoff_id):
    source, target = VALIDATOR.EDGES[index]
    return {
        "schema_version": 3,
        "record_type": "transition",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "generation": GENERATION,
        "transition_id": f"transition:{index + 1}",
        "previous_transition_ref": None if index == 0 else f"transition:{index}",
        "source": source,
        "target": target,
        "actor_bindings_id": ACTOR_BINDINGS_ID,
        "source_binding_id": f"binding:{source}",
        "target_binding_id": f"binding:{target}",
        "identity_record_ref": "B" if index < 3 else "R",
        "handoff_id": handoff_id,
    }


def valid_records():
    approval = approval_record()
    baseline = identity_record("B", "baseline", b"baseline", None, "orchestration_setup")
    result = identity_record("R", "result", b"result", "B", "implementation")
    attempt = attempt_record()
    setup = setup_record()
    state = {
        "schema_version": 3,
        "record_type": "state_transition",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "generation": GENERATION,
        "state_transition_id": "state:1",
        "previous_state_transition_ref": None,
        "from_state": None,
        "to_state": "running",
        "reason": "approved one-shot recovery",
        "spec": SPEC_PATH,
        "identity_record_ref": "B",
    }
    pre = handoff_record(
        "pre_skim",
        "design",
        "handoff:pre",
        {
            "orchestration_setup_ref": setup["orchestration_setup_id"],
            "baseline_identity_record_ref": "B",
            "routing_record": {},
            "candidates": [],
        },
    )
    design = handoff_record(
        "design",
        "commander_window",
        "handoff:design",
        {
            "baseline_identity_record_ref": "B",
            "changes_by_path": {},
            "forbidden_paths": [],
            "implementation_contract": {},
            "success_conditions": [],
            "rollback_plan": [],
            "required_tests": [],
        },
    )
    commander = handoff_record(
        "commander_window",
        "implementation",
        "handoff:commander",
        {
            "baseline_identity_record_ref": "B",
            "design_handoff_id": "handoff:design",
            "implementation_contract": {},
            "approval_id": APPROVAL_ID,
        },
    )
    implementation = {
        "schema_version": 3,
        "record_type": "implementation_result",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "generation": GENERATION,
        "implementation_result_id": "implementation:R",
        "baseline_identity_record_ref": "B",
        "result_identity_record_ref": "R",
    }
    implementation_handoff = handoff_record(
        "implementation",
        "post_skim",
        "handoff:implementation",
        {
            "implementation_result_ref": "implementation:R",
            "changed_paths": SCOPE_PATHS,
            "static_checks": [],
        },
    )
    post = handoff_record(
        "post_skim",
        "final_review",
        "handoff:post:valid",
        {
            "implementation_result_ref": "implementation:R",
            "reviewed_identity_record_ref": "R",
            "design_handoff_id": "handoff:design",
            "design_coverage": [],
            "candidates": [],
            "unplanned_changes": [],
        },
        run_id="post-run:valid",
    )
    final = handoff_record(
        "final_review",
        "design_receipt",
        "handoff:final",
        {
            "reviewed_identity_record_ref": "R",
            "post_skim_handoff_id": "handoff:post:valid",
            "verdict": "accept",
            "findings": [],
            "corrections": [],
        },
    )
    terminal = handoff_record(
        "design_receipt",
        None,
        "handoff:receipt",
        {
            "reviewed_identity_record_ref": "R",
            "final_review_handoff_id": "handoff:final",
            "disposition": "accept",
            "reason": "review complete",
        },
    )
    return [
        approval,
        attempt,
        baseline,
        *binding_records(),
        setup,
        state,
        pre,
        transition_record(0, "handoff:pre"),
        design,
        transition_record(1, "handoff:design"),
        commander,
        transition_record(2, "handoff:commander"),
        result,
        implementation,
        implementation_handoff,
        transition_record(3, "handoff:implementation"),
        post,
        transition_record(4, "handoff:post:valid"),
        final,
        transition_record(5, "handoff:final"),
        terminal,
    ]


def generation_one_records():
    records = valid_records()
    r0 = next(r for r in records if r.get("record_type") == "identity" and r.get("identity_record_id") == "R")
    recovery = {
        "schema_version": 3, "record_type": "recovery_input", "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID, "generation": 1, "recovery_input_id": "recovery:g1",
        "source_generation": 0, "source_result_ref": "implementation:R", "recovery_kind": "revise",
        "failure_evidence_refs": ["failure:g0"], "recovery_bundle_ref": "bundle:g1",
    }
    b1 = copy.deepcopy(r0)
    b1.update({
        "generation": 1, "identity_record_id": "B1", "epoch": "baseline",
        "producer": "baseline_promotion", "predecessor_identity_record_ref": "R",
    })
    promotion = {
        "schema_version": 3, "record_type": "baseline_promotion", "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID, "generation": 1, "baseline_promotion_id": "promotion:g1",
        "recovery_input_ref": "recovery:g1", "source_result_identity_record_ref": "R",
        "target_baseline_identity_record_ref": "B1",
    }
    bindings = []
    for record in binding_records():
        item = copy.deepcopy(record)
        item.update(generation=1, actor_bindings_id="bindings:g1", binding_id=f"binding:g1:{item['stage']}")
        bindings.append(item)
    setup = {
        "schema_version": 3, "record_type": "orchestration_setup", "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID, "generation": 1, "orchestration_setup_id": "setup:g1",
        "approval_ref": APPROVAL_ID, "previous_setup_ref": "setup:orchestration-fixture:g0",
        "recovery_input_ref": "recovery:g1", "baseline_promotion_ref": "promotion:g1",
        "baseline_identity_record_ref": "B1", "actor_bindings_id": "bindings:g1",
    }
    r1 = identity_record("R1", "result", b"result-1", "B1", "implementation")
    r1["generation"] = 1
    implementation = {
        "schema_version": 3, "record_type": "implementation_result", "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID, "generation": 1, "implementation_result_id": "implementation:R1",
        "baseline_identity_record_ref": "B1", "result_identity_record_ref": "R1",
    }
    handoffs = [copy.deepcopy(r) for r in records if r.get("record_type") == "handoff"]
    id_map = {r["handoff_id"]: r["handoff_id"].replace("handoff:", "handoff:g1:", 1) for r in handoffs}
    for item in handoffs:
        item["generation"] = 1
        item["handoff_id"] = id_map[item["handoff_id"]]
        item["actor_bindings_id"] = "bindings:g1"
        item["source_binding_id"] = f"binding:g1:{item['source_stage']}"
        item["target_binding_id"] = None if item["target_stage"] is None else f"binding:g1:{item['target_stage']}"
        item["recipient_binding_id"] = "binding:g1:commander_window" if item["source_stage"] == "design_receipt" else None
        payload = item["payload"]
        replacements = {
            "orchestration_setup_ref": "setup:g1", "baseline_identity_record_ref": "B1",
            "design_handoff_id": id_map.get("handoff:design"),
            "implementation_result_ref": "implementation:R1", "reviewed_identity_record_ref": "R1",
            "post_skim_handoff_id": id_map.get("handoff:post:valid"),
            "final_review_handoff_id": id_map.get("handoff:final"),
        }
        for field, value in replacements.items():
            if field in payload:
                payload[field] = value
        if item["source_stage"] == "post_skim":
            item["run_id"] = "post-run:g1"
            item["supersedes_handoff_ref"] = None
    transitions = [copy.deepcopy(r) for r in records if r.get("record_type") == "transition"]
    for index, item in enumerate(transitions):
        item.update(
            generation=1,
            transition_id=f"transition:g1:{index + 1}",
            previous_transition_ref=None if index == 0 else f"transition:g1:{index}",
            actor_bindings_id="bindings:g1",
            source_binding_id=f"binding:g1:{item['source']}",
            target_binding_id=f"binding:g1:{item['target']}",
            identity_record_ref="B1" if index < 3 else "R1",
            handoff_id=id_map[item["handoff_id"]],
        )
    state = {
        "schema_version": 3, "record_type": "state_transition", "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID, "generation": 1, "state_transition_id": "state:2",
        "previous_state_transition_ref": "state:1", "from_state": "running", "to_state": "running",
        "reason": "approved revision", "spec": SPEC_PATH, "identity_record_ref": "B1",
    }
    by_source = {item["source_stage"]: item for item in handoffs}
    staged = [
        by_source["pre_skim"], transitions[0],
        by_source["design"], transitions[1],
        by_source["commander_window"], transitions[2],
        r1, implementation, by_source["implementation"], transitions[3],
        by_source["post_skim"], transitions[4],
        by_source["final_review"], transitions[5],
        by_source["design_receipt"],
    ]
    return [*records, recovery, b1, promotion, *bindings, setup, state, *staged]


def producer_for(record):
    if record["record_type"] == "approval":
        return ACTORS["commander_window"]
    if record["record_type"] == "handoff":
        return ACTORS[record["source_stage"]]
    if record["record_type"] == "implementation_result" or (
        record["record_type"] == "identity" and record.get("epoch") == "result"
    ):
        return ACTORS["implementation"]
    return ACTORS["commander_window"]


def checkpoint_prefix(records, target):
    if target == "test_gate":
        return records
    if target == "pre_skim":
        stop = next(index for index, record in enumerate(records) if record.get("record_type") == "handoff" and record.get("source_stage") == "pre_skim")
        return records[:stop]
    transition_count = VALIDATOR.STAGES.index(target)
    transition_id = f"transition:{transition_count}"
    stop = next(index for index, record in enumerate(records) if record.get("record_type") == "transition" and record.get("transition_id") == transition_id)
    return records[: stop + 1]


def envelopes_for(entries):
    envelopes = []
    previous = None
    for sequence, entry in enumerate(entries):
        if isinstance(entry, tuple):
            status, prototype, envelope_findings = entry
        else:
            status, prototype, envelope_findings = "accepted", entry, []
        record = copy.deepcopy(prototype)
        record["created_at_utc"] = timestamp(sequence)
        record_type = record["record_type"]
        record_id = record[VALIDATOR.ID_FIELD_BY_TYPE[record_type]]
        envelope = {
            "schema_version": 3,
            "envelope_type": "orchestration_evidence",
            "status": status,
            "sequence": sequence,
            "work_id": WORK_ID,
            "attempt_id": ATTEMPT_ID,
            "record_type": record_type,
            "record_id": record_id,
            "record_sha256": VALIDATOR.payload_sha256(record),
            "record": record,
            "producer_actor_id": producer_for(record),
            "recorder_actor_id": ACTORS["commander_window"],
            "created_at_utc": timestamp(sequence),
            "previous_envelope_sha256": previous,
            "findings": envelope_findings,
        }
        envelopes.append(envelope)
        previous = VALIDATOR.payload_sha256(envelope)
    return envelopes


def finding_codes(result):
    return {finding["code"] for finding in result["findings"]}


def rechain(envelopes):
    previous = None
    for sequence, envelope in enumerate(envelopes):
        envelope["sequence"] = sequence
        envelope["record_sha256"] = VALIDATOR.payload_sha256(envelope["record"])
        envelope["previous_envelope_sha256"] = previous
        previous = VALIDATOR.payload_sha256(envelope)
    return envelopes


class OrchestrationEvidenceValidatorV3Test(unittest.TestCase):
    def make_workspace(self, temporary):
        root = Path(temporary)
        target = root / SCOPE_PATHS[0]
        target.parent.mkdir(parents=True)
        target.write_bytes(b"result")
        return root

    def test_valid_v3_test_gate_returns_full_deterministic_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            envelopes = envelopes_for(valid_records())
            first = VALIDATOR.validate_envelopes(root, envelopes, WORK_ID, ATTEMPT_ID, "test_gate")
            second = VALIDATOR.validate_envelopes(root, envelopes, WORK_ID, ATTEMPT_ID, "test_gate")
        self.assertTrue(first["valid"])
        self.assertEqual(first["state"], "ready_for_test")
        self.assertEqual(first["selected_refs"]["result_identity_record_id"], "R")
        self.assertEqual(first["validation_receipt"]["snapshot_payload"]["scope_paths"], SCOPE_PATHS)
        self.assertEqual(first["validation_receipt"], second["validation_receipt"])
        self.assertEqual(first["validation_receipt_sha256"], second["validation_receipt_sha256"])
        self.assertEqual(first["validation_receipt_sha256"], VALIDATOR.payload_sha256(first["validation_receipt"]))

    def test_all_eight_checkpoint_targets_have_positive_and_missing_prefix_negative_cases(self):
        targets = (
            "pre_skim", "design", "commander_window", "implementation",
            "post_skim", "final_review", "design_receipt", "test_gate",
        )
        for target in targets:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                root = self.make_workspace(temporary)
                if target in {"pre_skim", "design", "commander_window", "implementation"}:
                    (root / SCOPE_PATHS[0]).write_bytes(b"baseline")
                records = checkpoint_prefix(valid_records(), target)
                positive = VALIDATOR.validate_envelopes(root, envelopes_for(records), WORK_ID, ATTEMPT_ID, target)
                self.assertTrue(positive["valid"])
                broken = copy.deepcopy(records)
                if target == "pre_skim":
                    broken = [r for r in broken if r.get("record_type") != "orchestration_setup"]
                elif target == "test_gate":
                    broken = [r for r in broken if not (r.get("record_type") == "handoff" and r.get("source_stage") == "design_receipt")]
                else:
                    edge_index = VALIDATOR.STAGES.index(target) - 1
                    edge = VALIDATOR.EDGES[edge_index]
                    broken = [r for r in broken if not (r.get("record_type") == "handoff" and (r.get("source_stage"), r.get("target_stage")) == edge)]
                negative = VALIDATOR.validate_envelopes(root, envelopes_for(broken), WORK_ID, ATTEMPT_ID, target)
                self.assertFalse(negative["valid"])

    def test_schema_v3_exact_generic_recovery_records_and_no_legacy_fields(self):
        self.assertNotIn("generation", VALIDATOR.APPROVAL_FIELDS)
        self.assertNotIn("one_shot", VALIDATOR.APPROVAL_FIELDS)
        self.assertEqual(VALIDATOR.ATTEMPT_FIELDS, {
            "schema_version", "record_type", "work_id", "attempt_id",
            "approval_ref", "created_at_utc",
        })
        self.assertNotIn("legacy_identity_refs", VALIDATOR.IDENTITY_FIELDS)
        self.assertEqual(VALIDATOR.TERMINAL_PAYLOAD_FIELDS, {
            "reviewed_identity_record_ref", "final_review_handoff_id",
            "disposition", "reason",
        })
        self.assertIn("recovery_kind", VALIDATOR.RECOVERY_INPUT_FIELDS)
        self.assertIn("target_baseline_identity_record_ref", VALIDATOR.BASELINE_PROMOTION_FIELDS)

    def test_malformed_future_is_nonblocking_but_envelope_integrity_is_global(self):
        records = checkpoint_prefix(valid_records(), "design")
        future = copy.deepcopy(next(r for r in valid_records() if r.get("record_type") == "handoff" and r.get("source_stage") == "post_skim"))
        future["legacy_extra"] = True
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            (root / SCOPE_PATHS[0]).write_bytes(b"baseline")
            envelopes = envelopes_for([*records, future])
            projected = VALIDATOR.validate_envelopes(root, envelopes, WORK_ID, ATTEMPT_ID, "design")
            self.assertTrue(projected["valid"])
            self.assertIn("future_record_excluded", finding_codes(projected))
            envelopes[-1]["record_sha256"] = "0" * 64
            corrupted = VALIDATOR.validate_envelopes(root, envelopes, WORK_ID, ATTEMPT_ID, "design")
            self.assertFalse(corrupted["valid"])
            self.assertIn("envelope_record_sha256", finding_codes(corrupted))

    def test_expected_work_and_approval_enums_and_sorted_scope_are_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            mismatch = VALIDATOR.validate_envelopes(root, envelopes_for(valid_records()), "other-work", ATTEMPT_ID, "test_gate")
            self.assertFalse(mismatch["valid"])
        for field, value, code in (
            ("implementation_intensity", "SUPER", "approval_intensity_invalid"),
            ("process_level", "P9", "approval_process_level_invalid"),
            ("scope_paths", ["z", "a"], "approval_scope_invalid"),
        ):
            approval = approval_record()
            approval["created_at_utc"] = timestamp(0)
            approval[field] = value
            codes = {item["code"] for item in VALIDATOR.validate_approval_submission(approval, WORK_ID)}
            self.assertIn(code, codes)
        low = approval_record()
        low["created_at_utc"] = timestamp(0)
        self.assertEqual(low["protected_surfaces"], [])
        self.assertFalse(VALIDATOR.validate_approval_submission(low, WORK_ID))
        protected = approval_record()
        protected.update(
            implementation_intensity="HIGH",
            process_level="P3",
            protected_surfaces=["persistent_schema", "process_stop"],
            created_at_utc=timestamp(0),
        )
        self.assertFalse(VALIDATOR.validate_approval_submission(protected, WORK_ID))

    def test_wrong_result_producer_and_missing_predecessor_are_causal_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            envelopes = envelopes_for(valid_records())
            result_envelope = next(e for e in envelopes if e["record"].get("identity_record_id") == "R")
            result_envelope["producer_actor_id"] = ACTORS["commander_window"]
            result_envelope["record"]["predecessor_identity_record_ref"] = "missing-B"
            result = VALIDATOR.validate_envelopes(root, rechain(envelopes), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertFalse(result["valid"])
            self.assertTrue({"causal_producer", "result_predecessor_missing"} <= finding_codes(result))

    def test_terminal_same_generation_result_reentry_is_rejected(self):
        records = valid_records()
        reentry = copy.deepcopy(next(r for r in records if r.get("record_type") == "implementation_result"))
        reentry["implementation_result_id"] = "implementation:reentry"
        records.append(reentry)
        with tempfile.TemporaryDirectory() as temporary:
            result = VALIDATOR.validate_envelopes(self.make_workspace(temporary), envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
        self.assertFalse(result["valid"])
        self.assertIn("terminal_reentry", finding_codes(result))

    def test_setup_transition_and_state_forward_or_branch_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            records = valid_records()
            setup_index = next(i for i, r in enumerate(records) if r.get("record_type") == "orchestration_setup")
            first_binding = next(i for i, r in enumerate(records) if r.get("record_type") == "actor_binding")
            setup = records.pop(setup_index)
            records.insert(first_binding, setup)
            result = VALIDATOR.validate_envelopes(root, envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertIn("setup_forward_ref", finding_codes(result))

            records = valid_records()
            transition_index = next(i for i, r in enumerate(records) if r.get("transition_id") == "transition:1")
            handoff_index = next(i for i, r in enumerate(records) if r.get("handoff_id") == "handoff:pre")
            transition = records.pop(transition_index)
            records.insert(handoff_index, transition)
            result = VALIDATOR.validate_envelopes(root, envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertIn("transition_forward_ref", finding_codes(result))

            records = valid_records()
            branch = copy.deepcopy(next(r for r in records if r.get("record_type") == "state_transition"))
            branch["state_transition_id"] = "state:branch"
            records.append(branch)
            result = VALIDATOR.validate_envelopes(root, envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertFalse(result["valid"])
            self.assertEqual(result["state"], "needs_review")
            self.assertIsNone(result["validation_receipt"])
            self.assertIn("state_transition_root", finding_codes(result))
            self.assertIn("state_transition_branch", finding_codes(result))

            records = valid_records()
            state = next(r for r in records if r.get("record_type") == "state_transition")
            state["previous_state_transition_ref"] = state["state_transition_id"]
            state["from_state"] = "running"
            result = VALIDATOR.validate_envelopes(root, envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertFalse(result["valid"])
            self.assertEqual(result["state"], "needs_review")
            self.assertIsNone(result["validation_receipt"])
            self.assertIn("state_transition_root", finding_codes(result))

    def test_test_gate_requires_nonempty_current_running_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            missing = [r for r in valid_records() if r.get("record_type") != "state_transition"]
            result = VALIDATOR.validate_envelopes(root, envelopes_for(missing), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertFalse(result["valid"])
            self.assertIn("state_transition_missing", finding_codes(result))
            stopped = valid_records()
            state = next(r for r in stopped if r.get("record_type") == "state_transition")
            state["to_state"] = "needs_review"
            result = VALIDATOR.validate_envelopes(root, envelopes_for(stopped), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertFalse(result["valid"])
            self.assertIn("test_gate_state", finding_codes(result))

    def test_generation_one_promotes_full_r_and_old_receipt_never_falls_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            (root / SCOPE_PATHS[0]).write_bytes(b"result-1")
            records = generation_one_records()
            result = VALIDATOR.validate_envelopes(root, envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertTrue(result["valid"])
            self.assertEqual(result["generation"], 1)
            self.assertEqual(result["validation_receipt"]["recovery_bundle_ref"], "bundle:g1")
            b1 = next(r for r in records if r.get("identity_record_id") == "B1")
            r0 = next(r for r in records if r.get("identity_record_id") == "R")
            self.assertEqual(b1["snapshot_payload"], r0["snapshot_payload"])

            incomplete = [r for r in records if not (r.get("record_type") == "orchestration_setup" and r.get("generation") == 1)]
            no_fallback = VALIDATOR.validate_envelopes(root, envelopes_for(incomplete), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertFalse(no_fallback["valid"])
            self.assertEqual(no_fallback["generation"], 1)

    def test_generation_one_source_r_mismatch_and_forward_order_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            (root / SCOPE_PATHS[0]).write_bytes(b"result-1")
            records = generation_one_records()
            promotion = next(r for r in records if r.get("record_type") == "baseline_promotion")
            promotion["source_result_identity_record_ref"] = "B"
            mismatch = VALIDATOR.validate_envelopes(root, envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertFalse(mismatch["valid"])
            self.assertTrue({"promotion_source_result", "promotion_source_mismatch"} & finding_codes(mismatch))

            records = generation_one_records()
            recovery_index = next(i for i, r in enumerate(records) if r.get("record_type") == "recovery_input")
            promotion_index = next(i for i, r in enumerate(records) if r.get("record_type") == "baseline_promotion")
            promotion = records.pop(promotion_index)
            records.insert(recovery_index, promotion)
            forward = VALIDATOR.validate_envelopes(root, envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertFalse(forward["valid"])
            self.assertIn("promotion_forward_ref", finding_codes(forward))

    def test_rejected_envelope_is_a_finding_but_never_enters_accepted_index(self):
        records = valid_records()
        rejected = copy.deepcopy(next(item for item in records if item["record_type"] == "actor_binding"))
        rejected["actor_id"] = "conflicting-actor"
        records.append(("rejected", rejected, [{"code": "record_id_conflict", "detail": "same ID, different payload"}]))
        with tempfile.TemporaryDirectory() as temporary:
            result = VALIDATOR.validate_envelopes(self.make_workspace(temporary), envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
        self.assertTrue(result["valid"])
        self.assertIn("rejected:record_id_conflict", finding_codes(result))
        self.assertEqual(result["evidence_sequence"], len(records) - 1)

    def test_legacy_raw_record_and_accepted_conflict_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            legacy = VALIDATOR.validate_envelopes(root, [approval_record()], WORK_ID, ATTEMPT_ID, "test_gate")
            records = valid_records()
            conflict = copy.deepcopy(next(item for item in records if item.get("record_type") == "actor_binding"))
            conflict["actor_id"] = "conflicting-actor"
            conflict_result = VALIDATOR.validate_envelopes(root, envelopes_for([*records, conflict]), WORK_ID, ATTEMPT_ID, "test_gate")
        self.assertFalse(legacy["valid"])
        self.assertIn("legacy_raw_record_rejected", finding_codes(legacy))
        self.assertFalse(conflict_result["valid"])
        self.assertIn("record_id_conflict", finding_codes(conflict_result))

    def test_low_p0_is_generic_and_legacy_future_mixed_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            self.assertTrue(VALIDATOR.validate_envelopes(root, envelopes_for(valid_records()), WORK_ID, ATTEMPT_ID, "test_gate")["valid"])
            for version in (1, 2, 4):
                envelopes = envelopes_for(valid_records())
                envelopes[3]["record"]["schema_version"] = version
                envelopes[3]["record_sha256"] = VALIDATOR.payload_sha256(envelopes[3]["record"])
                result = VALIDATOR.validate_envelopes(root, envelopes, WORK_ID, ATTEMPT_ID, "test_gate")
                self.assertFalse(result["valid"])

    def test_invalid_post_skim_does_not_advance_latest_valid_and_later_valid_recovers(self):
        records = valid_records()
        valid_index = next(
            index
            for index, item in enumerate(records)
            if item.get("record_type") == "handoff" and item.get("source_stage") == "post_skim"
        )
        invalid = copy.deepcopy(records[valid_index])
        invalid["handoff_id"] = "handoff:post:invalid"
        invalid["run_id"] = "post-run:invalid"
        invalid["unresolved"] = ["local blocker"]
        records.insert(valid_index, invalid)
        with tempfile.TemporaryDirectory() as temporary:
            result = VALIDATOR.validate_envelopes(self.make_workspace(temporary), envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
        self.assertTrue(result["valid"])
        self.assertEqual(result["selected_refs"]["post_skim_handoff_id"], "handoff:post:valid")
        self.assertIn("post_skim_candidate_rejected", finding_codes(result))
        self.assertTrue(all(not item["blocking"] for item in result["findings"] if item["code"] in {"post_skim_candidate_rejected", "unresolved_blocker"}))

    def test_causal_only_invalid_post_does_not_advance_latest_valid(self):
        records = valid_records()
        valid_post = next(record for record in records if record.get("source_stage") == "post_skim")
        causal_invalid = copy.deepcopy(valid_post)
        causal_invalid.update(
            handoff_id="handoff:post:causal-invalid",
            run_id="post-run:causal-invalid",
            supersedes_handoff_ref=None,
        )
        implementation_transition = next(i for i, record in enumerate(records) if record.get("transition_id") == "transition:4")
        records.insert(implementation_transition, causal_invalid)
        with tempfile.TemporaryDirectory() as temporary:
            result = VALIDATOR.validate_envelopes(self.make_workspace(temporary), envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
        self.assertTrue(result["valid"])
        self.assertEqual(result["selected_refs"]["post_skim_handoff_id"], valid_post["handoff_id"])
        causal_findings = [item for item in result["findings"] if item.get("record_ref") == causal_invalid["handoff_id"]]
        self.assertIn("handoff_previous_transition_missing", {item["code"] for item in causal_findings})
        self.assertTrue(all(not item["blocking"] for item in causal_findings))

    def test_stage_evidence_must_alternate_and_utc_must_not_regress(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            records = valid_records()
            design_index = next(i for i, r in enumerate(records) if r.get("handoff_id") == "handoff:design")
            first_transition_index = next(i for i, r in enumerate(records) if r.get("transition_id") == "transition:1")
            design = records.pop(design_index)
            records.insert(first_transition_index, design)
            result = VALIDATOR.validate_envelopes(root, envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertFalse(result["valid"])
            self.assertTrue({"handoff_previous_transition_missing", "handoff_causal_order"} & finding_codes(result))

            records = valid_records()
            terminal_index = next(i for i, r in enumerate(records) if r.get("source_stage") == "design_receipt")
            final_transition_index = next(i for i, r in enumerate(records) if r.get("transition_id") == "transition:6")
            terminal = records.pop(terminal_index)
            records.insert(final_transition_index, terminal)
            result = VALIDATOR.validate_envelopes(root, envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertFalse(result["valid"])
            self.assertIn("terminal_causal_order", finding_codes(result))

            envelopes = envelopes_for(valid_records())
            design_envelope = next(e for e in envelopes if e["record"].get("handoff_id") == "handoff:design")
            design_envelope["record"]["created_at_utc"] = timestamp(0)
            result = VALIDATOR.validate_envelopes(root, rechain(envelopes), WORK_ID, ATTEMPT_ID, "test_gate")
            self.assertFalse(result["valid"])
            self.assertIn("handoff_utc_regression", finding_codes(result))

    def test_submission_enforces_generation_singletons_and_post_closure(self):
        envelopes = envelopes_for(valid_records())
        cases = []
        for record_type, code in (
            ("orchestration_setup", "setup_singleton"),
            ("actor_binding", "binding_stage_singleton"),
            ("implementation_result", "implementation_result_singleton"),
        ):
            candidate = copy.deepcopy(next(e["record"] for e in envelopes if e["record"].get("record_type") == record_type))
            id_field = VALIDATOR.ID_FIELD_BY_TYPE[record_type]
            candidate[id_field] += ":duplicate"
            cases.append((candidate, code))
        nonpost = copy.deepcopy(next(e["record"] for e in envelopes if e["record"].get("source_stage") == "design"))
        nonpost["handoff_id"] += ":duplicate"
        cases.append((nonpost, "handoff_edge_singleton"))
        terminal = copy.deepcopy(next(e["record"] for e in envelopes if e["record"].get("source_stage") == "design_receipt"))
        terminal["handoff_id"] += ":duplicate"
        terminal["target_stage"] = "pre_skim"
        cases.append((terminal, "terminal_singleton"))
        post = copy.deepcopy(next(e["record"] for e in envelopes if e["record"].get("source_stage") == "post_skim"))
        post.update(handoff_id="handoff:post:late", run_id="post-run:late", supersedes_handoff_ref="handoff:post:valid")
        cases.append((post, "post_skim_closed"))
        for candidate, expected in cases:
            with self.subTest(expected=expected):
                codes = {item["code"] for item in VALIDATOR.validate_submission(envelopes, candidate, producer_for(candidate))}
                self.assertIn(expected, codes)

    def test_transition_admission_requires_exact_previous_and_state_ids_are_attempt_global(self):
        records = valid_records()
        design_index = next(i for i, record in enumerate(records) if record.get("handoff_id") == "handoff:design")
        prefix = envelopes_for(records[: design_index + 1])
        transition = copy.deepcopy(next(record for record in records if record.get("transition_id") == "transition:2"))
        transition["previous_transition_ref"] = None
        transition["created_at_utc"] = timestamp(len(prefix))
        codes = {item["code"] for item in VALIDATOR.validate_submission(prefix, transition, ACTORS["commander_window"])}
        self.assertIn("transition_previous_not_latest", codes)

        generation_records = generation_one_records()
        state = next(record for record in generation_records if record.get("state_transition_id") == "state:2")
        state["state_transition_id"] = "state:1"
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            (root / SCOPE_PATHS[0]).write_bytes(b"result-1")
            result = VALIDATOR.validate_envelopes(root, envelopes_for(generation_records), WORK_ID, ATTEMPT_ID, "test_gate")
        self.assertFalse(result["valid"])
        self.assertIn("state_transition_id_reused", finding_codes(result))

        existing = envelopes_for(generation_one_records())
        candidate = copy.deepcopy(next(e["record"] for e in existing if e["record"].get("state_transition_id") == "state:2"))
        candidate.update(generation=2, state_transition_id="state:3", previous_state_transition_ref="state:1", from_state="needs_review", identity_record_ref=None, created_at_utc=timestamp(len(existing)))
        codes = {item["code"] for item in VALIDATOR.validate_submission(existing, candidate, ACTORS["commander_window"])}
        self.assertTrue({"state_previous_not_latest", "state_from_mismatch"} <= codes)

    def test_post_run_reuse_equal_utc_and_wrong_supersedes_do_not_advance_latest(self):
        base = valid_records()
        post_index = next(i for i, r in enumerate(base) if r.get("source_stage") == "post_skim")
        for mode in ("reuse", "equal_utc", "wrong_supersedes"):
            records = copy.deepcopy(base)
            candidate = copy.deepcopy(records[post_index])
            candidate["handoff_id"] = f"handoff:post:{mode}"
            candidate["run_id"] = records[post_index]["run_id"] if mode == "reuse" else f"post-run:{mode}"
            candidate["supersedes_handoff_ref"] = "wrong" if mode == "wrong_supersedes" else records[post_index]["handoff_id"]
            records.insert(post_index + 1, candidate)
            with tempfile.TemporaryDirectory() as temporary:
                envelopes = envelopes_for(records)
                if mode == "equal_utc":
                    post_envelopes = [e for e in envelopes if e["record"].get("source_stage") == "post_skim"]
                    post_envelopes[1]["record"]["created_at_utc"] = post_envelopes[0]["record"]["created_at_utc"]
                    rechain(envelopes)
                result = VALIDATOR.validate_envelopes(self.make_workspace(temporary), envelopes, WORK_ID, ATTEMPT_ID, "test_gate")
            if mode == "reuse":
                self.assertFalse(result["valid"])
            else:
                self.assertTrue(result["valid"])
                self.assertEqual(result["selected_refs"]["post_skim_handoff_id"], "handoff:post:valid")

    def test_multiple_valid_post_candidates_are_allowed_until_post_transition(self):
        records = valid_records()
        post_index = next(i for i, record in enumerate(records) if record.get("source_stage") == "post_skim")
        latest = copy.deepcopy(records[post_index])
        latest.update(
            handoff_id="handoff:post:latest",
            run_id="post-run:latest",
            supersedes_handoff_ref="handoff:post:valid",
        )
        records.insert(post_index + 1, latest)
        transition = next(record for record in records if record.get("transition_id") == "transition:5")
        transition["handoff_id"] = latest["handoff_id"]
        final = next(record for record in records if record.get("source_stage") == "final_review")
        final["payload"]["post_skim_handoff_id"] = latest["handoff_id"]
        with tempfile.TemporaryDirectory() as temporary:
            result = VALIDATOR.validate_envelopes(self.make_workspace(temporary), envelopes_for(records), WORK_ID, ATTEMPT_ID, "test_gate")
        self.assertTrue(result["valid"])
        self.assertEqual(result["selected_refs"]["post_skim_handoff_id"], latest["handoff_id"])

    def test_post_transition_admission_replays_latest_valid_candidate(self):
        records = valid_records()
        transition_index = next(i for i, record in enumerate(records) if record.get("transition_id") == "transition:5")
        prefix = records[:transition_index]
        post_a = next(record for record in prefix if record.get("source_stage") == "post_skim")
        transition = copy.deepcopy(records[transition_index])

        invalid_b = copy.deepcopy(post_a)
        invalid_b.update(
            handoff_id="handoff:post:invalid-b",
            run_id="post-run:invalid-b",
            supersedes_handoff_ref=post_a["handoff_id"],
            unresolved=["local blocker"],
        )
        existing = envelopes_for([*prefix, invalid_b])
        transition["created_at_utc"] = timestamp(len(existing))
        accepted_codes = {item["code"] for item in VALIDATOR.validate_submission(existing, transition, ACTORS["commander_window"])}
        self.assertFalse({"post_transition_candidate_invalid", "post_transition_candidate_stale"} & accepted_codes)

        invalid_transition = copy.deepcopy(transition)
        invalid_transition["handoff_id"] = invalid_b["handoff_id"]
        invalid_codes = {item["code"] for item in VALIDATOR.validate_submission(existing, invalid_transition, ACTORS["commander_window"])}
        self.assertIn("post_transition_candidate_invalid", invalid_codes)

        valid_b = copy.deepcopy(invalid_b)
        valid_b["handoff_id"] = "handoff:post:valid-b"
        valid_b["run_id"] = "post-run:valid-b"
        valid_b["unresolved"] = []
        existing = envelopes_for([*prefix, valid_b])
        transition["created_at_utc"] = timestamp(len(existing))
        stale_codes = {item["code"] for item in VALIDATOR.validate_submission(existing, transition, ACTORS["commander_window"])}
        self.assertIn("post_transition_candidate_stale", stale_codes)

    def test_historical_singletons_block_but_current_future_singletons_are_prefix_isolated(self):
        for mode, expected in (
            ("setup", "setup_singleton"),
            ("binding", "binding_stage_singleton"),
            ("implementation", "implementation_result_singleton"),
            ("handoff", "handoff_edge_singleton"),
            ("terminal", "terminal_singleton"),
        ):
            with self.subTest(mode=mode):
                records = generation_one_records()
                generation_one_pre = next(i for i, record in enumerate(records) if record.get("generation") == 1 and record.get("source_stage") == "pre_skim")
                historical = records[:generation_one_pre]
                if mode == "setup":
                    duplicate = copy.deepcopy(next(record for record in historical if record.get("record_type") == "orchestration_setup" and record.get("generation") == 0))
                    duplicate["orchestration_setup_id"] = "setup:alternate:g0"
                elif mode == "binding":
                    duplicate = copy.deepcopy(next(record for record in historical if record.get("record_type") == "actor_binding" and record.get("generation") == 0 and record.get("stage") == "pre_skim"))
                    duplicate.update(actor_bindings_id="alternate:g0", binding_id="alternate:g0:pre_skim")
                elif mode == "implementation":
                    duplicate = copy.deepcopy(next(record for record in historical if record.get("record_type") == "implementation_result" and record.get("generation") == 0))
                    duplicate["implementation_result_id"] = "implementation:alternate:g0"
                elif mode == "handoff":
                    duplicate = copy.deepcopy(next(record for record in historical if record.get("source_stage") == "design" and record.get("generation") == 0))
                    duplicate["handoff_id"] = "handoff:design:alternate:g0"
                else:
                    duplicate = copy.deepcopy(next(record for record in historical if record.get("source_stage") == "design_receipt" and record.get("generation") == 0))
                    duplicate["handoff_id"] = "handoff:terminal:alternate:g0"
                    duplicate["target_stage"] = "pre_skim"
                historical.append(duplicate)
                with tempfile.TemporaryDirectory() as temporary:
                    root = self.make_workspace(temporary)
                    result = VALIDATOR.validate_envelopes(root, envelopes_for(historical), WORK_ID, ATTEMPT_ID, "pre_skim")
                self.assertFalse(result["valid"])
                self.assertIn(expected, finding_codes(result))

        records = checkpoint_prefix(valid_records(), "design")
        future = copy.deepcopy(next(record for record in valid_records() if record.get("record_type") == "implementation_result"))
        future_duplicate = copy.deepcopy(future)
        future_duplicate["implementation_result_id"] = "implementation:future-duplicate"
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            (root / SCOPE_PATHS[0]).write_bytes(b"baseline")
            result = VALIDATOR.validate_envelopes(root, envelopes_for([*records, future, future_duplicate]), WORK_ID, ATTEMPT_ID, "design")
        self.assertTrue(result["valid"])
        self.assertNotIn("implementation_result_singleton", finding_codes(result))

    def test_current_snapshot_mutation_closes_gate_and_removes_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            envelopes = envelopes_for(valid_records())
            (root / SCOPE_PATHS[0]).write_bytes(b"changed-after-R")
            result = VALIDATOR.validate_envelopes(root, envelopes, WORK_ID, ATTEMPT_ID, "test_gate")
        self.assertFalse(result["valid"])
        self.assertIn("current_snapshot_mismatch", finding_codes(result))
        self.assertIsNone(result["validation_receipt"])

    def test_partial_log_and_legacy_migration_are_not_consumed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            path = VALIDATOR.evidence_log_path(root, WORK_ID)
            path.parent.mkdir(parents=True)
            path.write_bytes(b'{}')
            with self.assertRaises(VALIDATOR.UnsafeInputError):
                VALIDATOR.validate_evidence_log(root, WORK_ID, ATTEMPT_ID, "test_gate")
            path.write_bytes(json.dumps(approval_record()).encode("utf-8") + b"\n")
            result = VALIDATOR.validate_evidence_log(root, WORK_ID, ATTEMPT_ID, "test_gate")
        self.assertFalse(result["valid"])
        self.assertIn("legacy_raw_record_rejected", finding_codes(result))

    def test_envelope_chain_corruption_is_blocking(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_workspace(temporary)
            envelopes = envelopes_for(valid_records())
            envelopes[3]["previous_envelope_sha256"] = "0" * 64
            result = VALIDATOR.validate_envelopes(root, envelopes, WORK_ID, ATTEMPT_ID, "test_gate")
        self.assertFalse(result["valid"])
        self.assertIn("envelope_hash_chain", finding_codes(result))


if __name__ == "__main__":
    unittest.main()
