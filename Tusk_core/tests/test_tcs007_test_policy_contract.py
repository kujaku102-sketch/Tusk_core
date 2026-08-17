import json
import unittest
from pathlib import Path


CORE = Path(__file__).resolve().parents[1]


class TestPolicyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = (CORE / "TEST_POLICY.md").read_text(encoding="utf-8")
        cls.mapping = json.loads((CORE / "TEST-MAP.json").read_text(encoding="utf-8"))

    def test_policy_has_one_human_contract_and_machine_authorities(self):
        self.assertTrue(self.policy.startswith("<!-- md-scope-document: COMMON -->"))
        self.assertIn("`TEST-MAP.json`", self.policy)
        self.assertIn("`tools/test_selector.py`", self.policy)
        for stage in ("`focused`", "`component`", "`full`"):
            self.assertIn(stage, self.policy)
        self.assertIn("`component`へ安全側補正", self.policy)
        self.assertIn("下位stageの成功は上位stageを代替しない", self.policy)

    def test_policy_change_maps_to_this_contract(self):
        matching = [
            rule for rule in self.mapping["focused_rules"]
            if "TEST_POLICY.md" in rule["patterns"]
        ]
        self.assertEqual(len(matching), 1)
        self.assertIn("tests/test_tcs007_test_policy_contract.py", matching[0]["tests"])


if __name__ == "__main__":
    unittest.main()
