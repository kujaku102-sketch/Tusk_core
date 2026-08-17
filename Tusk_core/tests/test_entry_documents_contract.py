from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EntryDocumentsContractTests(unittest.TestCase):
    def test_start_here_is_short_and_routes_only(self):
        text = (ROOT / "START-HERE.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 20)
        for target in ("AGENTS.md", "GENERAL.md", "TEST_POLICY.md", "ERROR_POLICY.md"):
            self.assertIn(target, text)

    def test_agent_contract_owns_ai_rules(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for phrase in ("MAX_REWORK_COUNT = 3", "preflight_error", "SYNC-409", "Work Packetを作らない"):
            self.assertIn(phrase, text)

    def test_readme_is_human_overview(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Setup", text)
        self.assertIn("## Common commands", text)
        self.assertNotIn("## Work boundary", text)


if __name__ == "__main__":
    unittest.main()
