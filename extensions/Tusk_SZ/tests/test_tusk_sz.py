import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "tusk_sz.py"
SPEC = importlib.util.spec_from_file_location("tusk_sz", MODULE_PATH)
assert SPEC and SPEC.loader
tusk_sz = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tusk_sz
SPEC.loader.exec_module(tusk_sz)


def args_for(profile: str, workspace: Path, **overrides):
    values = {
        "profile": profile,
        "workspace": str(workspace),
        "evidence_dir": None,
        "evidence_root": str(tusk_sz.DEFAULT_EVIDENCE_ROOT),
        "run_id": "TEST-RUN",
        "apply": False,
        "node": None,
        "browser": None,
        "powershell": None,
        "python": None,
        "illustrator": None,
        "port": 4173,
        "build_timeout": 3,
        "probe_timeout": 3,
        "server_timeout": 3,
        "scenario_timeout": 3,
        "renderer_timeout": 3,
        "card_id": None,
        "allow_cache": False,
        "audit_only": False,
        "force": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def make_web_workspace(root: Path):
    (root / "tools").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "node_modules/vite/bin").mkdir(parents=True)
    (root / "node_modules/vite/dist/node").mkdir(parents=True)
    (root / "AGENTS.md").write_text("rules", encoding="utf-8")
    (root / "package.json").write_text(json.dumps({
        "name": "simple-zeke",
        "scripts": {"build": "vite build", "smoke:ui": "node scripts/smoke-ui.mjs"},
    }), encoding="utf-8")
    (root / "tools/serve.mjs").write_text("// server", encoding="utf-8")
    (root / "scripts/smoke-ui.mjs").write_text(
        'import { chromium } from "file:///C:/missing/playwright/index.mjs";', encoding="utf-8")
    (root / "node_modules/vite/bin/vite.js").write_text("// vite", encoding="utf-8")
    (root / "node_modules/vite/dist/node/index.js").write_text("export const ok = true;", encoding="utf-8")


def make_illustrator_workspace(root: Path, template: bool = False):
    for relative in ("tools/windows", "illustrator/scripts", "src/siege_export"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text("[project]\nname='siege-zeke'\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("rules", encoding="utf-8")
    (root / "tools/windows/render_card.ps1").write_text("exit 0", encoding="utf-8")
    (root / "illustrator/scripts/render_card.jsx").write_text("", encoding="utf-8")
    (root / "illustrator/scripts/template_audit.jsx").write_text("", encoding="utf-8")
    if template:
        (root / "illustrator/templates").mkdir(parents=True)
        (root / "illustrator/templates/card_v1.ai").write_bytes(b"AI")


class PathSafetyTests(unittest.TestCase):
    def test_strict_containment_accepts_descendant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(tusk_sz.is_strictly_contained(root / "packet/web", root))

    def test_strict_containment_rejects_equal_and_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(tusk_sz.is_strictly_contained(root, root))
            self.assertFalse(tusk_sz.is_strictly_contained(root / ".." / "outside", root))

    def test_validate_evidence_raises_f202(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(tusk_sz.TuskError) as caught:
                tusk_sz.validate_evidence_path(root, root)
            self.assertEqual(caught.exception.code, "F202")


class IdentityAndInspectTests(unittest.TestCase):
    def test_web_identity_is_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_web_workspace(root)
            self.assertTrue(tusk_sz.web_identity(root)["ok"])
            data = json.loads((root / "package.json").read_text(encoding="utf-8"))
            data["name"] = "wrong-product"
            (root / "package.json").write_text(json.dumps(data), encoding="utf-8")
            self.assertFalse(tusk_sz.web_identity(root)["ok"])

    def test_default_inspect_does_not_create_workspace_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_web_workspace(root)
            before = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
            with mock.patch.object(tusk_sz, "resolve_runtime", return_value={"available": True, "path": str(sys.executable), "origin": "test"}), \
                 mock.patch.object(tusk_sz, "playwright_import", return_value={"available": True, "path": "playwright", "origin": "test"}), \
                 mock.patch.object(tusk_sz, "probe_node_esm_import", return_value={
                     "available": True, "probed": True, "path": "module", "exit_code": 0,
                     "timed_out": False, "duration_seconds": 0.1, "detail": "import_ok"}):
                result = tusk_sz.inspect_web(args_for("web", root), root, None)
            after = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
            self.assertEqual(before, after)
            self.assertEqual(result["mode"], "inspect")
            self.assertEqual(result["overall_status"], "ready")
            self.assertEqual({result["layers"][name]["status"] for name in ("renderer", "ui", "e2e")}, {"ready"})

    def test_missing_node_blocks_without_layer_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_web_workspace(root)
            with mock.patch.object(tusk_sz, "resolve_runtime", return_value={"available": False, "path": None, "origin": None}):
                result = tusk_sz.inspect_web(args_for("web", root), root, None)
            self.assertFalse(result["ok"])
            self.assertEqual(result["layers"]["renderer"]["code"], "F201")
            self.assertNotEqual(result["layers"]["ui"]["status"], "passed")
            self.assertNotEqual(result["layers"]["e2e"]["status"], "passed")

    def test_broken_vite_import_blocks_every_web_layer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_web_workspace(root)
            ready = {"available": True, "path": "runtime", "origin": "test"}
            broken = {"available": False, "probed": True, "path": "vite", "exit_code": 1,
                      "timed_out": False, "duration_seconds": 0.1, "detail": "ERR_MODULE_NOT_FOUND"}
            with mock.patch.object(tusk_sz, "resolve_runtime", return_value=ready), \
                 mock.patch.object(tusk_sz, "playwright_import", return_value=ready), \
                 mock.patch.object(tusk_sz, "probe_node_esm_import", return_value=broken):
                result = tusk_sz.inspect_web(args_for("web", root), root, None)
            self.assertEqual([result["layers"][name]["status"] for name in ("renderer", "ui", "e2e")],
                             ["blocked", "blocked", "blocked"])
            self.assertTrue(all(result["layers"][name]["code"] == "F201" for name in ("renderer", "ui", "e2e")))

    def test_broken_playwright_import_preserves_renderer_ready_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_web_workspace(root)
            ready_runtime = {"available": True, "path": "runtime", "origin": "test"}
            good = {"available": True, "probed": True, "path": "vite", "exit_code": 0,
                    "timed_out": False, "duration_seconds": 0.1, "detail": "import_ok"}
            broken = {"available": False, "probed": True, "path": "playwright", "exit_code": 1,
                      "timed_out": False, "duration_seconds": 0.1, "detail": "ERR_MODULE_NOT_FOUND"}
            with mock.patch.object(tusk_sz, "resolve_runtime", return_value=ready_runtime), \
                 mock.patch.object(tusk_sz, "playwright_import", return_value=ready_runtime), \
                 mock.patch.object(tusk_sz, "probe_node_esm_import", side_effect=(good, broken)):
                result = tusk_sz.inspect_web(args_for("web", root), root, None)
            self.assertEqual(result["layers"]["renderer"]["status"], "ready")
            self.assertEqual(result["layers"]["ui"]["code"], "F201")
            self.assertEqual(result["layers"]["e2e"]["code"], "F201")
            self.assertEqual(result["overall_status"], "blocked")

    def test_missing_illustrator_template_is_precise_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_illustrator_workspace(root, template=False)
            result = tusk_sz.inspect_illustrator(args_for("illustrator", root), root, None)
            self.assertEqual(result["overall_status"], "blocked")
            self.assertEqual(result["layers"]["renderer"]["code"], "F204")
            self.assertEqual(result["layers"]["e2e"]["code"], "F204")
            self.assertEqual(result["layers"]["ui"]["status"], "not_applicable")


class RuntimeAndProcessTests(unittest.TestCase):
    def test_runtime_argument_precedes_environment_and_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            explicit = Path(tmp) / "runtime.exe"
            explicit.write_bytes(b"x")
            with mock.patch.dict(os.environ, {"TEST_RUNTIME": "missing"}), \
                 mock.patch.object(tusk_sz.shutil, "which", return_value=None):
                resolved = tusk_sz.resolve_runtime(str(explicit), "TEST_RUNTIME", ("runtime",), ())
            self.assertTrue(resolved["available"])
            self.assertEqual(resolved["origin"], "argument")

    def test_run_command_timeout_is_structured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = tusk_sz.run_command(
                [sys.executable, "-c", "import time; time.sleep(2)"], root, 1,
                root / "stdout.log", root / "stderr.log")
            self.assertTrue(result["timed_out"])
            self.assertIsNone(result["exit_code"])

    def test_spawned_process_cleanup_is_confirmed(self):
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                creationflags=flags, start_new_session=os.name != "nt")
        confirmed, _ = tusk_sz.stop_spawned_process(proc)
        self.assertTrue(confirmed)
        self.assertIsNotNone(proc.poll())

    def test_actual_node_probe_catches_stale_transitive_import(self):
        node = tusk_sz.resolve_runtime(None, "TEST_NO_NODE_ENV", ("node", "node.exe"), tusk_sz.node_fallbacks())
        if not node["available"]:
            self.skipTest("Node unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module = root / "stale.mjs"
            module.write_text("import './missing-transitive.mjs';", encoding="utf-8")
            result = tusk_sz.probe_node_esm_import(node["path"], str(module), root, 3)
            self.assertFalse(result["available"])
            self.assertEqual(result["exit_code"], 1)
            self.assertFalse(result["timed_out"])
            self.assertLessEqual(len(result["detail"]), 240)


class LayerAndResultTests(unittest.TestCase):
    def test_build_failure_cannot_become_ui_or_e2e_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "web"
            root.mkdir()
            make_web_workspace(root)
            evidence = Path(tmp) / "evidence"
            ready_runtime = {"available": True, "path": sys.executable, "origin": "test"}
            with mock.patch.object(tusk_sz, "resolve_runtime", return_value=ready_runtime), \
                 mock.patch.object(tusk_sz, "playwright_import", return_value=ready_runtime), \
                 mock.patch.object(tusk_sz, "probe_node_esm_import", return_value={
                     "available": True, "probed": True, "path": "module", "exit_code": 0,
                     "timed_out": False, "duration_seconds": 0.1, "detail": "import_ok"}), \
                 mock.patch.object(tusk_sz, "run_command", return_value={
                     "exit_code": 1, "timed_out": False, "duration_seconds": 0.1,
                     "stdout": "", "stderr": "failed"}):
                result = tusk_sz.apply_web(args_for("web", root, apply=True), root, evidence)
            self.assertEqual(result["layers"]["renderer"]["status"], "failed")
            self.assertEqual(result["layers"]["ui"]["status"], "blocked")
            self.assertEqual(result["layers"]["e2e"]["status"], "blocked")

    def test_result_validator_requires_three_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = tusk_sz.base_result(args_for("web", Path(tmp)), Path(tmp), None)
            result["finished_at"] = tusk_sz.utc_now()
            self.assertEqual(tusk_sz.validate_result(result), [])
            del result["layers"]["ui"]
            self.assertIn("layers.ui", tusk_sz.validate_result(result))

    def test_atomic_json_is_utf8_and_replaceable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            tusk_sz.atomic_write_json(path, {"text": "ジーグ"})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["text"], "ジーグ")
            self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_card_id_must_be_normalized_and_path_safe(self):
        self.assertTrue(tusk_sz.valid_card_id("STD-127"))
        for unsafe in (None, "", "std-127", "STD_127", "../STD-127", "STD-1/2", "STD-1234567"):
            self.assertFalse(tusk_sz.valid_card_id(unsafe))

    def test_png_output_requires_containment_suffix_size_and_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            output = workspace / "build/output/STD-127.png"
            output.parent.mkdir(parents=True)
            output.write_bytes(b"\x89PNG\r\n\x1a\ncontent")
            accepted, detail = tusk_sz.validate_png_output(workspace, "build/output/STD-127.png")
            self.assertEqual(accepted, output.resolve())
            self.assertEqual(detail, "valid_png")

            outside = Path(tmp) / "outside.png"
            outside.write_bytes(b"\x89PNG\r\n\x1a\ncontent")
            self.assertIsNone(tusk_sz.validate_png_output(workspace, str(outside))[0])
            fake = workspace / "build/output/fake.png"
            fake.write_bytes(b"not a png file")
            self.assertEqual(tusk_sz.validate_png_output(workspace, str(fake))[1], "output_png_signature_invalid")

    def test_unsafe_card_id_never_starts_product_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            make_illustrator_workspace(workspace, template=True)
            ready = {"available": True, "path": sys.executable, "origin": "test"}
            with mock.patch.object(tusk_sz, "resolve_runtime", return_value=ready), \
                 mock.patch.object(tusk_sz, "run_command") as runner:
                result = tusk_sz.apply_illustrator(
                    args_for("illustrator", workspace, apply=True, card_id="../STD-127"),
                    workspace, Path(tmp) / "evidence")
            runner.assert_not_called()
            self.assertEqual(result["layers"]["renderer"]["code"], "F200")


class CliBoundaryTests(unittest.TestCase):
    def test_apply_requires_evidence_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = args_for("web", Path(tmp), apply=True)
            with self.assertRaises(tusk_sz.TuskError) as caught:
                tusk_sz.execute(args)
            self.assertEqual(caught.exception.code, "F202")

    def test_parser_requires_explicit_workspace(self):
        parser = tusk_sz.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["--profile", "web"])


if __name__ == "__main__":
    unittest.main()
