import json
import sys
import unittest
from runtime import test_guard as module


class TestGuardTests(unittest.TestCase):
    def test_success_emits_done(self):
        result = module.run_guard([sys.executable, "-c", "print('ok')"], 5)
        self.assertEqual("success", result["status"])
        self.assertEqual("DONE", result["events"][-1]["event"])

    def test_nonzero_emits_fail(self):
        result = module.run_guard([sys.executable, "-c", "raise SystemExit(3)"], 5)
        self.assertEqual("failed", result["status"])
        self.assertEqual("F004", result["events"][-1]["code"])

    def test_timeout_emits_fail(self):
        result = module.run_guard([sys.executable, "-c", "import time; time.sleep(2)"], 1)
        self.assertEqual("failed", result["status"])
        self.assertIn("timeout", result["events"][-1]["message"])
        json.dumps(result)


if __name__ == "__main__":
    unittest.main()
