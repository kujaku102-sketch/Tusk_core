import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContractFileTests(unittest.TestCase):
    def test_all_json_contracts_parse(self):
        paths = list((ROOT / "schemas").glob("*.json")) + list((ROOT / "policy").glob("*.json")) + list((ROOT / "runtime").glob("*.json"))
        for path in paths:
            with self.subTest(path=path.name):
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_minimal_authorities_exist(self):
        for relative in ("AGENTS.md", "policy/GRAMMAR.md", "policy/ERROR_CODES.json"):
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
