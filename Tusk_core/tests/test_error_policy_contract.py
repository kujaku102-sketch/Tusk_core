from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ErrorPolicyContractTests(unittest.TestCase):
    def test_policy_owns_grammar_and_registry_owns_rows(self):
        policy = (ROOT / "ERROR_POLICY.md").read_text(encoding="utf-8")
        registry = (ROOT / "ERROR_CODES.md").read_text(encoding="utf-8")
        self.assertIn("[TUSK_FORCE_STOP]", policy)
        self.assertIn("F200-F299", policy)
        self.assertIn("F182", registry)
        self.assertIn("M180", registry)

    def test_legacy_spec_is_redirect_only(self):
        legacy = (ROOT / "ERROR_CODES_SPEC.md").read_text(encoding="utf-8")
        self.assertIn("ERROR_POLICY.md", legacy)
        self.assertIn("ERROR_CODES.md", legacy)
        self.assertNotIn("## 4. ログ文法形式", legacy)


if __name__ == "__main__":
    unittest.main()
