<!-- md-scope-document: COMMON -->
# Test policy

テスト範囲の人間向け正本。機械的な対応表は`TEST-MAP.json`、選択処理は
`tools/test_selector.py`を正本とする。入力は現在のGit差分と要求stageだけであり、
会話、推測、Work Packetから選択しない。

## Stages

- `focused`: 変更ファイルへ直接対応するテストだけを修正ループ内で実行する。
  未対応ファイルが1つでもあれば`component`へ安全側補正する。
- `component`: 変更したcomponentの全テストを、一連の変更完了後に実行する。
- `full`: workspace統合テストを実行する。統合、release、installer、distribution、
  migration、および共有契約を跨ぐ複数component変更の前に必須とする。

下位stageの成功は上位stageを代替しない。実行結果にはrequested/effective stage、
選択テスト、補正理由、未対応変更、終了コードを残す。非ゼロ終了時は後続stageを
停止する。

テスト本体へ到達する前の作業ディレクトリ、相対パス、import経路、起動形式だけの
不備は`preflight_error`とする。対象と安全範囲を変えない機械的な経路補正を1回だけ
行い、停止せず同じテストを続行できる。テスト本体の失敗、入力fixtureの不一致、
対象拡大が必要な補正はこれに含めず、通常の限定修正ループへ移す。

## Execution

```powershell
python tools/test_selector.py --root . --map TEST-MAP.json --stage focused --changed <path> --run
python tools/test_selector.py --root . --map TEST-MAP.json --stage component --run
python tools/test_selector.py --root . --map TEST-MAP.json --stage full --run
```
