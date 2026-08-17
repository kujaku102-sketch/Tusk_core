# Tusk-flash Grammar

## Routes

- `DIRECT`: 単一責務かつ保護対象を含まない小変更。
- `SPLIT`: 独立した責務へ最大3分割できる変更。
- `STOP`: 認証、秘密情報、破壊操作、migration、仕様矛盾、編集範囲競合、同一失敗2回。

## Task Slice

各Sliceは目的、読取範囲、排他的な書込範囲、入出力契約、依存、受入テスト、禁止変更を持つ。子は範囲追加を行わず、必要性を結果へ記録する。

## Agent Result

結果は`success`、`failed`、`needs_review`のいずれか。変更ファイル、実行テスト、短い要約、問題を構造化して返す。思考履歴や全文ログを含めない。

## Monitor Events

イベントは`PROGRESS`、`MINOR`、`FAIL`、`DONE`だけを使用する。`FAIL`後は後続を止める。コード・契約不良だけを修正回数へ算入し、起動経路補正は1回だけ許可する。
