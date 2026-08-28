import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


CORE_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = CORE_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


COMMON = load_module(
    "orchestration_evidence_common",
    CORE_ROOT / "tools" / "orchestration_evidence_common.py",
)
LOGGER = load_module(
    "orchestration_evidence_log",
    CORE_ROOT / "tools" / "orchestration_evidence_log.py",
)
VALIDATOR_FIXTURES = load_module(
    "orchestration_evidence_validator_fixtures",
    CORE_ROOT / "tests" / "test_orchestration_evidence_validator.py",
)

WORK_ID = "core-orchestration-evidence-fixture"
ATTEMPT_ID = "orchestration-evidence:fixture:1"
APPROVAL_ID = "approval:orchestration-evidence-fixture"
SCOPE = ["Tusk_core/target.txt"]


def approval_record():
    return {
        "schema_version": 3,
        "record_type": "approval",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "approval_id": APPROVAL_ID,
        "implementation_intensity": "LOW",
        "process_level": "P0",
        "protected_surfaces": [],
        "scope_paths": SCOPE,
        "commander_actor_id": "commander:orchestration-fixture",
        "spec": "Tusk_core/specs/CORE_ORCHESTRATION_EVIDENCE_SPEC.md",
        "created_at_utc": "2026-08-21T00:00:00Z",
    }


def attempt_record():
    return {
        "schema_version": 3,
        "record_type": "attempt",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "approval_ref": APPROVAL_ID,
        "created_at_utc": "2026-08-21T00:00:02Z",
    }


def binding_record(binding_id="binding:pre"):
    return {
        "schema_version": 3,
        "record_type": "actor_binding",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "generation": 0,
        "actor_bindings_id": "bindings:g0",
        "binding_id": binding_id,
        "stage": "pre_skim",
        "actor_role": "skim",
        "actor_id": "skim:pre",
        "created_at_utc": "2026-08-21T00:00:03Z",
    }


def state_record(state_id="state:1", generation=0, previous=None, from_state=None):
    return {
        "schema_version": 3,
        "record_type": "state_transition",
        "work_id": WORK_ID,
        "attempt_id": ATTEMPT_ID,
        "generation": generation,
        "state_transition_id": state_id,
        "previous_state_transition_ref": previous,
        "from_state": from_state,
        "to_state": "running",
        "reason": "admission fixture",
        "spec": "Tusk_core/specs/CORE_ORCHESTRATION_EVIDENCE_SPEC.md",
        "identity_record_ref": None,
        "created_at_utc": "2026-08-21T00:00:04Z",
    }


class OrchestrationEvidenceLogTest(unittest.TestCase):
    def prepare(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "Tusk_core").mkdir()
        approval_path = Path("approval.json")
        (root / approval_path).write_text(json.dumps(approval_record()), encoding="utf-8")
        initialized = LOGGER.initialize_log(
            root,
            WORK_ID,
            approval_path,
            "commander:orchestration-fixture",
        )
        return root, initialized

    def append(self, root, record, sequence):
        record_path = Path(f"record-{sequence}.json")
        (root / record_path).write_text(json.dumps(record), encoding="utf-8")
        return LOGGER.append_record(
            root,
            WORK_ID,
            ATTEMPT_ID,
            record_path,
            "commander:orchestration-fixture",
            "commander:orchestration-fixture",
            sequence,
        )

    def append_fixture(self, root, envelopes, record, sequence):
        path = COMMON.evidence_log_path(root, WORK_ID)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(b"".join(COMMON.canonical_json_bytes(envelope) + b"\n" for envelope in envelopes))
        record_path = root / f"fixture-record-{sequence}.json"
        record_path.write_text(json.dumps(record), encoding="utf-8")
        commander = VALIDATOR_FIXTURES.ACTORS["commander_window"]
        producer = VALIDATOR_FIXTURES.ACTORS[record["source_stage"]] if record.get("record_type") == "handoff" else commander
        return LOGGER.append_record(root, WORK_ID, ATTEMPT_ID, record_path.relative_to(root), producer, commander, sequence)

    def test_init_uses_hashed_path_and_accepted_genesis_sequence_zero(self):
        root, result = self.prepare()
        digest = hashlib.sha256(WORK_ID.encode("utf-8")).hexdigest()
        self.assertEqual(
            result["log_path"],
            f"work/orchestration_evidence/{digest}/events.jsonl",
        )
        raw = (root / result["log_path"]).read_bytes()
        envelopes = LOGGER.parse_envelope_stream(raw)
        self.assertEqual(envelopes[0]["sequence"], 0)
        self.assertEqual(envelopes[0]["status"], "accepted")
        self.assertEqual(envelopes[0]["record_type"], "approval")

    def test_append_is_single_sequence_and_exact_replay_collapses(self):
        root, initialized = self.prepare()
        first = self.append(root, attempt_record(), 1)
        self.assertEqual((first["status"], first["sequence"]), ("accepted", 1))
        replay = self.append(root, attempt_record(), 2)
        self.assertEqual((replay["status"], replay["sequence"]), ("collapsed_replay", 1))
        envelopes = LOGGER.parse_envelope_stream(
            (root / initialized["log_path"]).read_bytes()
        )
        self.assertEqual([item["sequence"] for item in envelopes], [0, 1])

    def test_incremental_admission_is_generic_for_low_p0_and_high_p3(self):
        root, _ = self.prepare()
        self.assertEqual(self.append(root, attempt_record(), 1)["status"], "accepted")
        with tempfile.TemporaryDirectory() as temporary:
            other = Path(temporary)
            (other / "Tusk_core").mkdir()
            approval = approval_record()
            approval["implementation_intensity"] = "HIGH"
            approval["process_level"] = "P3"
            approval["protected_surfaces"] = ["persistent_schema", "process_stop"]
            (other / "approval.json").write_text(json.dumps(approval), encoding="utf-8")
            initialized = LOGGER.initialize_log(other, WORK_ID, Path("approval.json"), approval["commander_actor_id"])
            self.assertEqual(initialized["status"], "accepted")

    def test_legacy_v1_v2_future_and_mixed_records_are_rejected_without_migration(self):
        for version in (1, 2, 4):
            with self.subTest(version=version):
                root, _ = self.prepare()
                record = attempt_record()
                record["schema_version"] = version
                rejected = self.append(root, record, 1)
                self.assertEqual(rejected["status"], "rejected")
                expected = "legacy_schema_rejected" if version in (1, 2) else "unsupported_schema_version"
                self.assertIn(expected, {finding["code"] for finding in rejected["findings"]})

    def test_forward_reference_and_missing_binding_producer_are_rejected_envelopes(self):
        root, _ = self.prepare()
        self.append(root, attempt_record(), 1)
        forward = {
            "schema_version": 3, "record_type": "implementation_result",
            "work_id": WORK_ID, "attempt_id": ATTEMPT_ID, "generation": 0,
            "implementation_result_id": "implementation:forward",
            "baseline_identity_record_ref": "B-missing",
            "result_identity_record_ref": "R-missing",
            "created_at_utc": "2026-08-21T00:00:03Z",
        }
        rejected = self.append(root, forward, 2)
        self.assertEqual(rejected["status"], "rejected")
        self.assertTrue({"causal_binding_missing", "implementation_identity_forward_ref"} <= {item["code"] for item in rejected["findings"]})

    def test_invalid_post_run_id_is_reserved_and_cannot_be_reused(self):
        root, _ = self.prepare()
        self.append(root, attempt_record(), 1)
        post = {
            "schema_version": 3, "record_type": "handoff", "work_id": WORK_ID,
            "attempt_id": ATTEMPT_ID, "generation": 0, "handoff_id": "post:invalid:1",
            "source_stage": "post_skim", "target_stage": "final_review",
            "actor_bindings_id": "bindings:g0", "source_binding_id": "binding:post",
            "target_binding_id": "binding:review", "recipient_actor_role": None,
            "recipient_binding_id": None, "spec": "Tusk_core/specs/CORE_ORCHESTRATION_EVIDENCE_SPEC.md",
            "affected_paths": SCOPE, "decision": "proceed", "payload": {},
            "evidence_refs": ["evidence"], "unresolved": [], "run_id": "reserved-run",
            "supersedes_handoff_ref": None, "created_at_utc": "2026-08-21T00:00:04Z",
        }
        first = self.append(root, post, 2)
        self.assertEqual(first["status"], "rejected")
        post["handoff_id"] = "post:invalid:2"
        post["created_at_utc"] = "2026-08-21T00:00:05Z"
        second = self.append(root, post, 3)
        self.assertEqual(second["status"], "rejected")
        self.assertIn("post_skim_run_id_reused", {item["code"] for item in second["findings"]})

    def test_writer_applies_binding_singleton_and_attempt_global_state_admission(self):
        root, _ = self.prepare()
        self.assertEqual(self.append(root, attempt_record(), 1)["status"], "accepted")
        self.assertEqual(self.append(root, binding_record(), 2)["status"], "accepted")
        duplicate_binding = binding_record("binding:pre:duplicate")
        duplicate_binding["created_at_utc"] = "2026-08-21T00:00:04Z"
        rejected = self.append(root, duplicate_binding, 3)
        self.assertEqual(rejected["status"], "rejected")
        self.assertIn("binding_stage_singleton", {item["code"] for item in rejected["findings"]})

        root_state = state_record()
        root_state["created_at_utc"] = "2026-08-21T00:00:05Z"
        self.assertEqual(self.append(root, root_state, 4)["status"], "accepted")
        reused = state_record("state:1", generation=1, previous="state:1", from_state="running")
        reused["created_at_utc"] = "2026-08-21T00:00:06Z"
        rejected = self.append(root, reused, 5)
        self.assertEqual(rejected["status"], "rejected")
        self.assertIn("state_transition_id_reused", {item["code"] for item in rejected["findings"]})
        stale = state_record("state:2", generation=1, previous=None, from_state="needs_review")
        stale["created_at_utc"] = "2026-08-21T00:00:07Z"
        rejected = self.append(root, stale, 6)
        self.assertEqual(rejected["status"], "rejected")
        self.assertTrue({"state_previous_not_latest", "state_from_mismatch"} <= {item["code"] for item in rejected["findings"]})

    def test_writer_replays_post_candidates_for_transition_and_closes_post(self):
        fixture = VALIDATOR_FIXTURES
        records = fixture.valid_records()
        transition_index = next(i for i, record in enumerate(records) if record.get("transition_id") == "transition:5")
        prefix = records[:transition_index]
        post_a = next(record for record in prefix if record.get("source_stage") == "post_skim")
        transition = copy.deepcopy(records[transition_index])

        for mode in ("invalid_b_to_a", "valid_b_to_a", "invalid_b_transition"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "Tusk_core").mkdir()
                candidate_b = copy.deepcopy(post_a)
                candidate_b.update(
                    handoff_id=f"handoff:post:{mode}",
                    run_id=f"post-run:{mode}",
                    supersedes_handoff_ref=post_a["handoff_id"],
                    unresolved=["local blocker"] if mode != "valid_b_to_a" else [],
                )
                envelopes = fixture.envelopes_for([*prefix, candidate_b])
                submitted = copy.deepcopy(transition)
                submitted["created_at_utc"] = fixture.timestamp(len(envelopes))
                if mode == "invalid_b_transition":
                    submitted["handoff_id"] = candidate_b["handoff_id"]
                result = self.append_fixture(root, envelopes, submitted, len(envelopes))
                if mode == "invalid_b_to_a":
                    self.assertEqual(result["status"], "accepted")
                    late_post = copy.deepcopy(post_a)
                    late_post.update(
                        handoff_id="handoff:post:after-close",
                        run_id="post-run:after-close",
                        supersedes_handoff_ref=post_a["handoff_id"],
                        created_at_utc=fixture.timestamp(len(envelopes) + 1),
                    )
                    closed = self.append_fixture(root, envelopes, late_post, len(envelopes) + 1)
                    self.assertEqual(closed["status"], "rejected")
                    self.assertIn("post_skim_closed", {item["code"] for item in closed["findings"]})
                else:
                    self.assertEqual(result["status"], "rejected")
                    expected = "post_transition_candidate_stale" if mode == "valid_b_to_a" else "post_transition_candidate_invalid"
                    self.assertIn(expected, {item["code"] for item in result["findings"]})

    def test_writer_ignores_causal_only_invalid_post_and_hardens_terminal_singleton(self):
        fixture = VALIDATOR_FIXTURES
        records = fixture.valid_records()
        post_a = next(record for record in records if record.get("source_stage") == "post_skim")
        causal_invalid = copy.deepcopy(post_a)
        causal_invalid.update(
            handoff_id="handoff:post:causal-invalid",
            run_id="post-run:causal-invalid",
            supersedes_handoff_ref=None,
        )
        implementation_transition = next(i for i, record in enumerate(records) if record.get("transition_id") == "transition:4")
        records.insert(implementation_transition, causal_invalid)
        post_transition_index = next(i for i, record in enumerate(records) if record.get("transition_id") == "transition:5")
        prefix = records[:post_transition_index]
        transition = copy.deepcopy(records[post_transition_index])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Tusk_core").mkdir()
            envelopes = fixture.envelopes_for(prefix)
            transition["created_at_utc"] = fixture.timestamp(len(envelopes))
            accepted = self.append_fixture(root, envelopes, transition, len(envelopes))
            self.assertEqual(accepted["status"], "accepted")

        terminal_records = fixture.valid_records()
        terminal = copy.deepcopy(next(record for record in terminal_records if record.get("source_stage") == "design_receipt"))
        terminal.update(
            handoff_id="handoff:terminal:different-target",
            target_stage="pre_skim",
            created_at_utc=fixture.timestamp(len(terminal_records)),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Tusk_core").mkdir()
            envelopes = fixture.envelopes_for(terminal_records)
            rejected = self.append_fixture(root, envelopes, terminal, len(envelopes))
            self.assertEqual(rejected["status"], "rejected")
            self.assertIn("terminal_singleton", {item["code"] for item in rejected["findings"]})

    def test_conflict_and_scope_mismatch_are_rejected_envelopes(self):
        root, initialized = self.prepare()
        self.append(root, attempt_record(), 1)
        conflict = attempt_record()
        conflict["approval_ref"] = "approval:conflict"
        rejected = self.append(root, conflict, 2)
        self.assertEqual(rejected["status"], "rejected")
        self.assertIn("record_id_conflict", {item["code"] for item in rejected["findings"]})
        identity = {
            "schema_version": 3,
            "record_type": "identity",
            "work_id": WORK_ID,
            "attempt_id": ATTEMPT_ID,
            "generation": 0,
            "identity_record_id": "identity:outside",
            "epoch": "baseline",
            "snapshot_payload": {
                "algorithm": "sha256-path-snapshot-v1",
                "path_snapshot": [{"path": "outside.txt", "state": "absent"}],
                "scope_paths": ["outside.txt"],
            },
            "snapshot_sha256": "a" * 64,
            "producer": "orchestration_setup",
            "predecessor_identity_record_ref": None,
            "created_at_utc": "2026-08-21T00:00:03Z",
        }
        scope_rejected = self.append(root, identity, 3)
        self.assertEqual(scope_rejected["status"], "rejected")
        envelopes = LOGGER.parse_envelope_stream(
            (root / initialized["log_path"]).read_bytes()
        )
        self.assertEqual([item["status"] for item in envelopes], ["accepted", "accepted", "rejected", "rejected"])

    def test_partial_existing_log_and_legacy_raw_migration_fail_closed(self):
        root, initialized = self.prepare()
        log = root / initialized["log_path"]
        with log.open("ab") as stream:
            stream.write(b"partial")
        record_path = Path("attempt.json")
        (root / record_path).write_text(json.dumps(attempt_record()), encoding="utf-8")
        with self.assertRaises(LOGGER.EvidenceLogError):
            LOGGER.append_record(
                root,
                WORK_ID,
                ATTEMPT_ID,
                record_path,
                "commander:orchestration-fixture",
                "commander:orchestration-fixture",
                1,
            )

        with tempfile.TemporaryDirectory() as other:
            other_root = Path(other)
            (other_root / "Tusk_core").mkdir()
            work = COMMON.hashed_work_path(other_root, WORK_ID)
            work.mkdir(parents=True)
            (work / "events.jsonl").write_text(
                json.dumps(attempt_record()) + "\n",
                encoding="utf-8",
            )
            approval_path = Path("approval.json")
            (other_root / approval_path).write_text(json.dumps(approval_record()), encoding="utf-8")
            with self.assertRaises(LOGGER.EvidenceLogError):
                LOGGER.initialize_log(
                    other_root,
                    WORK_ID,
                    approval_path,
                    "commander:orchestration-fixture",
                )

    def test_commander_identity_and_expected_sequence_are_not_inferred(self):
        root, _ = self.prepare()
        record_path = Path("attempt.json")
        (root / record_path).write_text(json.dumps(attempt_record()), encoding="utf-8")
        with self.assertRaises(LOGGER.EvidenceLogError):
            LOGGER.append_record(
                root,
                WORK_ID,
                ATTEMPT_ID,
                record_path,
                "commander:orchestration-fixture",
                "different-recorder",
                1,
            )
        with self.assertRaises(LOGGER.EvidenceLogError):
            LOGGER.append_record(
                root,
                WORK_ID,
                ATTEMPT_ID,
                record_path,
                "commander:orchestration-fixture",
                "commander:orchestration-fixture",
                2,
            )

    def test_common_path_safety_rechecks_toctou_and_rejects_reparse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target_path = Path("target.txt")
            target = root / target_path
            target.write_text("a", encoding="utf-8")
            token = COMMON.capture_path_safety(root, target_path, require_file=True)
            target.write_text("changed", encoding="utf-8")
            with self.assertRaises(COMMON.EvidenceSafetyError):
                COMMON.recheck_path_safety(token)
            with patch.object(COMMON, "_is_reparse", return_value=True):
                with self.assertRaises(COMMON.EvidenceSafetyError):
                    COMMON.capture_path_safety(root, target_path)


if __name__ == "__main__":
    unittest.main()
