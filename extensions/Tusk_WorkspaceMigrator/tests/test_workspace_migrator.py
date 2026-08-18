import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "workspace_migrator.py"
SPEC = importlib.util.spec_from_file_location("workspace_migrator", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class WorkspaceMigratorTests(unittest.TestCase):
    def roots(self, root: Path) -> tuple[Path, Path]:
        legacy = root / "legacy"
        workspace = root / "current"
        (legacy / "extensions" / "Tusk_Test" / "tools").mkdir(parents=True)
        (legacy / "extensions" / "Tusk_Test" / "work" / "cache").mkdir(parents=True)
        (legacy / "work" / "runs" / "RUN-1").mkdir(parents=True)
        (workspace / "Tusk_core").mkdir(parents=True)
        (workspace / "extensions").mkdir()
        (workspace / "Tusk_core" / "AGENTS.md").write_text("core\n", encoding="utf-8")
        extension = legacy / "extensions" / "Tusk_Test"
        (extension / "AGENTS.md").write_text("entry\n", encoding="utf-8")
        (extension / "tools" / "tool.py").write_text("VALUE = 1\n", encoding="utf-8")
        (extension / "work" / "cache" / "secret.log").write_text("legacy\n", encoding="utf-8")
        (extension / "token.json").write_text("secret\n", encoding="utf-8")
        (extension / "EXTENSION-MANIFEST.json").write_text("{}\n", encoding="utf-8")
        return legacy, workspace

    def test_inspect_is_read_only_and_reports_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            legacy, workspace = self.roots(Path(temp))
            plan = MODULE.build_plan(legacy, workspace)
            self.assertEqual(plan["state"], "ready")
            self.assertEqual(plan["legacy_run_count"], 1)
            self.assertEqual(plan["selected_extensions"][0]["name"], "Tusk_Test")
            self.assertFalse((workspace / "work").exists())

    def test_stage_excludes_runtime_and_secrets_and_generates_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            legacy, workspace = self.roots(Path(temp))
            result = MODULE.stage(legacy, workspace, "MIG-1", ["Tusk_Test"], True)
            staged = workspace / "work" / "migrations" / "MIG-1" / "staged_extensions" / "Tusk_Test"
            self.assertEqual(result["state"], "staged")
            self.assertTrue((staged / "AGENTS.md").is_file())
            self.assertTrue((staged / "tools" / "tool.py").is_file())
            self.assertFalse((staged / "work").exists())
            self.assertFalse((staged / "token.json").exists())
            manifest = json.loads((staged / "EXTENSION-MANIFEST.json").read_text(encoding="utf-8"))
            rows = {row["path"]: row["sha256"] for row in manifest["managed_files"]}
            self.assertEqual(rows["AGENTS.md"], MODULE.digest(staged / "AGENTS.md"))
            self.assertNotIn("EXTENSION-MANIFEST.json", rows)
            scope = manifest["runtime_scope"]
            self.assertTrue(scope["workspace_required"])
            self.assertEqual(scope["owned_paths"], ["extensions/Tusk_Test"])
            self.assertEqual(
                set(scope["derived_from"]),
                {"activation", "current_task", "current_spec", "git_diff", "validated_context_cache"},
            )
            self.assertTrue(scope["excluded_paths"])

    def test_stage_never_overwrites_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            legacy, workspace = self.roots(Path(temp))
            MODULE.stage(legacy, workspace, "MIG-1", None, True)
            with self.assertRaises(MODULE.MigrationError) as raised:
                MODULE.stage(legacy, workspace, "MIG-1", None, True)
            self.assertEqual(raised.exception.code, "TUSK_MIGRATION_DESTINATION_EXISTS")

    def test_stage_requires_apply(self):
        with tempfile.TemporaryDirectory() as temp:
            legacy, workspace = self.roots(Path(temp))
            with self.assertRaises(MODULE.MigrationError) as raised:
                MODULE.stage(legacy, workspace, "MIG-1", None, False)
            self.assertEqual(raised.exception.code, "TUSK_MIGRATION_WRITE_REQUIRES_APPLY")

    def test_same_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Tusk_core").mkdir()
            (root / "Tusk_core" / "AGENTS.md").write_text("core\n", encoding="utf-8")
            (root / "extensions").mkdir()
            with self.assertRaises(MODULE.MigrationError) as raised:
                MODULE.build_plan(root, root)
            self.assertEqual(raised.exception.code, "TUSK_MIGRATION_INVALID_ROOT")


if __name__ == "__main__":
    unittest.main()
