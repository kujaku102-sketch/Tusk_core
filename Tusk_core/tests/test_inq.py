from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "inq.py"
AUTHORITY_MAP = ROOT / "AUTHORITY-MAP.json"


class InQTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(TOOL), "--workspace", str(self.workspace), "--authority-map", str(AUTHORITY_MAP), *args], text=True, capture_output=True, check=False)

    def add(self, target: str = "PROCESS_POLICY.md") -> subprocess.CompletedProcess[str]:
        return self.run_tool("add", "--id", "INQ-TEST-001", "--kind", "improvement", "--scope", "core", "--summary", "candidate", "--target-authority", target)

    def test_add_creates_non_authoritative_observation(self):
        result = self.add()
        self.assertEqual(result.returncode, 0, result.stderr)
        item = json.loads(result.stdout)
        self.assertEqual(item["state"], "observed")
        self.assertTrue((self.workspace / "work" / "inq" / "registry.json").is_file())

    def test_verified_requires_evidence_and_reviewer(self):
        self.add()
        self.assertEqual(self.run_tool("transition", "--id", "INQ-TEST-001", "--state", "candidate").returncode, 0)
        failed = self.run_tool("transition", "--id", "INQ-TEST-001", "--state", "verified")
        self.assertNotEqual(failed.returncode, 0)
        passed = self.run_tool("transition", "--id", "INQ-TEST-001", "--state", "verified", "--evidence", "tests/result.json", "--reviewer", "review:sol")
        self.assertEqual(passed.returncode, 0, passed.stderr)

    def test_proposed_requires_registered_authority(self):
        self.add("UNKNOWN.md")
        self.run_tool("transition", "--id", "INQ-TEST-001", "--state", "candidate")
        self.run_tool("transition", "--id", "INQ-TEST-001", "--state", "verified", "--evidence", "evidence.json", "--reviewer", "review:sol")
        result = self.run_tool("transition", "--id", "INQ-TEST-001", "--state", "proposed")
        self.assertNotEqual(result.returncode, 0)

    def test_adopted_requires_decision_and_does_not_edit_authority(self):
        before = (ROOT / "PROCESS_POLICY.md").read_bytes()
        self.add()
        self.run_tool("transition", "--id", "INQ-TEST-001", "--state", "candidate")
        self.run_tool("transition", "--id", "INQ-TEST-001", "--state", "verified", "--evidence", "evidence.json", "--reviewer", "review:sol")
        self.assertEqual(self.run_tool("transition", "--id", "INQ-TEST-001", "--state", "proposed").returncode, 0)
        self.assertNotEqual(self.run_tool("transition", "--id", "INQ-TEST-001", "--state", "adopted", "--reviewer", "lead:core").returncode, 0)
        self.assertEqual(self.run_tool("transition", "--id", "INQ-TEST-001", "--state", "adopted", "--reviewer", "lead:core", "--reason", "approved proposal").returncode, 0)
        self.assertEqual((ROOT / "PROCESS_POLICY.md").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
