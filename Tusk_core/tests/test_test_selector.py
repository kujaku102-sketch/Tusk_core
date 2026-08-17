import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("test_selector", ROOT / "tools" / "test_selector.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TestSelectorTests(unittest.TestCase):
    def test_mapped_change_selects_focused_test(self):
        mapping = MODULE.load_map(ROOT / "TEST-MAP.json")
        stage, tests, reason, unmatched = MODULE.select(ROOT, mapping, "focused", ["tools/integrity_gate.py"])
        self.assertEqual(stage, "focused")
        self.assertIn("tests/test_integrity_gate.py", tests)
        self.assertEqual(reason, "mapped_change")
        self.assertEqual(unmatched, [])

    def test_unmapped_change_escalates_to_component(self):
        mapping = MODULE.load_map(ROOT / "TEST-MAP.json")
        stage, tests, reason, unmatched = MODULE.select(ROOT, mapping, "focused", ["unknown.py"])
        self.assertEqual(stage, "component")
        self.assertIn("tests/test_test_selector.py", tests)
        self.assertEqual(reason, "unmapped_change")
        self.assertEqual(unmatched, ["unknown.py"])

    def test_component_and_full_expand_suite(self):
        mapping = MODULE.load_map(ROOT / "TEST-MAP.json")
        component = MODULE.select(ROOT, mapping, "component", [])[1]
        full = MODULE.select(ROOT, mapping, "full", [])[1]
        self.assertEqual(component, full)
        self.assertIn("tests/test_common_test_guard_monitor.py", full)

    def test_invalid_map_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "map.json"
            path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            with self.assertRaises(ValueError):
                MODULE.load_map(path)


if __name__ == "__main__":
    unittest.main()
