<!-- md-scope-document: COMMON -->
# Tusk Core Agent Contract

1. **プロファイル選択**: `START-HERE.md` に従い、自分のプロバイダ専用プロファイル（`profiles/GEMINI_PROFILE.md`、`CLAUDE_PROFILE.md`、`CODEX_PROFILE.md` のいずれか1本）だけを読む。
2. **スコープ保護と作業中リカバリー** (`tusk_manager.py` の実体は `extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py`。Tusk_Basic_skills は Core 必須の Extension で常に有効):
   - 編集前に `tusk_manager.py session start --work-id <id> --scope <paths...> [--owner <name>]` で対象ファイルを登録する。未完了 session とスコープが重なる場合は拒否される。
   - 未完了 session が複数あるときは `stop/resume/revise/rollback/complete/status` に `--work-id <id>` を付ける。放置 session は `session list [--stale-hours N]` で確認し `session abandon --work-id <id> --reason <reason>` で片付ける（ファイルは巻き戻さない）。
   - 仕様不足・承認待ち・エラー停止時は推測で進めず `tusk_manager.py session stop --reason <reason>` で作業中変更を保護して止まる。
   - 手戻り (`revise`) は最大3回 (`MAX_REWORK_COUNT = 3`) までとし、ロールバック時はスコープ内のファイルだけを復元してユーザーの無関係な変更を壊さない。
3. **キャッシュ活用**:
   - 大規模スコープは `tusk_manager.py context --scope <scope_key>` で変更差分を確認し、未変更ファイルの無駄な全文読込を避ける（`EXTENSION_POLICY.md` 参照）。
   - 既知の失敗パターンは `work/focus_cache/LANDMINES.md` を確認・記録する。
4. **完了条件**: 推測で成功を宣言せず、`TEST_POLICY.md` に基づくテストと成果物検証を通過した場合のみ `session complete` する。
