from pathlib import Path
import re
import unittest


DOC = Path(__file__).resolve().parents[1] / "ROUTING_POLICY.md"
SPEC = Path(__file__).resolve().parents[1] / "specs" / "ROUTING_POLICY_CONSOLIDATION.md"


class RoutingPolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOC.read_text(encoding="utf-8")

    def test_canonical_scope_and_sections(self):

        for heading in (
            "## Implementation Intensity",
            "## Skim classification",
            "## Provider routing and snapshot policy",
            "## MAX gate",
            "## Authority boundary",
            "## Failure analysis routing",
        ):
            self.assertIn(heading, self.text)

    def test_intensity_and_provider_contract(self):
        self.assertEqual(
            re.findall(r"^\| `(LOW|MID|HIGH|MAX)` \|", self.text, re.MULTILINE)[:4],
            ["LOW", "MID", "HIGH", "MAX"],
        )
        for field in (
            "provider_route:", "cache_input_ceiling_kib:", "snapshot_policy:",
            "max_activation_count:", "max_approved:", "max_approval_id:",
        ):
            self.assertIn(field, self.text)

    def test_skim_output_is_complete(self):
        for field in (
            "implementation_intensity:", "intensity_reason:", "process_level:",
            "process_level_reason:", "confidence:", "affected_paths:",
            "risk_triggers:", "risk_evidence:", "required_tests:",
            "needs_review:", "review_reason:",
        ):
            self.assertIn(field, self.text)

    def test_process_policy_is_referenced_without_level_definitions(self):
        self.assertIn("`PROCESS_POLICY.md`", self.text)
        for level in range(5):
            self.assertNotRegex(self.text, rf"`P{level}`\s*:")

    def test_max_gate_and_authority_guards(self):
        for value in (
            "recurrent_error_or_stop", "terra_mid_impractical",
            "must never be activated automatically", "explicit human approval",
            "max_requires_explicit_human_approval", "needs_human_review",
            "AUTHORITY_SEPARATION.md", "PROCESS_POLICY.md",
        ):
            self.assertIn(value, self.text)
        self.assertNotIn("Only one automatic `MAX` activation", self.text)
        authority = (DOC.parent / "AUTHORITY_SEPARATION.md").read_text(encoding="utf-8")
        for value in (
            "Process Levelの低下提案は人間の明示承認なしに適用しない",
            "Protected Surface", "個別Spec下限",
        ):
            self.assertIn(value, authority)

    def test_spec_records_completion(self):
        value = SPEC.read_text(encoding="utf-8")
        self.assertIn("状態: `COMPLETED`", value)
        self.assertIn("python -m unittest tests/test_routing_policy.py", value)


if __name__ == "__main__":
    unittest.main()
