# Runtime Role Adapter

Runtime AdapterはCoreの論理ロールをProvider固有のモデル系列へ変換する。Authority、Process Level、Implementation Intensity、承認、テスト下限を変更しない。

## Logical roles

- `lead`
- `skim`
- `failure_analysis`
- `handoff`
- `implementation` + `LOW|MID|HIGH|MAX`
- `review` + `LOW|MID|HIGH|MAX`

`skim`と`failure_analysis`は常に`read_only`。`handoff`は`transform_only`。実装だけ`write_limited`を許可する。Adapter解決失敗は推測せず非ゼロ終了とする。

## Claude binding

- `Fable`: 開発指揮、最上位レビュー
- `Opus`: 実装
- `Sonnet`: 流し見、失敗ログ解析、引き継ぎ要約

モデル名はaliasであり、実環境の識別子は対応する環境変数で差し替える。
