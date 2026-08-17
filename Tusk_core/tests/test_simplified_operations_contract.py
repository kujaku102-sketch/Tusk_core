import unittest
from pathlib import Path


CORE = Path(__file__).resolve().parents[1]


class SimplifiedOperationsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.general = (CORE / "GENERAL.md").read_text(encoding="utf-8")
        cls.focus = (CORE / "FOCUS_CACHE_SPEC.md").read_text(encoding="utf-8")
        cls.authority = (CORE / "AUTHORITY_SEPARATION.md").read_text(encoding="utf-8")

    def test_focus_cache_is_landmine_count_only(self):
        self.assertIn("work/focus_cache/LANDMINES.md", self.focus)
        self.assertIn("- 発生回数:", self.focus)
        self.assertIn("- 地雷:", self.focus)
        self.assertIn("- 原因:", self.focus)
        self.assertIn("- 正解パターン:", self.focus)
        self.assertIn("成功時はFocus Cacheを更新しない", self.general)

    def test_complex_focus_mechanisms_are_disabled(self):
        for value in ("revision鎖", "reservation", "promotion", "transient", "handoff"):
            self.assertIn(value, self.focus)
        self.assertIn("新規運用で使用しない", self.general)

    def test_normal_work_has_no_intermediate_human_approval(self):
        self.assertIn("途中承認を要求せず", self.general)
        self.assertIn("人間の明示承認が必要なのは", self.general)
        self.assertIn("非常時rollback", self.general)

    def test_tests_are_script_driven_and_agents_run_only_on_failure(self):
        self.assertIn("テスト実行専用エージェントは配置しない", self.general)
        self.assertIn("成功時は解析担当やテスト担当エージェントを起動しない", self.authority)
        self.assertIn("失敗時だけ構造化ログを調査", self.authority)


if __name__ == "__main__":
    unittest.main()
