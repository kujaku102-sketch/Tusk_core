import importlib.util
import os
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
        self.assertEqual("gpt-5.6-terra", result["model"])
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


if __name__ == "__main__":
    unittest.main()
