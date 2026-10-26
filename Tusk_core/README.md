<!-- md-scope-document: COMMON -->
# Tusk Core

Tusk Coreは、製品固有ルールを持たない軽量な実装・テスト・リカバリー安全基盤。製品機能は有効化した拡張から読み込む。AI向け契約は `AGENTS.md`、詳細な共通規則は `GENERAL.md` にある。

## Common commands

```powershell
# ワークスペース初期化 (tusk_manager の実体は Tusk_Basic_skills の Skill tusk-manager。常に有効)
python ..\extensions\Tusk_Basic_skills\skills\tusk-manager\scripts\tusk_manager.py --workspace D:\target init

# 作業中の変更リカバリー（開始 / 状態確認 / 中断 / 再開 / 改訂 / ロールバック / 完了）
python ..\extensions\Tusk_Basic_skills\skills\tusk-manager\scripts\tusk_manager.py --workspace D:\target session start --work-id work-01 --scope path\to\file.py
python ..\extensions\Tusk_Basic_skills\skills\tusk-manager\scripts\tusk_manager.py --workspace D:\target session status
python ..\extensions\Tusk_Basic_skills\skills\tusk-manager\scripts\tusk_manager.py --workspace D:\target session stop --reason "waiting user decision"
python ..\extensions\Tusk_Basic_skills\skills\tusk-manager\scripts\tusk_manager.py --workspace D:\target session resume
python ..\extensions\Tusk_Basic_skills\skills\tusk-manager\scripts\tusk_manager.py --workspace D:\target session revise
python ..\extensions\Tusk_Basic_skills\skills\tusk-manager\scripts\tusk_manager.py --workspace D:\target session rollback --to baseline
python ..\extensions\Tusk_Basic_skills\skills\tusk-manager\scripts\tusk_manager.py --workspace D:\target session complete

# 複数 session 同時運用: 未完了が2つ以上なら各操作に --work-id が必須。start は --owner を記録可、スコープ重なりは拒否
python ..\extensions\Tusk_Basic_skills\skills\tusk-manager\scripts\tusk_manager.py --workspace D:\target session complete --work-id work-01
python ..\extensions\Tusk_Basic_skills\skills\tusk-manager\scripts\tusk_manager.py --workspace D:\target session list --stale-hours 24
python ..\extensions\Tusk_Basic_skills\skills\tusk-manager\scripts\tusk_manager.py --workspace D:\target session abandon --work-id work-01 --reason "owner gone"

# 差分に対応する個別テスト
python tools\test_selector.py --root . --map TEST-MAP.json --stage focused --changed <path> --run

# 既知の失敗地雷を記録
python tools\landmine_cache.py --workspace D:\target record --error-key test.example --landmine "failure" --cause "cause" --correct-pattern "safe pattern" --target "component"
```

ログmarkerとコード一覧は `ERROR_POLICY.md`、`ERROR_CODES.md` を参照する。
