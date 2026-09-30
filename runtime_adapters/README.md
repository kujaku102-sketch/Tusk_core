# Runtime Adapters

モデル名やIDE/CLI固有操作をCoreから分離する。Adapterは論理ロールと実行環境のbindingだけを所有し、Core policyやExtension仕様を再定義しない。

同梱Adapter:

- `codex`: 現行Luna / Sol / Astra割当を論理ロールへ変換する。
- `claude`: Tusk独自aliasのFable（開発指揮・最上位レビュー）/ Opus（実装）/ Sonnet（低推論）を論理ロールへ変換する。

これらは互換対象を示す識別名であり、OpenAI、Anthropicその他のモデル提供者による提携、認定、推奨を示さない。

```powershell
python role_adapter.py validate
python role_adapter.py resolve --adapter codex --role implementation --intensity HIGH
python role_adapter.py resolve --adapter claude --role review --intensity MAX
```

出力はbinding情報だけで、Provider起動や権限変更は行わない。`model_env`で指定された環境変数があれば既定aliasを置換する。

各Adapterの`config.json`が`active_profile`と`profiles`（名前からbinding JSONへのパス）を定義する。相対パスはconfigの所在を基準に解決する。既定プロファイルは現行`adapter.json`を使う。新しいbinding JSONを用意し、`profiles`へ登録して`active_profile`を変更すれば切り替わる。

```powershell
python role_adapter.py resolve --adapter codex --profile default --role implementation --intensity HIGH
python role_adapter.py resolve --adapter codex --config C:/settings/codex/config.json --role skim
```

config編集、モデル割当変更、プロファイル追加・差し替えはRuntime Adapter設定の変更として自由に行える。Core規則変更、Core変更承認、Core manifest再生成の対象にはしない。適用時はschemaとロール権限を検証し、失敗した場合は別プロファイルへ黙って切り替えない。設定変更でMAX承認やProcess Level、変更可能範囲を解除できない。

Codexの現行profileは`Tusk_agents6.1`。実装はLOW=`6Luna/high`、MID=`6Luna/max`、HIGH=`6.1Sol/high`、MAX=`6Astra/high`。流し見は`6Luna/medium`、本レビューは全強度で`6.1Sol/medium`、設計は`6.1Sol/high`、MAX設計は`6Astra/medium`。指揮は会話のモデルと推論強度を継承する。失敗解析と引継ぎは従来割当を維持する。

```powershell
python role_adapter.py resolve --adapter codex --role design --intensity MAX
python role_adapter.py resolve --adapter codex --role lead
```

Core監視ツールから失敗解析を通知する場合は、`failure_analysis`を解決した`model`を`--codex-model`で渡す。未指定時は`TUSK_CODEX_ANALYSIS_MODEL`を参照し、どちらもない場合は通知を開始しない。
