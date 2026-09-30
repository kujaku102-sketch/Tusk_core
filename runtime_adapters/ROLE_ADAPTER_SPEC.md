# Runtime Role Adapter

Runtime AdapterはCoreの論理ロールをProvider固有のモデル系列へ変換する。Authority、Process Level、Implementation Intensity、承認、テスト下限を変更しない。

## Profile config

Adapter内の`config.json`を設定正本とする。schema version 1、adapter_id、active_profile、profilesを持ち、profilesは名前からbinding JSONへのパスを定義する。CLIの`--config`は設定正本の所在、`--profile`はその呼出しの選択を上書きする。通常はactive_profileを使う。モデル環境変数は選択済みbindingのモデルだけを上書きする。

configとprofileはCore外の自由編集設定であり、追加・差し替え・モデル変更にCore変更承認を要求しない。binding schema、Adapter ID、論理ロール権限の検証は毎回行う。解決済みprofile名を出力し、Coreオーケストレーションはその結果をactor割当へ渡す。実行中のactor bindingは既存run契約に従って固定し、設定変更は次のsetupから適用する。

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
