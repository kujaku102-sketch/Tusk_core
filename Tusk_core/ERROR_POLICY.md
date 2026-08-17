<!-- md-scope-document: COMMON -->
# Error policy

エラーコードの人間向け正本。機械が読む具体的なコード一覧と互換表は
`ERROR_CODES.md`を正本とする。

## Code space

- `F000-F199`: Core共通の強制停止。後続処理を停止する。
- `M000-M199`: Core共通の軽度問題。証拠を保存して処理を継続する。
- `F200-F299`: プログラム依存の強制停止。
- `M200-M299`: プログラム依存の軽度問題。
- `F000`と`M000`は分類不能・未確定用とする。
- 完全なコードは接頭辞を含む4文字 (`Fxxx`, `Mxxx`) とする。

共通番号帯は、`001-019`環境・設定、`020-039`プロセス・停止、
`040-059`ファイル・パス、`060-079`データ、`080-099`外部通信、
`100-179`拡張領域、`180-189`ユーザー操作、`190-199`将来拡張とする。

プログラム依存コードは各プログラムのレジストリで`program_id`、意味キー、
F/M区分、停止・継続動作を定義する。未バインド番号を推測せず、`F000`または
`M000`で記録する。既存の共通番号帯にある互換コードは個別Specなしに改番しない。

## Marker grammar

```text
[TUSK_FORCE_STOP] code=Fxxx program_id=<PROGRAM_ID> run_id=<RUN_ID> component=<COMPONENT> step=<STEP> reason=<REASON>
[TUSK_MINOR_ISSUE] code=Mxxx program_id=<PROGRAM_ID> run_id=<RUN_ID> component=<COMPONENT> step=<STEP> target=<TARGET> detail=<DETAIL>
[TUSK_PROGRESS] run_id=<RUN_ID> component=<COMPONENT> step=<STEP> current=<CURRENT> total=<TOTAL|unknown>
```

ログは1行で出力し、直後にflushする。`IDTASK_*` markerは入力互換だけに使用し、
新規Core出力へ使用しない。拡張固有コードは有効化された拡張自身の
`ERROR_CODES.md`を参照する。

軽度問題が設定された件数または比率の閾値へ達した場合は、レジストリの対応する
Fコードへ昇格して停止する。`F182`は監視コンソールが生成する人間停止専用であり、
通常ログから偽装しない。
