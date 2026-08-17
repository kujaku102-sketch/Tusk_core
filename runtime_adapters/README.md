# Runtime Adapters

モデル名やIDE/CLI固有操作をCoreから分離する。Adapterは論理ロールと実行環境のbindingだけを所有し、Core policyやExtension仕様を再定義しない。

同梱Adapter:

- `codex`: 現行Luna / Terra / Sol割当を論理ロールへ変換する。
- `claude`: Tusk独自aliasのFable（開発指揮・最上位レビュー）/ Opus（実装）/ Sonnet（低推論）を論理ロールへ変換する。

これらは互換対象を示す識別名であり、OpenAI、Anthropicその他のモデル提供者による提携、認定、推奨を示さない。

```powershell
python role_adapter.py validate
python role_adapter.py resolve --adapter codex --role implementation --intensity HIGH
python role_adapter.py resolve --adapter claude --role review --intensity MAX
```

出力はbinding情報だけで、Provider起動や権限変更は行わない。`model_env`で指定された環境変数があれば既定aliasを置換する。
