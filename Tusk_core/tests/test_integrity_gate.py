from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "tools" / "integrity_gate.py"


class IntegrityGateTests(unittest.TestCase):
    def run_cli(self, workspace: Path, store: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), "--workspace", str(workspace), "--trust-store", str(store), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def setup_workspace(self, root: Path) -> tuple[Path, Path, Path]:
        workspace = root / "workspace"
        package = workspace / "Tusk_core"
        package.mkdir(parents=True)
        key = {"schema_version": 1, "authority_id": "key-1", "workspace_id": "test", "allowed_scopes": ["Tusk_core"]}
        (workspace / "developer.key.json").write_text(json.dumps(key), encoding="utf-8")
        target = package / "file.txt"
        target.write_text("original", encoding="utf-8")
        manifest = {"algorithm": "sha256", "managed_files": [{"path": "file.txt", "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}]}
        manifest_path = package / "DISTRIBUTION-MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8-sig")
        return workspace, package, manifest_path

    def test_trusted_development_key_allows_source_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace, package, manifest = self.setup_workspace(Path(temporary))
            store = Path(temporary) / "trust.json"
            self.assertEqual(0, self.run_cli(workspace, store, "trust").returncode)
            (package / "file.txt").write_text("edited", encoding="utf-8")
            result = self.run_cli(workspace, store, "verify", "--scope", "Tusk_core", "--mode", "development", "--package-root", str(package), "--manifest", str(manifest))
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("integrity=development-warning", result.stdout)

    def test_release_never_accepts_development_bypass(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace, package, manifest = self.setup_workspace(Path(temporary))
            store = Path(temporary) / "trust.json"
            self.run_cli(workspace, store, "trust")
            (package / "file.txt").write_text("edited", encoding="utf-8")
            result = self.run_cli(workspace, store, "verify", "--scope", "Tusk_core", "--mode", "release", "--package-root", str(package), "--manifest", str(manifest))
            self.assertEqual(4, result.returncode)

    def test_key_change_revokes_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _, _ = self.setup_workspace(Path(temporary))
            store = Path(temporary) / "trust.json"
            self.run_cli(workspace, store, "trust")
            key_path = workspace / "developer.key.json"
            key = json.loads(key_path.read_text(encoding="utf-8"))
            key["allowed_scopes"].append("extensions/Tusk_DTP")
            key_path.write_text(json.dumps(key), encoding="utf-8")
            result = self.run_cli(workspace, store, "check", "--scope", "Tusk_core", "--mode", "development")
            self.assertEqual(3, result.returncode)


if __name__ == "__main__":
    unittest.main()
