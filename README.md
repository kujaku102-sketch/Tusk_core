# Tusk Core (Lightweight Edition)

**導入方法: ワークスペースの直下に配置し、エージェントに `AGENTS.md` を読ませる**

`Tusk_core_rb` は、不要な形式承認儀式や重複ランタイムを削ぎ落とし、**「作業中の変更リカバリー (`session`)」「地雷キャッシュ (`landmine_cache`)」「差分テスト選択 (`test_selector`)」「長時間実行監視 (`test_guard_monitor`)」** の4本柱に絞った軽量・実用特化型コアアーキテクチャ。

```text
Tusk_core/          共通契約・ツール・テスト
extensions/         ドメイン固有能力
work/               ローカル設定・地雷キャッシュ・作業中セッションリカバリー（Git対象外）
```

## Quick check

```powershell
Push-Location Tusk_core
python tools/test_selector.py --root . --map TEST-MAP.json --stage full --run
Pop-Location
```

## 作業中の変更リカバリー (Session Recovery)

タスク中断・仕様変更・手戻り時に、ユーザーの無関係な変更を壊さずに対象スコープだけを安全に保護・復元する。

```powershell
# 1. 作業開始（対象スコープのベースラインSHAとバックアップを記録）
python extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py --workspace . session start --work-id task-01 --scope src/app.py

# 2. 中断・待機（現在の作業中変更をWIPスナップショットとして保存し waiting_human へ遷移）
python extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py --workspace . session stop --reason "仕様確認待ち"

# 3. 再開（停止中のファイル改変がないかSHA検証して running へ復帰）
python extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py --workspace . session resume

# 4. 仕様変更・手戻り（WIPを維持したまま世代と rework_count を進める。上限3回）
python extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py --workspace . session revise --scope src/extra.py

# 5. ロールバック（スコープ内の変更だけをベースラインまたは現世代開始時へ戻す）
python extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py --workspace . session rollback --to baseline

# 6. 完了
python extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py --workspace . session complete

# 複数 session を同時に扱うとき: 未完了が2つ以上なら stop/resume/revise/rollback/complete/status に --work-id が必須
python extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py --workspace . session complete --work-id task-01

# 放置 session の確認と片付け（abandon は状態のみ変更。ファイル・スナップショットは触らない）
python extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py --workspace . session list --stale-hours 24
python extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py --workspace . session abandon --work-id task-01 --reason "owner gone"
```

## License

Apache License 2.0。詳細は `LICENSE` を参照。
