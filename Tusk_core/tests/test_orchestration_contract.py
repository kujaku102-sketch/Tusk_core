import ast
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = CORE_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))
STAGES = [
    "pre_skim",
    "design",
    "commander_window",
    "implementation",
    "post_skim",
    "final_review",
    "design_receipt",
]
ORCHESTRATION_SPEC_PATTERNS = {
    "specs/CORE_ORCHESTRATION_EVIDENCE_SPEC.md",
    "tools/orchestration_evidence_validator.py",
    "tests/test_orchestration_evidence_validator.py",
    "tools/orchestration_evidence_common.py",
    "tools/orchestration_evidence_log.py",
    "tests/test_orchestration_evidence_log.py",
}
ORCHESTRATION_SPEC_TESTS = {
    "tests/test_routing_policy.py",
    "tests/test_orchestration_contract.py",
    "tests/test_process_classifier.py",
    "tests/test_simplified_operations_contract.py",
    "tests/test_entry_documents_contract.py",
    "tests/test_test_selector.py",
    "tests/test_test_policy_contract.py",
    "tests/test_orchestration_evidence_log.py",
    "tests/test_orchestration_evidence_validator.py",
    "tests/test_common_test_guard_monitor.py",
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module(
    "orchestration_evidence_validator",
    CORE_ROOT / "tools" / "orchestration_evidence_validator.py",
)
LOGGER = load_module(
    "orchestration_evidence_log",
    CORE_ROOT / "tools" / "orchestration_evidence_log.py",
)


def read_text(path):
    return (CORE_ROOT / path).read_text(encoding="utf-8")


def headings(text):
    return [
        (len(match.group(1)), match.group(2).strip())
        for match in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", text, re.MULTILINE)
    ]


def section(text, title, level=2):
    marks = "#" * level
    match = re.search(
        rf"^{marks}\s+{re.escape(title)}\s*$\n(.*?)(?=^#{{1,{level}}}\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"missing Markdown section: {title}")
    return match.group(1)


def yaml_blocks(text):
    return re.findall(r"```yaml\s*\n(.*?)\n```", text, re.DOTALL)


def yaml_top_keys(block):
    return {
        match.group(1)
        for line in block.splitlines()
        if (match := re.match(r"^([a-z][a-z0-9_]*):", line))
    }


def yaml_record_fields(text, record_type):
    for block in yaml_blocks(text):
        if re.search(rf"^record_type:\s*{re.escape(record_type)}\s*$", block, re.MULTILINE):
            return yaml_top_keys(block)
    raise AssertionError(f"missing YAML record schema: {record_type}")


def parse_stage_table(text):
    body = section(text, "Seven-stage orchestration roles and order")
    rows = []
    for line in body.splitlines():
        if not line.startswith("|") or "---" in line or line.startswith("| Stage"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 4:
            rows.append(cells)
    return rows


def import_from_modules(path):
    tree = ast.parse(read_text(path), filename=path)
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


class OrchestrationGovernanceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.authority = read_text("AUTHORITY_SEPARATION.md")
        cls.routing = read_text("ROUTING_POLICY.md")
        cls.process = read_text("PROCESS_POLICY.md")
        cls.test_policy = read_text("TEST_POLICY.md")
        cls.mapping = json.loads(read_text("TEST-MAP.json"))
        cls.orchestration_spec = read_text("specs/CORE_ORCHESTRATION_EVIDENCE_SPEC.md")

    def test_authority_owns_only_seven_stage_role_binding_and_handoff_shape(self):
        rows = parse_stage_table(self.authority)
        self.assertEqual([row[0].strip("`") for row in rows], STAGES)
        route = section(self.authority, "通常経路")
        sequence = re.search(r"```text\s*\n(.+?)\n```", route, re.DOTALL).group(1)
        self.assertEqual([value.strip() for value in sequence.split("→")], STAGES)
        for semantic_field in (
            "history_rework_count",
            "remediation_depth",
            "attempt_index",
            "max_attempts",
            "revision_count",
            "retry_count",
        ):
            self.assertNotIn(semantic_field, self.authority)
        self.assertIn("PROCESS_POLICY.md", route)
        self.assertIn("PROCESS_POLICY.md", section(self.authority, "Handoff contract"))

    def test_documented_record_schemas_match_validator_v3(self):
        expected = {
            "approval": (self.process, VALIDATOR.APPROVAL_FIELDS),
            "attempt": (self.process, VALIDATOR.ATTEMPT_FIELDS),
            "actor_binding": (self.authority, VALIDATOR.ACTOR_BINDING_FIELDS),
            "identity": (self.process, VALIDATOR.IDENTITY_FIELDS),
            "implementation_result": (
                self.process,
                VALIDATOR.IMPLEMENTATION_RESULT_FIELDS,
            ),
            "handoff": (self.authority, VALIDATOR.HANDOFF_FIELDS),
            "transition": (self.process, VALIDATOR.TRANSITION_FIELDS),
            "state_transition": (self.process, VALIDATOR.STATE_TRANSITION_FIELDS),
        }
        for record_type, (document, fields) in expected.items():
            with self.subTest(record_type=record_type):
                self.assertEqual(yaml_record_fields(document, record_type), fields)
        self.assertEqual(VALIDATOR.SCHEMA_VERSION, 3)
        self.assertEqual(LOGGER.SCHEMA_VERSION, 3)
        self.assertEqual(VALIDATOR.ENVELOPE_FIELDS, LOGGER.ENVELOPE_FIELDS)
        self.assertEqual(VALIDATOR.ATTEMPT_FIELDS, {
            "schema_version", "record_type", "work_id", "attempt_id",
            "approval_ref", "created_at_utc",
        })
        self.assertIn("recovery_kind", VALIDATOR.RECOVERY_INPUT_FIELDS)
        self.assertIn("baseline_promotion_id", VALIDATOR.BASELINE_PROMOTION_FIELDS)
        self.assertNotIn("implementation_handoff_id", VALIDATOR.IMPLEMENTATION_RESULT_FIELDS)

    def test_process_is_sole_owner_of_generic_setup_recovery_and_admission(self):
        ledger = section(
            self.process,
            "Stage-external setup, generation, and recovery",
            level=3,
        )
        for token in (
            "generation",
            "recovery input",
            "baseline promotion",
            "full canonical snapshot payload",
            "sequence 0",
        ):
            self.assertIn(token, ledger)
        for forbidden in ("history_rework_count: 3", "max_attempts: 1", "revision_count: 0", "retry_count: 0"):
            self.assertNotIn(forbidden, ledger)
        admission = section(self.process, "Trusted evidence admission and freshness", level=4)
        for token in (
            "accepted/rejected",
            "events.jsonl",
            "canonical JSON",
            "flush",
            "fsync",
            "partial",
            "migration",
            "latest-valid",
            "validation receipt",
            "reparse",
            "TOCTOU",
        ):
            self.assertIn(token, admission)

    def test_routing_defines_per_run_post_skim_duty_and_defers_admission(self):
        post = section(self.routing, "Post-skim", level=3)
        for token in (
            "per-run duty",
            "handoff_id",
            "run_id",
            "現在UTC",
            "supersedes_handoff_ref",
            "commander-controlled machine recorder",
        ):
            self.assertIn(token, post)
        self.assertIn("PROCESS_POLICY.md`だけを正本", post)
        self.assertIn("admission", post)

    def test_test_policy_fixes_receipt_validator_guard_selector_product_order(self):
        order = section(self.test_policy, "Receipt to product execution order", level=3)
        self.assertIn("receipt → validator → guard → selector --run / product", order)
        self.assertLess(order.index("receipt →"), order.index("validator →"))
        self.assertIn("process registry読込", order)
        self.assertIn("lock取得", order)
        guard = section(self.test_policy, "Guard and evidence")
        self.assertIn("`orchestration_gate`は必須boolean", guard)
        for token in ("target: test_gate", "full `validation_receipt`", "partial", "hash-only", "R-ID-only"):
            self.assertIn(token, guard)
        self.assertIn("explicit `false`", guard)
        self.assertIn("guardがvalidatorを", guard)
        self.assertIn("attempt・target指定で再実行", guard)

    def test_guard_code_executes_gate_before_registry_and_lock(self):
        monitor = read_text("tools/test_guard_monitor.py")
        main = monitor[monitor.index("def main(") :]
        self.assertLess(main.index("validate_orchestration_gate("), main.index("parse_error_registry("))
        self.assertLess(main.index("validate_orchestration_gate("), main.index("validate_registry("))
        self.assertLess(main.index("validate_orchestration_gate("), main.index("acquire_guard_lock("))
        self.assertIn("orchestration_gate", main)

    def test_shared_safety_primitive_import_graph_is_explicit(self):
        validator_imports = import_from_modules("tools/orchestration_evidence_validator.py")
        recorder_imports = import_from_modules("tools/orchestration_evidence_log.py")
        guard_imports = import_from_modules("tools/test_guard_monitor.py")
        self.assertTrue(
            {"orchestration_evidence_common", "tools.orchestration_evidence_common"}
            & validator_imports
        )
        self.assertTrue(
            {"orchestration_evidence_common", "tools.orchestration_evidence_common"}
            & recorder_imports
        )
        self.assertIn("tools.orchestration_evidence_validator", guard_imports)
        self.assertTrue(
            {"orchestration_evidence_common", "tools.orchestration_evidence_common"}
            & guard_imports
        )

    def test_test_map_patterns_are_globally_unique_and_preserve_orchestration_union(self):
        rules = self.mapping["focused_rules"]
        patterns = [pattern for rule in rules for pattern in rule["patterns"]]
        self.assertEqual(len(patterns), len(set(patterns)))
        orchestration = next(
            rule
            for rule in rules
            if "specs/CORE_ORCHESTRATION_EVIDENCE_SPEC.md" in rule["patterns"]
        )
        self.assertEqual(set(orchestration["patterns"]), ORCHESTRATION_SPEC_PATTERNS)
        self.assertEqual(set(orchestration["tests"]), ORCHESTRATION_SPEC_TESTS)

    def test_numberless_orchestration_spec_records_adopted_contract_and_exclusions(self):
        self.assertEqual(
            headings(self.orchestration_spec)[0],
            (1, "Core Orchestration Evidence Specification"),
        )
        provenance = section(self.orchestration_spec, "Provenance")
        for source in (
            "TCS-014_SEVEN_STAGE_ORCHESTRATION.md",
            "TCS-015_ROOT_REMEDIATION_ORCHESTRATION.md",
            "TCS-016_GOVERNANCE_BOOTSTRAP_RECOVERY.md",
        ):
            self.assertIn(source, provenance)
        adopted = section(self.orchestration_spec, "Adopted evidence semantics")
        for token in ("accepted", "latest-valid", "stale", "replay", "conflict", "component root"):
            self.assertIn(token, adopted)
        exclusions = section(self.orchestration_spec, "Explicit exclusions")
        for token in ("固定work ID", "固定approval ID", "root-remediation", "one-shot", "MAX/P3", "revision", "retry"):
            self.assertIn(token, exclusions)

    def test_markdown_fences_are_balanced_and_validator_output_shape_is_declared(self):
        for name, document in (
            ("authority", self.authority),
            ("routing", self.routing),
            ("process", self.process),
            ("test_policy", self.test_policy),
            ("orchestration_spec", self.orchestration_spec),
        ):
            with self.subTest(name=name):
                self.assertEqual(document.count("```" ) % 2, 0)
        validator_section = section(
            self.test_policy,
            "Read-only orchestration evidence validator",
            level=3,
        )
        for field in (
            "schema_version",
            "validator",
            "work",
            "attempt",
            "generation",
            "evidence_sequence",
            "current_snapshot_sha256",
            "validation_receipt",
            "validation_receipt_sha256",
        ):
            self.assertIn(f"`{field}`", validator_section)
        self.assertNotIn("validator v2", self.test_policy)
        self.assertNotIn("implementation_handoff_id", self.process)
        for token in (
            "attempt-global",
            "handoff_i < transition_i < handoff_(i+1)",
            "post-skim以外の各handoff edge",
            "候補local findings",
        ):
            self.assertIn(token, self.process)
        self.assertIn("post候補は対応transitionまで複数可", self.orchestration_spec)


if __name__ == "__main__":
    unittest.main()
