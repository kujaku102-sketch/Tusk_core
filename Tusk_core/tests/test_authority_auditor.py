from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "authority_auditor.py"
MAP = ROOT / "AUTHORITY-MAP.json"


class AuthorityAuditorTests(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(TOOL), "--root", str(ROOT), "--map", str(MAP), *args], text=True, capture_output=True, check=False)

    def test_current_authorities_are_consistent(self):
        result = self.run_tool("audit")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["issues"], [])
        self.assertIn("DUPLICATE_AUTHORITY", payload["classifications"])

    def test_existing_concept_reuses_canonical(self):
        result = self.run_tool("creation-gate", "--concept", "process_safety", "--candidate", "NEW_PROCESS.md")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["decision"], "REUSE_EXISTING")

    def test_unconfirmed_new_concept_is_rejected(self):
        result = self.run_tool("creation-gate", "--concept", "deployment_policy", "--candidate", "DEPLOYMENT_POLICY.md")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["decision"], "REJECT")

    def test_confirmed_independent_concept_is_allowed_without_writing(self):
        candidate = "DEPLOYMENT_POLICY.md"
        result = self.run_tool("creation-gate", "--concept", "deployment_policy", "--candidate", candidate, "--independent-concept")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["decision"], "ALLOW_NEW_AUTHORITY")
        self.assertFalse((ROOT / candidate).exists())


if __name__ == "__main__":
    unittest.main()
