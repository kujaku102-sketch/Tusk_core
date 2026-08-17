import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("context_cache", ROOT / "runtime" / "context_cache.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ContextCacheTests(unittest.TestCase):
    def test_builds_current_structure_without_work_or_symlinks(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            (root / "AGENTS.md").write_text("rules", encoding="utf-8")
            (root / "app.py").write_text("import json\nif __name__ == '__main__':\n    pass\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("import unittest\n", encoding="utf-8")
            (root / "work" / "logs").mkdir(parents=True)
            (root / "work" / "logs" / "run.log").write_text("FAIL sample\n", encoding="utf-8")
            result = module.build_cache(root)
            self.assertIn("AGENTS.md", result["important_files"])
            self.assertIn("app.py", result["entry_points"])
            self.assertTrue(result["test_commands"])
            self.assertEqual(["FAIL sample"], result["recent_failures"])
            self.assertFalse(any(path.startswith("work/") for path in result["important_files"]))


if __name__ == "__main__":
    unittest.main()
