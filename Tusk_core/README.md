# Tusk Core

Tusk Coreは、製品固有ルールを持たない実装・テスト安全基盤。製品機能は呼出側が選択した
拡張から読み込む。AI向け契約は`AGENTS.md`、詳細な共通規則は`GENERAL.md`にある。

## Setup

Python 3.12と`requirements.txt`の実行時依存を用意する。

```powershell
python -m pip install -r requirements.txt
```

## Common commands

```powershell
# 記録の状態を読む
python -B -m runtime.cli status --state C:\workspace\evidence
```

ログmarkerとコード一覧は`ERROR_POLICY.md`、`ERROR_CODES.md`を参照する。
