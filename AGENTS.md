# Tusk Workspace Entry

## Load order

1. `Tusk_core/START-HERE.md` と `Tusk_core/AGENTS.md` を読む。
2. **自分の実行モデルに対応するプロファイル1ファイルだけ**を読む（他社モデルのプロファイルは読まない）：
   - **Gemini**: `Tusk_core/profiles/GEMINI_PROFILE.md`
   - **Claude**: `Tusk_core/profiles/CLAUDE_PROFILE.md`
   - **Codex**: `Tusk_core/profiles/CODEX_PROFILE.md`
3. `work/settings/extensions.enabled.json` で有効化され、manifest検証を通った Extension の `AGENTS.md` だけを読む。
4. `work/context_cache/`（存在する場合）で対象スコープの差分を確認し、未変更ファイルの全文走査を省いて現行Specと `work/focus_cache/LANDMINES.md` を読む。

## Boundary

- `Tusk_core` に製品固有規則を入れない。製品固有のルール・Skillは各Extensionまたは現行Specに置く。
- 作業開始時は `python extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py --workspace . session start --work-id <id> --scope <paths...>` で変更対象スコープを登録し、中断・再開・ロールバックを安全に管理する。複数 session は `work/recovery/sessions/<work_id>.json` で並行管理され、スコープが重なる start は拒否される。2つ以上の未完了 session がある間は `stop/resume/revise/rollback/complete/status` に `--work-id <id>` が必須。
- archive、release、build、dist、vendor、`_internal`、tmp は明示要求がない限り読まない。
- 指定外ファイルやユーザーの無関係な変更を勝手に巻き戻さない。
