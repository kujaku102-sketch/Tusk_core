import importlib.util
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PATH = Path(__file__).resolve().parents[1] / "role_adapter.py"
SPEC = importlib.util.spec_from_file_location("role_adapter", PATH)
role_adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(role_adapter)


class RoleAdapterTests(unittest.TestCase):
    def test_all_adapters_validate(self):
        for name in ("codex", "claude"):
            role_adapter.load_adapter(name)

    def test_codex_current_high_route(self):
        result = role_adapter.resolve("codex", "implementation", "HIGH")
        self.assertEqual("gpt-6-sol", result["model"])
        self.assertEqual("medium", result["reasoning_effort"])
        self.assertEqual("write_limited", result["access"])

    def test_claude_role_families(self):
        self.assertEqual("Fable", role_adapter.resolve("claude", "lead")["model"])
        self.assertEqual("Sonnet", role_adapter.resolve("claude", "skim")["model"])
        self.assertEqual("Opus", role_adapter.resolve("claude", "implementation", "MID")["model"])
        self.assertEqual("Fable", role_adapter.resolve("claude", "review", "MAX")["model"])

    def test_environment_override(self):
        with mock.patch.dict(os.environ, {"TUSK_CLAUDE_MID_MODEL": "custom-sonnet-id"}):
            self.assertEqual("custom-sonnet-id", role_adapter.resolve("claude", "implementation", "MID")["model"])

    def test_read_only_roles_cannot_receive_intensity(self):
        with self.assertRaises(ValueError):
            role_adapter.resolve("codex", "skim", "LOW")

    def test_active_profile_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            default = role_adapter.load_adapter("codex")
            default.pop("selected_profile")
            custom = json.loads(json.dumps(default))
            custom["bindings"]["skim"]["model_alias"] = "custom-model"
            for name, data in (("default", default), ("custom", custom)):
                (root / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
            config = root / "config.json"
            config.write_text(json.dumps({"schema_version": 1, "adapter_id": "codex", "active_profile": "custom", "profiles": {"default": "default.json", "custom": "custom.json"}}), encoding="utf-8")
            self.assertEqual("custom-model", role_adapter.resolve("codex", "skim", config_path=config)["model"])
            self.assertEqual("default", role_adapter.resolve("codex", "skim", config_path=config, profile="default")["profile"])
            with self.assertRaises(ValueError):
                role_adapter.resolve("codex", "skim", config_path=config, profile="missing")

    def test_profile_cannot_expand_role_access(self):
        data = role_adapter.load_adapter("codex")
        data["bindings"]["review"]["MAX"]["access"] = "write_limited"
        with self.assertRaises(ValueError):
            role_adapter.validate_adapter(data)


if __name__ == "__main__":
    unittest.main()
