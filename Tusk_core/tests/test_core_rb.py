from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools import landmine_cache, test_guard_monitor, test_selector


CORE_ROOT = Path(__file__).resolve().parents[1]


class TestTuskCoreRb(unittest.TestCase):
    def test_entry_and_authority_documents_exist(self) -> None:
        auth_map = json.loads((CORE_ROOT / "AUTHORITY-MAP.json").read_text(encoding="utf-8"))
        self.assertEqual(auth_map["schema_version"], 2)
        for row in auth_map["authorities"]:
            doc_path = CORE_ROOT / row["canonical"]
            self.assertTrue(doc_path.is_file(), f"Missing canonical doc: {row['canonical']}")

        gemini_txt = (CORE_ROOT / "profiles" / "GEMINI_PROFILE.md").read_text(encoding="utf-8")
        claude_txt = (CORE_ROOT / "profiles" / "CLAUDE_PROFILE.md").read_text(encoding="utf-8")
        codex_txt = (CORE_ROOT / "profiles" / "CODEX_PROFILE.md").read_text(encoding="utf-8")
        self.assertIn("flash_lite", gemini_txt)
        self.assertNotIn("gpt-6-sol", gemini_txt)
        self.assertIn("haiku", claude_txt)
        self.assertNotIn("gpt-6-sol", claude_txt)
        self.assertIn("gpt-6-sol", codex_txt)
        self.assertNotIn("flash_lite", codex_txt)

    def test_error_registry_and_product_codes_6xx_to_9xx(self) -> None:
        reg = test_guard_monitor.parse_error_registry(CORE_ROOT / "ERROR_CODES.md")
        # 1XX-5XX fixed domain codes
        self.assertIn("F101", reg["force"])
        self.assertIn("F201", reg["force"])
        self.assertIn("F301", reg["force"])
        self.assertIn("F401", reg["force"])
        self.assertIn("F501", reg["force"])
        self.assertIn("M201", reg["minor"])

        # Product custom codes (6XX-9XX) should be accepted automatically by F/M prefix + digits
        f_marker = test_guard_monitor.parse_event(
            "[TUSK_FORCE_STOP] run_id=r1 code=F601 component=dtp step=render reason=frame_overflow",
            "r1",
            reg,
        )
        self.assertIsNotNone(f_marker)
        code, err = test_guard_monitor.validate_issue(f_marker, reg)
        self.assertEqual(code, "F601")
        self.assertIsNone(err)

        m_marker = test_guard_monitor.parse_event(
            "[TUSK_MINOR_ISSUE] run_id=r1 code=M842 component=ui step=check target=btn1 detail=minor_shift",
            "r1",
            reg,
        )
        self.assertIsNotNone(m_marker)
        code_m, err_m = test_guard_monitor.validate_issue(m_marker, reg)
        self.assertEqual(code_m, "M842")
        self.assertIsNone(err_m)

        # Unregistered code in fixed range (1XX-5XX) must be rejected
        bad_fixed = test_guard_monitor.parse_event(
            "[TUSK_FORCE_STOP] run_id=r1 code=F299 component=core step=s reason=unknown_fixed",
            "r1",
            reg,
        )
        _, err_bad = test_guard_monitor.validate_issue(bad_fixed, reg)
        self.assertEqual(err_bad, "unregistered_code_or_severity_mismatch")

    def test_landmine_cache_and_test_selector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            args = argparse.Namespace(
                workspace=ws,
                error_key="err.01",
                landmine="bad pattern",
                cause="root cause",
                correct_pattern="good pattern",
                target="modA",
                confirmed_on="2026-10-22",
            )
            landmine_cache.record(args)
            l_path = landmine_cache.cache_path(ws)
            self.assertTrue(l_path.is_file())
            self.assertIn("err.01", l_path.read_text(encoding="utf-8"))

        mapping = test_selector.load_map(CORE_ROOT / "TEST-MAP.json")
        effective, selected, _, _ = test_selector.select(
            CORE_ROOT, mapping, "focused", ["extensions.json"]
        )
        self.assertEqual(effective, "focused")
        self.assertEqual(selected, ["tests/test_core_rb.py"])


if __name__ == "__main__":
    unittest.main()
