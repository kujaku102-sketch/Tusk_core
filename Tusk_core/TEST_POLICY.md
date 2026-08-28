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

### Selector root and changed-path contract

`tools/test_selector.py`の`--root`はworkspace rootではなく、`TEST-MAP.json`と`tests/`を直下に持つcomponent rootである。Tusk Coreでは`Tusk_core`の絶対パスを渡す。`--changed`はそのcomponent root相対のPOSIXパスだけを受け取り、workspace相対のcanonical snapshot pathと同じ値を渡さない。

workspace相対値をselector入力へ変換するcallerは、大文字・小文字を変えずexact prefix `Tusk_core/`を最大1回だけ除去する。除去後にも同じprefixが残る値、空、`.`、絶対パス、backslash、`..`、非canonical POSIX形式を拒否する。prefixがない値はすでにcomponent-relativeとして同じ安全検証だけを行う。snapshot用のworkspace-relative配列とselector用のcomponent-relative配列は別変数、別検証とし、一方を他方のidentityやlookup keyに再利用しない。

Extensionまたは現行Specが入力規模、実機、ビルド後、配布前などの製品固有tierを
定義する場合、そのtierはCore stageへ追加適用する。Core stageと製品固有tierは
互いに代替せず、両方の要求を満たした場合だけ必要なテスト範囲を完了扱いにする。

テスト本体へ到達する前の作業ディレクトリ、相対パス、import経路、起動形式だけの
不備は`preflight_error`とする。対象と安全範囲を変えない機械的な経路補正を1回だけ
行い、停止せず同じテストを続行できる。テスト本体の失敗、入力fixtureの不一致、
対象拡大が必要な補正はこれに含めず、通常の限定修正ループへ移す。

訂正前後のコマンドとエラーを保存し、変更できるのはコマンド文字列だけとする。製品ソース、テストコード、fixture、期待値、環境設定、依存物を変更しない。ファイル不存在、正本不明、workspace外参照、権限エラー、reparse point、対象identity不一致、または製品・テストコードが一行でも実行された可能性がある場合は`preflight_error`へ分類しない。限定訂正後も起動不能なら`waiting_human`へ停止する。

## Orchestration entry gate

テスト開始には、指定`work_id`・`attempt_id`の現行generationに属するimplementation result identity record Rについて、次の証拠をすべて必須とする。identityのschema、計算、lookup、invalidationは`PROCESS_POLICY.md`だけを参照する。

- sequence 0のaccepted approval genesis、attempt、現行generationのbaseline B、actor binding set、stage外`orchestration_setup`が同じwork・attempt・approval scopeを固定し、`pre_skim`が同じsetup referenceをconsumeしている。
- implementation resultの`result_identity_record_ref`がRを参照する。
- accepted index上のlatest-valid post-skimがRを参照し、そのper-run ID・UTC・run ID・supersedesが有効である。rejected envelopeとinvalid candidateはlatest-validを進めない。
- final reviewがその最新post-skim handoffとRを参照し、`verdict: accept`である。
- design receiptの`reviewed_identity_record_ref`がRを参照し、`disposition: accept`である。
- 各result handoffの`unresolved`にblockerがない。
- テスト起動直前にRの`snapshot_payload.scope_paths`の現在raw bytes・byte count・stateから`PROCESS_POLICY.md`のcanonical手順でsnapshotを再計算し、Rの`snapshot_sha256`と一致する。
- events raw SHA、最後のcontiguous sequence、R ID、R full snapshot、latest-valid post-skim、terminalを固定したvalidator v3のfull validation receiptとSHAがtest contractとexactに一致する。

すなわち、テスト開始時はcurrent canonical snapshot、implementation result、post-skim、final review、design receiptがすべて同じR recordを解決しなければならない。pre-edit baseline BとRの値一致は要求せず、Bはentry gateの同一性predicateに使わない。design receipt後にRが持つscopeのraw bytes、byte count、state、またはscope自体が変更された場合はgateを即時閉じ、新しいR recordに対するpost-skim、final review、design receiptが揃うまでテストを起動しない。

一つでも欠落、actor binding衝突、work・attempt・generation・approval・result identity・receiptの不一致、stale post-skim、terminal reentry、未解決blockerがある場合はテストを開始せず`needs_review`とする。design receiptのaccept前にpreflight、guard、selector `--run`、製品テストを起動しない。このentry gateは既存のstage選択、製品固有tier、guard、evidence要件を緩和または置換しない。

### Read-only orchestration evidence validator

`tools/orchestration_evidence_validator.py`はtrusted envelope streamを検証するstdlib-onlyの読み取り専用CLI version 3である。`--workspace-root`、`--work-id`、`--attempt-id`、`--target <pre_skim | design | commander_window | implementation | post_skim | final_review | design_receipt | test_gate>`を必須とし、input pathは`work/orchestration_evidence/<sha256(work_id)>/events.jsonl`からだけ導出する。attempt選択とcheckpoint選択を混同しない。file、evidence、Cache、state、manifestを作成・編集・削除しない。

CLIはenvelope version、contiguous sequence、prior-envelope SHA、record payload SHA、approval ref、producer/recorder ID、UTC、accepted/rejectedを検証する。cross-record lookupはaccepted indexだけを使い、rejected recordをindexへ入れずfindingへ残す。同一ID・同一canonical JSONのreplayは1 recordへcollapseし、同一IDのconflictは拒否する。legacy raw recordと暗黙migrationを拒否する。invalid post-skimがlatest-validを進めないため、後続valid runは直前latest-validを正しくsupersedeして回復できる。

出力top-levelは`schema_version`、`validator`、`work`、`attempt`、`generation`、`target`、`valid`、`state`、`evidence_sequence`、`evidence_log_sha256`、`current_snapshot_sha256`、`selected_refs`、`findings`、`validation_receipt`、`validation_receipt_sha256`を持つ。指定checkpointまでの累積prefixが有効な場合だけ終了0と`valid: true`を返す。`pre_skim`から`implementation`はlive B、`post_skim`から`test_gate`はlive Rを照合する。読み取り可能な不足・意味不一致は終了2・`state: needs_review`、workspace外、reparse、partial、存在しない・通常fileでない・UTF-8/JSONLとして読めないinputは終了3・`state: waiting_human`とする。

### Receipt to product execution order

順序は`receipt → validator → guard → selector --run / product`で固定する。開発指揮がtest contractへexpected full receiptとSHAを固定し、guardは製品process registry読込、lock取得、process照会、selector `--run`または製品起動より前にvalidator v3をwork・attempt・`test_gate`指定で再実行する。outer contract、embedded receipt、actual receiptのwork・attempt・target、exact field set、canonical bytes、各SHAが三者一致した後だけguardを開始する。順序変更、validator結果のcache再利用、receipt hashだけの照合を許可しない。

`test_gate`はstate transition chainが非空かつ線形で、latest recordが現行attempt・現行generationに属し、`to_state: running`の場合だけ開く。欠落、非running、branch、cycle、predecessor欠落、generation後退はgateを閉じる。

## Guard and evidence

- レビュー済みの差分だけをテストし、テスト中は製品コード、テストコード、fixture、期待値を変更しない。
- test contractの`orchestration_gate`は必須booleanとする。既存runはexplicit `false`でだけ互換継続できる。`true`では`orchestration_evidence` objectを`workspace_root`、`work_id`、`attempt_id`、`target: test_gate`、full `validation_receipt`、`validation_receipt_sha256`のexact六fieldとし、guardがvalidatorをattempt・target指定で再実行する。embedded receiptとvalidator receiptのcanonical bytes、両SHAを完全一致させ、partial、hash-only、R-ID-only、extra field、mutationを拒否する。
- 実行ごとに一意な`run_id`と専用ログ先を使い、コマンド、開始・終了時刻、終了コード、入力、成果物を一時保存する。
- guardを要求するSpecでは、監視状態と対象プロセスidentityを確認してから製品テストを開始する。監視起動に失敗した場合は製品テストを開始しない。
- 子プロセスは監視へ渡せる登録済みroot processの子として起動し、PID、実行ファイル、コマンドidentityを記録する。停止時は個別列挙とidentity再確認を行い、末端から停止する。
- プロセス停止は、現行Specへ登録され停止直前にidentityを再確認できた対象だけに限定する。登録外プロセス、identity不一致、広範なプロセスツリー停止は行わない。製品固有の親子関係と停止順序はExtensionまたは現行Specを正本とする。
- 非ゼロ終了、強制停止、監視異常を検出した時点で後続stageを停止する。自動再起動、無制限再試行、成功条件の緩和を行わない。
- 成功は終了コードだけで決めず、Specの成功条件、件数、ID集合、成果物、必要なSHA、最終レビューを検証する。停止と成功通知が競合した場合は停止を優先する。
- 成功時は生ログ全文を恒久保存せず、`run_id`、Spec、終了コード、成功件数、要求されたID集合照合、成果物identity、開始・終了時刻、最終判定を`success_summary.json`へ残す。既存ログは削除しない。
- 失敗時は構造化されたエラー抜粋、発生理由、発生箇所、失敗工程、直接根拠、回避規則、適用した限定修正、変更前後の対象identity、検証結果、Focus Cache参照を保持し、`PROCESS_POLICY.md`の再作業規則へ渡す。
- 成功時は解析Providerを起動しない。失敗解析は読み取り専用とし、その結果だけで修正や完了を決定しない。
- 軽度問題が残る場合は、現行Specの許容範囲内であることを開発指揮が確認するまで完了にしない。
- 終了通知は全成功条件と成果物検証の後だけ生成する。未解決の強制停止と終了通知が同時に存在する場合は強制停止を優先する。`guard_summary.json`の`completed`だけで製品または作業の完了を決めない。

個別処理のハードタイムアウトは既定で追加しない。実害と停止根拠を確認した処理だけExtensionまたは現行Specで追加する。全体停滞時間、軽度問題の件数・比率、人間停止、解析通知の具体値は製品固有契約へ置く。

製品固有マーカー、軽度問題の件数・比率、外部アプリ停止方法、成果物固有の検証はExtensionまたは現行Specを正本とし、Coreで固定しない。

## Execution

```powershell
python tools/test_selector.py --root . --map TEST-MAP.json --stage focused --changed <path> --run
python tools/test_selector.py --root . --map TEST-MAP.json --stage component --run
python tools/test_selector.py --root . --map TEST-MAP.json --stage full --run
```
