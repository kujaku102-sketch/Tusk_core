import unittest
from pathlib import Path


CORE = Path(__file__).resolve().parents[1]


class SimplifiedOperationsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.general = (CORE / "GENERAL.md").read_text(encoding="utf-8")
        cls.focus = (CORE / "FOCUS_CACHE_SPEC.md").read_text(encoding="utf-8")
        cls.authority = (CORE / "AUTHORITY_SEPARATION.md").read_text(encoding="utf-8")
        cls.process = (CORE / "PROCESS_POLICY.md").read_text(encoding="utf-8")
        cls.test_policy = (CORE / "TEST_POLICY.md").read_text(encoding="utf-8")

    def test_general_is_small_and_routes_to_authorities(self):
        self.assertLessEqual(len(self.general.encode("utf-8")), 10 * 1024)
        for target in (
            "ROUTING_POLICY.md", "PROCESS_POLICY.md", "TEST_POLICY.md",
            "ERROR_POLICY.md", "AUTHORITY_SEPARATION.md", "INTEGRITY_POLICY.md",
            "CONTEXT_CACHE_SPEC.md", "FOCUS_CACHE_SPEC.md",
        ):
            self.assertIn(target, self.general)
        for forbidden in (
            "IDTASK_", "codex exec", "Luna", "Antigravity",
            "MAX_REWORK_COUNT", "generation_base_sha", "guard_summary",
        ):
            self.assertNotIn(forbidden, self.general)

    def test_focus_cache_is_landmine_count_only(self):
        self.assertIn("work/focus_cache/LANDMINES.md", self.focus)
        self.assertIn("- 発生回数:", self.focus)
        self.assertIn("- 地雷:", self.focus)
        self.assertIn("- 原因:", self.focus)
        self.assertIn("- 正解パターン:", self.focus)
        self.assertIn("成功時はFocus Cacheを更新しない", self.focus)

    def test_complex_focus_mechanisms_are_disabled(self):
        for value in ("revision鎖", "reservation", "promotion", "transient", "handoff"):
            self.assertIn(value, self.focus)
        self.assertIn("新規作業では入力、更新、完了判定へ使用しない", self.focus)

    def test_normal_work_has_no_intermediate_human_approval(self):
        self.assertIn("上限内の修正", self.process)
        self.assertIn("自動進行できる", self.process)
        self.assertIn("人間承認が必要な例外", self.authority)
        self.assertIn("非常時rollback", self.authority)

    def test_tests_are_script_driven_and_agents_run_only_on_failure(self):
        self.assertIn("レビュー済みの差分だけをテスト", self.test_policy)
        self.assertIn("成功時は解析Providerを起動しない", self.test_policy)
        self.assertIn("成功時は解析担当やテスト担当エージェントを起動しない", self.authority)
        self.assertIn("失敗時だけ構造化ログを調査", self.authority)


if __name__ == "__main__":
    unittest.main()
