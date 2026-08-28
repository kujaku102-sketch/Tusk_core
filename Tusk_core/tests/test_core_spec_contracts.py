from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CoreSpecContracts(unittest.TestCase):
    def test_specs(self):
        for name in (
            "CORE_ROUTING_BASELINE.md",
            "RISK_EVIDENCE.md",
            "PROPOSAL_AUTHORITY_AND_SAFETY_APPEAL.md",
        ):
            self.assertTrue((ROOT / "specs" / name).is_file())
        retired = ROOT / "archive" / "retired" / "TCS-002_EXTENSION_KNOWLEDGE.md"
        self.assertTrue(retired.is_file())
        self.assertIn("FROZEN", retired.read_text(encoding="utf-8"))

    def test_risk_axes(self):
        text = (ROOT / "PROCESS_POLICY.md").read_text(encoding="utf-8")
        for key in (
            "failure_frequency",
            "ambiguity",
            "blast_radius",
            "known_solution_confidence",
            "dependency_volatility",
            "rollback_difficulty",
        ):
            self.assertIn(key, text)

    def test_authority(self):
        text = (ROOT / "AUTHORITY_SEPARATION.md").read_text(encoding="utf-8")
        self.assertIn("Execution Authority", text)
        self.assertIn("Proposal Authority", text)
        self.assertIn("人間の明示承認なしに適用しない", text)


if __name__ == "__main__":
    unittest.main()
