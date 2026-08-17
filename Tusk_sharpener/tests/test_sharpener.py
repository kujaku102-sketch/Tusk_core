import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "sharpener.py"
SPEC = importlib.util.spec_from_file_location("tusk_sharpener", MODULE_PATH)
sharpener = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sharpener)


class SharpenerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "core"
        (self.root / "tests").mkdir(parents=True)
        (self.root / "A.md").write_text("# A\n", encoding="utf-8")
        (self.root / "R.md").write_text("See A.md\n", encoding="utf-8")
        (self.root / "ERROR_CODES.md").write_text("| F001 | fatal | description |\n| M001 | minor | description |\n", encoding="utf-8")
        (self.root / "tests" / "test_a.py").write_text("pass\n", encoding="utf-8")
        self.write_json("AUTHORITY-MAP.json", {"authorities": [{"concept": "a", "canonical": "A.md", "redirects": ["R.md"]}]})
        self.write_json("extensions.json", {"extensions": [{"id": "x", "entry": "../extensions/x"}]})
        self.write_json("TEST-MAP.json", {"focused_rules": [{"patterns": ["A.md"], "tests": ["tests/test_a.py"]}]})
        rows = []
        for value in ["A.md", "R.md", "ERROR_CODES.md", "AUTHORITY-MAP.json", "extensions.json", "TEST-MAP.json", "tests/test_a.py"]:
            rows.append({"path": value, "sha256": sharpener.sha256(self.root / value)})
        self.write_json("DISTRIBUTION-MANIFEST.json", {"managed_files": rows})

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, name, data):
        (self.root / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def test_healthy_fixture(self):
        self.assertEqual("healthy", sharpener.run_check(self.root, None)["status"])

    def test_authority_conflict(self):
        self.write_json("AUTHORITY-MAP.json", {"authorities": [
            {"concept": "a", "canonical": "A.md", "redirects": []},
            {"concept": "b", "canonical": "A.md", "redirects": []}]})
        codes = {item["code"] for item in sharpener.run_check(self.root, None)["issues"]}
        self.assertIn("AUTHORITY_PATH_CONFLICT", codes)

    def test_manifest_mismatch_is_repairable(self):
        (self.root / "A.md").write_text("changed\n", encoding="utf-8")
        items = sharpener.run_check(self.root, None)["issues"]
        self.assertTrue(any(item["code"] == "MANIFEST_SHA_MISMATCH" and item["repairable"] for item in items))

    def test_manifest_repair_preserves_rows(self):
        (self.root / "A.md").write_text("changed\n", encoding="utf-8")
        original_lines = (self.root / "DISTRIBUTION-MANIFEST.json").read_text(encoding="utf-8").splitlines()
        before = sharpener.load_json(self.root / "DISTRIBUTION-MANIFEST.json")["managed_files"]
        sharpener.repair_manifest(self.root)
        after = sharpener.load_json(self.root / "DISTRIBUTION-MANIFEST.json")["managed_files"]
        self.assertEqual([item["path"] for item in before], [item["path"] for item in after])
        self.assertEqual(len(original_lines), len((self.root / "DISTRIBUTION-MANIFEST.json").read_text(encoding="utf-8").splitlines()))
        self.assertEqual("healthy", sharpener.run_check(self.root, None)["status"])

    def test_duplicate_error_code(self):
        (self.root / "ERROR_CODES.md").write_text("| F001 | a | x |\n| F001 | b | y |\n", encoding="utf-8")
        self.assertIn("ERROR_CODE_DUPLICATE", {item["code"] for item in sharpener.run_check(self.root, None)["issues"]})

    def test_missing_test(self):
        self.write_json("TEST-MAP.json", {"focused_rules": [{"patterns": ["A.md"], "tests": ["tests/missing.py"]}]})
        self.assertIn("TEST_FILE_MISSING", {item["code"] for item in sharpener.run_check(self.root, None)["issues"]})

    def test_stale_cache_is_warning(self):
        workspace = Path(self.temp.name) / "workspace"
        cache = workspace / "work" / "context.json"
        cache.parent.mkdir(parents=True)
        cache.write_text("{}", encoding="utf-8")
        os.utime(cache, (1_600_000_000, 1_600_000_000))
        (workspace / "work" / "cache_index.json").write_text(json.dumps({"entries": [{"path": "work/context.json", "sha256": sharpener.sha256(cache)}]}), encoding="utf-8")
        result = sharpener.run_check(self.root, workspace)
        self.assertEqual("healthy", result["status"])
        self.assertIn("CACHE_STALE", {item["code"] for item in result["issues"]})

    def test_retired_scope_authority_is_rejected(self):
        (self.root / "MD_SCOPE_RULES.md").write_text("legacy", encoding="utf-8")
        codes = {item["code"] for item in sharpener.run_check(self.root, None)["issues"]}
        self.assertIn("RETIRED_SCOPE_AUTHORITY_ACTIVE", codes)

    def test_runtime_scope_contract_is_required_for_extensions(self):
        extension = self.root.parent / "extensions" / "sample"
        extension.mkdir(parents=True)
        (extension / "AGENTS.md").write_text("rules", encoding="utf-8")
        (extension / "EXTENSION-MANIFEST.json").write_text("{}", encoding="utf-8")
        codes = {item["code"] for item in sharpener.run_check(self.root, None)["issues"]}
        self.assertIn("RUNTIME_SCOPE_DERIVATION_INVALID", codes)
        self.assertIn("RUNTIME_SCOPE_PATHS_MISSING", codes)


if __name__ == "__main__":
    unittest.main()
