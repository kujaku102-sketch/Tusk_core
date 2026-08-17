<!-- md-scope-document: COMMON -->
# Tusk Core

Tusk Coreは、製品固有ルールを持たない実装・テスト安全基盤。製品機能は有効化した
拡張から読み込む。AI向け契約は`AGENTS.md`、詳細な共通規則は`GENERAL.md`にある。

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Common commands

```powershell
# 差分に対応する個別テスト
.\.venv\Scripts\python tools\test_selector.py --root . --map TEST-MAP.json --stage focused --changed <path> --run

# 既知の失敗地雷を記録
.\.venv\Scripts\python tools\landmine_cache.py --workspace D:\target record --error-key test.example --landmine "failure" --cause "cause" --correct-pattern "safe pattern" --target "component"

# 開発用integrity keyを初回登録
.\.venv\Scripts\python tools\integrity_gate.py --workspace D:\target trust
```

配布、更新、repairでは開発用integrity bypassを使用しない。ログmarkerとコード一覧は
`ERROR_POLICY.md`、`ERROR_CODES.md`を参照する。
