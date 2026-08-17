from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.tusk_manager import (
    init_workspace,
    list_extensions,
    set_extension_enabled,
    install_extension,
    remove_extension,
    check_updates,
    uninstall_workspace,
)


class TestTuskManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir) / "test_ws"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_workspace(self):
        res = init_workspace(self.workspace)
        self.assertEqual(res["status"], "success")
        self.assertTrue((self.workspace / "work" / "settings" / "extensions.enabled.json").is_file())
        self.assertTrue((self.workspace / "work" / "focus_cache" / "LANDMINES.md").is_file())
        self.assertTrue((self.workspace / "developer.key.json").is_file())
        self.assertTrue((self.workspace / "extensions").is_dir())

    def test_extension_lifecycle(self):
        # 1. Init
        init_workspace(self.workspace)

        # 2. ダミー拡張作成
        dummy_ext_src = Path(self.temp_dir) / "Tusk_Dummy"
        dummy_ext_src.mkdir()
        entry_file = dummy_ext_src / "AGENTS.md"
        entry_file.write_bytes(b"# Dummy Extension\n")

        manifest_data = {
            "root": "Tusk_Dummy",
            "entry": "AGENTS.md",
            "algorithm": "sha256",
            "managed_files": [
                {
                    "path": "AGENTS.md",
                    "sha256": "d6d420898c8a98ab175244f60c85363fb40e8d042aec34ddc5044724eae0f451" # SHA of '# Dummy Extension\n'
                }
            ]
        }
        (dummy_ext_src / "EXTENSION-MANIFEST.json").write_text(
            json.dumps(manifest_data, indent=2), encoding="utf-8"
        )

        # 3. Install & Auto-enable
        inst_res = install_extension(self.workspace, dummy_ext_src, enable=True)
        self.assertEqual(inst_res["status"], "success")

        # 4. List check
        list_res = list_extensions(self.workspace)
        self.assertIn("Tusk_Dummy", list_res["available_extensions"])
        self.assertIn("tusk_dummy", list_res["enabled_extensions"])

        # 5. Disable
        dis_res = set_extension_enabled(self.workspace, "Tusk_Dummy", False)
        self.assertEqual(dis_res["status"], "success")
        self.assertFalse(dis_res["enabled"])

        list_res2 = list_extensions(self.workspace)
        self.assertNotIn("tusk_dummy", list_res2["enabled_extensions"])
        self.assertIn("tusk_dummy", list_res2["disabled_extensions"])

        # 6. Re-enable
        en_res = set_extension_enabled(self.workspace, "Tusk_Dummy", True)
        self.assertEqual(en_res["status"], "success")
        self.assertTrue(en_res["enabled"])

        # 7. Check updates
        up_res = check_updates(self.workspace)
        self.assertIn("Tusk_Dummy", up_res["components"])
        self.assertEqual(up_res["components"]["Tusk_Dummy"]["status"], "up_to_date")

        # 8. Remove
        rem_res = remove_extension(self.workspace, "Tusk_Dummy")
        self.assertEqual(rem_res["status"], "success")
        self.assertFalse((self.workspace / "extensions" / "Tusk_Dummy").exists())

    def test_uninstall_workspace(self):
        init_workspace(self.workspace)
        self.assertTrue((self.workspace / "work").is_dir())

        # Non-purge uninstall (cleans work/tmp/key)
        un_res = uninstall_workspace(self.workspace, purge=False)
        self.assertEqual(un_res["status"], "success")
        self.assertFalse((self.workspace / "work").exists())
        self.assertFalse((self.workspace / "developer.key.json").exists())
        self.assertTrue(self.workspace.exists()) # Workspace root itself remains

        # Purge uninstall
        purge_res = uninstall_workspace(self.workspace, purge=True)
        self.assertEqual(purge_res["status"], "success")
        self.assertFalse(self.workspace.exists())


if __name__ == "__main__":
    unittest.main()
