import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("task_splitter", ROOT / "runtime" / "task_splitter.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

CACHE = {"git_head": "abc", "important_files": ["AGENTS.md"], "protected_paths": ["LICENSE"]}


class TaskSplitterTests(unittest.TestCase):
    def test_direct_for_one_responsibility(self):
        result = module.create_plan(CACHE, "change runtime", ["runtime/a.py", "runtime/b.py"], "python test.py")
        self.assertEqual("DIRECT", result["route"])
        self.assertEqual(1, len(result["slices"]))

    def test_split_caps_at_three_disjoint_slices(self):
        targets = ["api/a.py", "ui/b.py", "tests/c.py", "docs/d.md"]
        result = module.create_plan(CACHE, "multi", targets, "python test.py")
        self.assertEqual("SPLIT", result["route"])
        self.assertEqual(3, len(result["slices"]))
        module.assert_disjoint(result["slices"])
        writable = [path for item in result["slices"] for path in item["writable_paths"]]
        self.assertEqual(sorted(targets), sorted(writable))

    def test_protected_target_stops(self):
        result = module.create_plan(CACHE, "license", ["LICENSE"], "python test.py")
        self.assertEqual("STOP", result["route"])

    def test_unsafe_target_is_rejected(self):
        with self.assertRaises(ValueError):
            module.create_plan(CACHE, "escape", ["../outside.py"], "python test.py")


if __name__ == "__main__":
    unittest.main()
