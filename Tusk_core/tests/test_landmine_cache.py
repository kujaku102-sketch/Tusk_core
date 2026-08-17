from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "tools" / "landmine_cache.py"


class LandmineCacheTests(unittest.TestCase):
    def run_cli(self, workspace: Path, key: str, cause: str = "原因") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--workspace",
                str(workspace),
                "record",
                "--error-key",
                key,
                "--landmine",
                "地雷",
                "--cause",
                cause,
                "--correct-pattern",
                "正解",
                "--target",
                "target",
                "--confirmed-on",
                "2026-08-16",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_new_record_and_duplicate_increment(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            first = self.run_cli(workspace, "test.example")
            second = self.run_cli(workspace, "test.example")
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            text = (workspace / "work" / "focus_cache" / "LANDMINES.md").read_text(encoding="utf-8")
            self.assertEqual(1, text.count("## test.example"))
            self.assertIn("- 発生回数: 2", text)
            self.assertTrue((workspace / "work" / "focus_cache" / "LANDMINES.previous.md").is_file())

    def test_records_sort_by_count_then_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            self.run_cli(workspace, "test.b")
            self.run_cli(workspace, "test.a")
            self.run_cli(workspace, "test.b")
            text = (workspace / "work" / "focus_cache" / "LANDMINES.md").read_text(encoding="utf-8")
            self.assertLess(text.index("## test.b"), text.index("## test.a"))


if __name__ == "__main__":
    unittest.main()
