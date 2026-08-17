# Tusk Core

**導入方法:ワークスペースの直下にすべて配置後、エージェントに読ませる**

TuskはAI支援開発の共通契約、自己監査、実行環境差し替え、拡張機能を分離する小型アーキテクチャ。

```text
Tusk_core/          共通契約・テスト・機械判定
Tusk_sharpener/     Integrity / Authenticity / Consistency監査
runtime_adapters/   Codex、Gemini、Claude等の実行環境差し替え口
extensions/         ドメイン固有能力
work/               ローカルactivationと生成状態（Git対象外）
```

## Quick check

```powershell
python -m unittest discover -s Tusk_core/tests -p "test_*.py"
python Tusk_sharpener/sharpener.py check --target Tusk_core --workspace .
```

製品コード、認証キー、実行Cache、archiveは同梱しない。Extensionは明示的に導入・有効化したものだけを読む。

