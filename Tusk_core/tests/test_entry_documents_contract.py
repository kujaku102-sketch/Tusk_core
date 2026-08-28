from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EntryDocumentsContractTests(unittest.TestCase):
    def test_start_here_is_short_and_routes_only(self):
        text = (ROOT / "START-HERE.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 20)
        for target in ("AGENTS.md", "GENERAL.md", "TEST_POLICY.md", "ERROR_POLICY.md"):
            self.assertIn(target, text)

    def test_agent_contract_routes_without_redefining_policy_details(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for phrase in ("PROCESS_POLICY.md", "TEST_POLICY.md", "SYNC-409", "Work Packetを作らない"):
            self.assertIn(phrase, text)
        self.assertNotIn("MAX_REWORK_COUNT = 3", text)
        self.assertNotIn("`preflight_error`は", text)
        self.assertIn("MAX_REWORK_COUNT = 3", (ROOT / "PROCESS_POLICY.md").read_text(encoding="utf-8"))
        self.assertIn("`preflight_error`", (ROOT / "TEST_POLICY.md").read_text(encoding="utf-8"))

    def test_readme_is_human_overview(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Setup", text)
        self.assertIn("## Common commands", text)
        self.assertNotIn("## Work boundary", text)


if __name__ == "__main__":
    unittest.main()
