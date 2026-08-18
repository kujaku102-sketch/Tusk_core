import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "extension_manager.py"
ACTIVATION_EXAMPLE = Path(__file__).resolve().parents[2] / "work" / "settings" / "extensions.enabled.json.example"
SPEC = importlib.util.spec_from_file_location("extension_manager", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExtensionManagerTests(unittest.TestCase):
    def make_extension(self, root: Path, name: str = "Tusk_Test") -> None:
        target = root / name
        target.mkdir(parents=True)
        entry = target / "AGENTS.md"
        entry.write_text("test", encoding="utf-8")
        digest = MODULE.hashlib.sha256(entry.read_bytes()).hexdigest()
        manifest = {"schema_version": 1, "root": name, "entry": "AGENTS.md", "algorithm": "sha256", "managed_files": [{"path": "AGENTS.md", "sha256": digest}]}
        (target / "EXTENSION-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_discover_uses_tusk_prefix_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Tusk_A").mkdir()
            (root / "Other").mkdir()
            self.assertEqual(MODULE.discover(root), ["Tusk_A"])

    def test_enable_requires_valid_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "extensions"
            registry = Path(temp) / "work" / "extensions.enabled.json"
            self.make_extension(root)
            result = MODULE.set_enabled(root, registry, "Tusk_Test", True)
            self.assertEqual(result["enabled_extensions"][0]["id"], "tusk_test")

    def test_inactive_extension_is_not_validated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Tusk_Broken").mkdir()
            self.assertEqual(MODULE.discover(root), ["Tusk_Broken"])

    def test_activation_example_matches_registry_schema(self):
        example = json.loads(ACTIVATION_EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(
            set(example),
            {"schema_version", "enabled_extensions", "disabled_extensions"},
        )
        self.assertEqual(MODULE.load_registry(ACTIVATION_EXAMPLE), example)


if __name__ == "__main__":
    unittest.main()
