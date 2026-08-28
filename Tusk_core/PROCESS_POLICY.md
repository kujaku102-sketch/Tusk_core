# Process Policy

Process Policyは変更の危険度、必須安全工程、テスト下限、実行経路を決める正本である。技術的難度とProviderを決めるImplementation Intensityとは独立する。一方から他方を推定・変更しない。複数条件では常に最も高い下限と最も厳しい要件を採用し、作業中の範囲拡大時は再判定する。

## Work lifecycle

作業状態は`running`、`needs_review`、`waiting_human`、`needs_human_review`、`completed`、`abandoned`の6種類とし、`current_state`は常に1つだけ保持する。同一イベントで複数条件が成立した場合は`abandoned > needs_human_review > waiting_human > needs_review > running > completed`の順で選ぶ。

- `needs_review`: 技術情報または読み取り専用レビュー根拠が不足している。製品編集、実行テスト、ビルドは禁止する。
- `waiting_human`: 人間の操作、判断、再開指示を待つ。編集、テスト、再実行、ビルド、追加担当の起動を禁止する。
- `needs_human_review`: 再作業上限、承認範囲超過、MAX後の追加修正など、人間の再判定が必要である。
- `completed`: 個別Specの成功条件、必須テスト、成果物検証、最終レビューを全て満たしている。
- `abandoned`: 未完了のまま終了し、差分と失敗証拠を引き継げる状態である。

`STOP`は状態ではなく後続を止める制御シグナルである。承認不足、非ゼロ終了、編集不能、人間操作待ちは`waiting_human`、上限到達・危険領域への拡大・MAX後の追加修正は`needs_human_review`、技術情報不足は`needs_review`、人間が終了を指示した場合は`abandoned`へ変換する。分類不能なSTOPは推測せず`waiting_human`とする。停止状態は自動処理、実装担当、レビュー担当、監視ツールが独自に解除しない。

状態変更は`work_id`、変更前後の状態、理由、UTC時刻、対象Spec、現在差分を追記専用で保存する。通常開発の状態遷移や再開判定にSHA認証を要求しない。Protected Surfaceで必要な変更前SHAは本Policy、配布時SHAは`INTEGRITY_POLICY.md`に従う。

状態変更のactual recordは次のschemaを持ち、`state_transition_id`は`(work_id, attempt_id)`全体で一意にlookupする。generationを跨いでも最初のrecordだけ`previous_state_transition_ref`と`from_state`を`null`にし、以降は直前にacceptedされたattempt-global recordのIDと`to_state`をそれぞれ参照・継承する。自己参照、ID再利用、最新record以外の参照、将来参照、欠落、分岐、cycle、append順またはUTC時刻の後退を許可しない。

```yaml
schema_version: 3
record_type: state_transition
work_id: <stable work id>
attempt_id: <stable attempt id>
generation: <non-negative integer>
state_transition_id: <unique state transition id>
previous_state_transition_ref: <prior state transition id or null>
from_state: <prior current_state or null>
to_state: <one current_state value>
reason: <machine-readable reason>
spec: <current spec path or identity>
identity_record_ref: <current canonical identity record id or null>
created_at_utc: <UTC timestamp>
```

`needs_review`中に許可するのは、指定された読み取り専用レビュー担当によるSpec、差分、ログ、証拠の確認だけである。レビュー担当は状態を直接解除せず、確認範囲、根拠、判定、未解決事項を開発指揮へ返す。開発指揮が現行Specと照合し、情報が充足すれば`running`、人間判断が必要なら`waiting_human`、上限または承認範囲超過なら`needs_human_review`へ移す。`completed`後に未解決エラー、未検証条件、承認外差分を検出した場合は完成判定を取り消す。

指定レビューProviderが利用できない場合は接続を反復せず、開発指揮自身の読み取り専用レビューへ一度だけ切り替えられる。開発指揮も根拠を確定できなければ`waiting_human`へ移す。

## Orchestration phase

`orchestration_phase`は`current_state`と独立した工程位置であり、既存の6種の作業状態、優先順位、停止・再開の意味を変更しない。値はunordered enum `{commander_window, design, design_receipt, final_review, implementation, post_skim, pre_skim}`に限定する。順序、6連続edge、stage-role対応は`AUTHORITY_SEPARATION.md`だけを正本とし、このPolicyへ再掲しない。

### Stage-external setup, generation, and recovery

`orchestration_setup`は`orchestration_phase`に含めないstage外preconditionである。attemptとgeneration、recovery input、baseline promotion、evidence admissionの意味は本節だけを正本とする。最初のaccepted envelopeはsequence 0のapproval genesisでなければならない。Coreは特定のIntensity、Process Level、counter、one-shot、root-remediation、revision/retry禁止を固定しない。

```yaml
schema_version: 3
record_type: approval
work_id: <approved stable work id>
attempt_id: <approved stable attempt id>
approval_id: <exact approval reference>
implementation_intensity: <approved LOW | MID | HIGH | MAX>
process_level: <approved P0 | P1 | P2 | P3 | P4>
protected_surfaces: [<sorted exact approved surfaces>]
scope_paths: [<sorted exact approved workspace-relative paths>]
commander_actor_id: <commander recorder actor id>
spec: <current workspace-relative spec path>
created_at_utc: <UTC timestamp>
```

```yaml
schema_version: 3
record_type: attempt
work_id: <same approved work id>
attempt_id: <same approved attempt id>
approval_ref: <genesis approval id>
created_at_utc: <UTC timestamp>
```

setup recordはschema v3で`work_id`、`attempt_id`、`generation`、`orchestration_setup_id`、`approval_ref`、`previous_setup_ref`、`recovery_input_ref`、`baseline_promotion_ref`、`baseline_identity_record_ref`、`actor_bindings_id`、`created_at_utc`だけを持つ。generation 0ではprevious/recovery/promotionをすべて`null`にし、Bのproducerを`orchestration_setup`、predecessorを`null`とする。generation N>0では三refを必須にし、N-1 setup、同generation recovery input、同generation baseline promotionへexactに解決する。

recovery inputは`recovery_input_id`、`source_generation`、`source_result_ref`、`recovery_kind: rework | resume | revise`、`failure_evidence_refs`、`recovery_bundle_ref`を持ち、`generation == source_generation + 1`とする。baseline promotionはrecovery input、直前generationのR、現行generationの新Bを参照する。新Bのfull canonical snapshot payloadとSHAは直前Rと完全一致し、predecessorはそのR、producerは`baseline_promotion`とする。要約、未解決external reference、hashだけをsnapshotの代用にしない。

#### Trusted evidence admission and freshness

`tools/orchestration_evidence_log.py`が唯一のmachine recorderである。開発指揮が明示したapprovalを推測、補完、拡張せず、`init`でapproval genesisを作り、`append`でrecordを提出する。保存先は`work/orchestration_evidence/<sha256(UTF-8 work_id)>/events.jsonl`だけとし、work IDを生directory名へ使わない。各workはaccepted/rejectedを同じ1 fileへsequence順で保存する。

```yaml
schema_version: 3
envelope_type: orchestration_evidence
status: accepted | rejected
sequence: <0-based contiguous integer>
work_id: <approved work id>
attempt_id: <approved attempt id>
record_type: <record type or null>
record_id: <record id or null>
record_sha256: <canonical record payload SHA-256>
record: <submitted record>
producer_actor_id: <record producer actor id>
recorder_actor_id: <approved commander actor id>
created_at_utc: <recorder UTC>
previous_envelope_sha256: <prior canonical envelope SHA-256 or null at sequence 0>
findings: [<rejection finding or none>]
```

recorderはexclusive lock取得後にevents全体を再読込し、sequence、prior hash、writer ID、scopeを再照合する。semantic admissionはvalidatorの`validate_submission`だけを呼び、writer独自のapproval/record predicateを持たない。1 envelopeを1 JSON lineとしてsingle appendし、flushと`fsync`後に再読込する。lock競合を待機retryしない。partial line、末尾LF欠落、UTF-8/JSON破損、lockまたはlogのidentity変化はfail closedとし、自動truncate、repair、migrationをしない。

accepted recordだけをcross-record indexへ入れ、rejected envelopeはrecordをindexへ入れずfindingとして保持する。generation recordは`(record_type, work_id, attempt_id, generation, record_id)`、approval/attemptは`(record_type, work_id, attempt_id, record_id)`でlookupする。同一composite ID・同一canonical recordは既存accepted recordへcollapseしてsequenceを消費せず、同一ID・異payloadはrejected envelopeとする。schema v1 raw、schema v2、future version、mixed streamを明示的に拒否し、暗黙migrationしない。

semantic admissionでは各generationの`orchestration_setup`、各stageのactor binding、`implementation_result`、post-skim以外の各handoff edge、terminal design receiptをsingletonとする。post-skim candidateだけは対応するpost-skim transitionがacceptedされるまで複数runを許し、そのtransition後のcandidateを拒否する。state transition IDはattempt-global singletonである。

post-skim recordは各runで新しいhandoff ID、run ID、UTCを持ち、直前のlatest-valid post-skimだけをsupersedeする。handoff shape、binding/producer、scope、unresolved、current result/R/design参照、run ID、UTC、supersedesの候補local findingsが一件でもblockingならlatest-validへ採用しない。そのinvalid findingはstream全体ではnonblockingとし、後続のvalid runが直前latest-validをsupersedeすれば回復できる。rejected envelopeもlatest-validを進めない。final review、design receipt、validation receiptは最新のvalid post-skimだけをconsumeする。result R、current snapshot、accepted sequence、events raw SHAのいずれかが変われば既存receiptはstaleである。

validator v3はfileを変更せず、指定attemptとcheckpointに対して次のdeterministic validation receiptとそのcanonical payload SHA-256を返す。UTCをreceiptへ入れてhashを実行ごとに変化させない。より高いgenerationのrecoveryが開始した後は旧generationのreceiptへfallbackしない。

```yaml
schema_version: 3
receipt_type: orchestration_validation
validator: orchestration_evidence_validator_v3
work_id: <validated work id>
attempt_id: <validated attempt id>
generation: <current generation>
target: <requested checkpoint>
evidence_log_path: <hashed workspace-relative events.jsonl path>
evidence_log_sha256: <raw events.jsonl SHA-256>
evidence_sequence: <last contiguous envelope sequence>
snapshot_identity_record_id: <checkpoint-selected B or R id>
snapshot_payload: <full canonical path snapshot payload>
snapshot_sha256: <canonical snapshot SHA-256>
recovery_bundle_ref: <current recovery bundle or null>
selected_refs: <deterministic selected record references>
```

canonical JSON、payload SHA、hashed work path、workspace相対path、nearest existing ancestorの`lstat`、symlink/reparse/junction拒否、root containment、TOCTOU再照合は`tools/orchestration_evidence_common.py`をvalidator、recorder、guardが共有する。安全性を証明できない入力は推測せず停止する。

すべてのphase transitionはappend-onlyで保存し、最低限次のfieldを持つ。

```yaml
schema_version: 3
record_type: transition
work_id: <stable work id>
attempt_id: <stable attempt id>
generation: <non-negative integer>
transition_id: <unique transition id>
previous_transition_ref: <prior transition id or null for the first edge>
source: <one orchestration_phase value>
target: <Authority-permitted next orchestration_phase value>
actor_bindings_id: <validated binding set id>
source_binding_id: <source stage binding id>
target_binding_id: <target stage binding id>
identity_record_ref: <validated baseline or result identity record id>
handoff_id: <validated handoff id>
created_at_utc: <UTC timestamp>
```

各transitionはappend-onlyであり、`transition_id`を作業・attempt・generation内で一意にする。`previous_transition_ref`は直前の同一work・attempt・generationのaccepted authority transitionまたは最初のedgeの`null`だけを参照し、自己参照、将来record、欠落record、異なwork・attempt・generation、分岐、cycleを禁止する。各generationは`handoff_i < transition_i < handoff_(i+1)`をsequenceで厳密に交互化し、terminal design receiptも最終transitionより後に置く。各隣接recordのUTCは後退させない。previous recordの`target`は現在recordの`source`と一致する。

直前のhandoff欠落、`source`・`target`がAuthorityのedgeに不一致、bindingのcomposite lookup失敗、対象work・generation・`identity_record_ref`の不一致、causal reference違反、`unresolved`にblockerが残る場合は`current_state: needs_review`とし、phase transitionと製品編集・実行テストを開始しない。`design_receipt`のterminal recordはphase transitionではなく、その後のstage reentryを禁止する。

### Canonical path snapshot identity

identityの計算、schema、lookup、invalidation、epoch、result bridge、legacy provenanceはこの節だけを正本とする。canonical algorithmは`sha256-path-snapshot-v1`であり、snapshot payloadのtop-level keyは`algorithm`、`path_snapshot`、`scope_paths`の3つだけとする。

```yaml
algorithm: sha256-path-snapshot-v1
path_snapshot:
  - path: <normalized workspace-relative POSIX path>
    sha256: <lowercase 64hex SHA256 of raw file bytes>
    size: <raw byte count>
    state: file
scope_paths:
  - <same normalized paths in the same order>
```

`scope_paths`と`path_snapshot`は同じpath集合をPOSIX形式のordinal順で持つ。file entryのkeyは`path`、`sha256`、`size`、`state`だけであり、`state`は`file`とする。absent entryは`path`と`state: absent`だけを持つ。fileの`sha256`はraw bytesから計算し、`size`は同じraw bytesのbyte countとする。

payloadはUTF-8、`ensure_ascii=false`、keyのordinal sort、separator `,` / `:`、whitespaceなし、末尾LFなしのcanonical JSONへserializeする。そのcanonical bytesのSHA256 lowercase 64hexがsnapshot identityである。liveまたはpost-edit snapshotは各payloadから再計算し、任意の正しいlowercase 64hexを受け入れる。特定fixture値との一致をlive判定に使わない。

identity recordは次のfieldを必須とし、`(work_id, attempt_id, generation, identity_record_id)`でlookupする。

```yaml
schema_version: 3
record_type: identity
work_id: <stable work id>
attempt_id: <stable attempt id>
generation: <non-negative integer>
identity_record_id: <unique record id>
epoch: baseline | result
snapshot_payload: <canonical sha256-path-snapshot-v1 object>
snapshot_sha256: <recomputed lowercase 64hex identity>
producer: orchestration_setup | baseline_promotion | implementation
predecessor_identity_record_ref: <baseline record id or null>
created_at_utc: <UTC timestamp>
```

lookup時はrecordの`work_id`・`attempt_id`・`generation`・`identity_record_id`と、`snapshot_payload`から再計算した`lowercase 64hex`を照合する。generation 0 baselineの`producer`はstage外の`orchestration_setup`、昇格baselineは`baseline_promotion`、resultは`implementation`とし、setupをorchestration stageに追加しない。scope path、state、raw byte SHA256、byte count、順序、canonical serializationのいずれかが変化したら既存recordを現在差分に対してinvalidateする。

baseline利用stage集合は`{commander_window, design, pre_skim}`、result利用stage集合は`{design_receipt, final_review, post_skim}`とする。`implementation`だけが次のresult bridge recordをappendし、baseline Bとresult Rを結ぶ。

```yaml
schema_version: 3
record_type: implementation_result
work_id: <stable work id>
attempt_id: <stable attempt id>
generation: <non-negative integer>
implementation_result_id: <unique result id>
baseline_identity_record_ref: <validated baseline identity record id>
result_identity_record_ref: <validated result identity record id>
created_at_utc: <UTC timestamp>
```

実装証拠のappend順は、result identity R、`implementation_result`、そのIDをpayloadで参照するimplementation handoff、対応transitionの順とする。`implementation_result`から将来のhandoffを逆参照しない。

result bridge以外のrecordはBとRの両方を参照しない。通常実装ではBとRの値一致を要求しない。旧identity referenceやhash-only summaryをschema v3 identityへ混在させず、canonical identity、lookup key、一致判定、test gateの代用にしない。

`design_receipt.disposition: accept`は七段階を完了し、`TEST_POLICY.md`のentry gateへ証拠を渡す。entry gateは`orchestration_phase`に含めない。同一generationのterminal reentryは許可しない。terminal前はresult Rと実装差分を変えないpost-skim evidenceの新規runを許し、trusted recorderがlatest-validを更新する。修正、resume、reviseを続ける場合は明示的なrecovery inputとbaseline promotionにより次generationを開始し、全七段階を再実行する。

テスト失敗時は後続を停止し、読み取り専用解析の証拠を設計担当へ返す。修正を続ける契約では新しいgenerationを`pre_skim`から開始し、設計担当が解析証拠を受け取ったうえで全七段階を省略せず再実行する。その後のテスト開始は`TEST_POLICY.md`のentry gateが別に判定する。

## Rework and resume

- `MAX_REWORK_COUNT = 3`とする。初回実装と初回テストは数えず、限定修正へ着手する世代ごとに1加算する。
- 初回の作業許可には、承認済み範囲、修正方針、再作業最大強度、必須テスト内で行う最大3世代の限定修正を含める。危険領域またはMAXを除き、各世代の追加承認を要求しない。
- 同じ修正世代のレビューとテストを別々に加算しない。修正を行わない再確認も加算しない。異なる`error_key`への修正でも総`rework_count`へ加算する。
- 連続失敗は`error_key + 対象Spec + 対象ファイル + 失敗工程`で識別する。同じ組が限定修正後も2回連続した時点で上限前でも`waiting_human`へ停止する。
- 修正効果が機械的検証で確認できた場合だけ、その組の連続失敗回数を解除する。ログ文言の変化、一時的な非再現、担当またはProvider変更では解除しない。
- 環境、Provider、CLI、テスト起動経路の失敗を製品コードの失敗へ算入しない。分類を分け、同じ失敗を名称変更で分割しない。
- 上限内の修正は、開始時に承認された範囲、方針、最大強度、必須テスト内だけ自動進行できる。範囲または危険度が拡大した場合は再分類し、必要な承認を得る。
- 非ゼロ終了、計画外依存、編集不能、STOP後に別案や再実行へ自動移行しない。テスト本体へ到達する前の限定的な`preflight_error`だけは`TEST_POLICY.md`に従う。
- 同じ失敗が2回続いた場合は`FOCUS_CACHE_SPEC.md`に従って発生回数、失敗条件、確認済み原因、正解パターンを保存する。成功時は更新しない。
- 限定修正へ着手した後の非ゼロ終了またはSTOPは、その修正世代を消費済みとして保持する。上限到達後は新規修正、再テスト、再起動、追加担当の起動を禁止し、`needs_human_review`へ移す。
- 各修正世代は`work_id`、`generation`、`rework_count`、対象パス、開始時の現在差分、変更後差分、`error_key`、実装結果を持つ。レビュー、テスト、再確認だけでは世代を進めない。
- 停止時は現在差分、失敗テスト、エラーコード、ログ末尾、成果物、Focus Cache更新の有無を保存する。Protected Surfaceまたは配布工程で要求されない通常開発SHAを追加しない。
- 同じ作業IDでの再開、または新しい作業IDが未解決事案を引き継ぐ場合は`rework_count`と連続失敗回数を維持する。未解決の`error_key`、対象Spec、対象ファイル、失敗工程を一件も引き継がない新規作業だけリセットできる。

`waiting_human`からの操作は`resume`、`revise`、`rollback`、`abandon`だけとし、対象`work_id`を記録する。`resume`は現在差分、修正方針、`rework_count`、連続失敗回数を維持し、停止時から対象Spec、対象パス、差分に外部変更がないことを確認する。`revise`は変更後の範囲、安全工程、最大強度、必須テストを再確定し、MAXまたは危険領域なら新しい承認を得る。`rollback`は今回の作業差分だけをGitで一意に分離でき、対象提示と明示承認を得た場合だけ行い、既存のユーザー変更、失敗証拠、ログ、Focus Cacheを戻さない。`abandon`は未完了として差分と証拠を保存し、その後の再開には新しい`work_id`を使う。曖昧な続行指示は直前の停止作業を機械的に一意特定できる場合だけ`resume`として扱う。

## Process Level P0-P4

記録は`process_level:P0`〜`process_level:P4`とし、優先度は`priority:<value>`へ分離する。複数条件に該当する場合は最も高いProcess Levelを採用する。

| Process Level | 影響範囲 | 必須の安全工程 | テスト下限 |
|---|---|---|---|
| `process_level:P0` | 文言、読取専用調査、実行経路へ影響しない文書・メタデータ | 対象とdiffを確認し、コード・設定・成果物が変わらないことを確認 | 該当する構文、schema、リンク、diff-check |
| `process_level:P1` | 単一ファイルまたは単一機能の局所的で容易に復元可能な変更 | 現在差分、変更可能パス、復元方法 | 対象単体テストまたは限定検証 |
| `process_level:P2` | 複数ファイル、同一コンポーネントの複数経路、永続設定・互換契約 | 依存先、互換条件、backupまたはrollback | 対象テストと関連回帰 |
| `process_level:P3` | 複数コンポーネント、外部アプリ、プロセス間連携、永続データ、移行 | 隔離環境、停止・復旧、成果物保全、外部依存確認 | 単体、関連回帰、統合、必要時は限定実機 |
| `process_level:P4` | release、installer、distribution、security境界、破壊的・不可逆操作、広範な利用者データ | 明示承認、完全backup/rollback、監視、停止、成果物/manifest検証 | 全体回帰、統合、必要な実機、install/update/recovery/rollback |

外部アプリを実際に起動・停止・操作する場合は最低`process_level:P3`とする。永続設定または利用者データを書き換える場合は最低`process_level:P2`とする。配布物、インストーラ、更新・アンインストール、破壊的操作は`process_level:P4`とする。隔離やmock、既知解法、読取専用の先行調査は製品変更の影響範囲を下げない。個別仕様が厳しければ追加要件を優先する。

作業契約には最低限`process_level`、理由、`affected_components`、`safety_steps`、`minimum_tests`を記録する。不記載、理由不足、範囲不確定は`needs_review`とし、実装・実行へ進まない。

## Mechanical correction

機械補正は承認・編集・実行・テスト選定前に行い、宣言値を決して下げない。入力は宣言レベル、正規化済みworkspace相対の一意な対象パス（componentとeffect付き）、対象component、全操作フラグ、全Protected Surface、Risk Evidence、軽量ルート事実とする。パスに`..`、絶対パス、重複、空componentを許さない。パスcomponentは対象component一覧に存在しなければならない。意味的リスクを名前から推測しない。

下限は`P0=0`〜`P4=4`として次の最大値である。

```text
corrected_process_level = max(declared, scope, operation, protected_surface, risk_evidence)
```

- scope: writeなしで最大1 componentはP0、1 write/1 componentはP1、複数write/1 componentはP2、writeが複数componentならP3。
- operation: persistent settingsはP2。external app、persistent data、migrationはP3。release、distribution、installer、update/uninstall、破壊・不可逆、security boundary、広範なuser dataはP4。
- Risk Evidence: `cross_component`または`difficult`はP3、`distribution`または`irreversible`はP4の根拠にできる。

追加パス、component、true flag、厳しい保護下限は結果を低下させない。承認後の事実削除は下方補正でなくscope変更として再分類する。出力は宣言値、補正値、変更有無、各補正理由（rule/from/required/evidence）、レビュー状態・理由を含む。

必須値の欠落・不正値、非boolean flag、非正規化・workspace外パス、未知の保護面、根拠なし、異なる権威入力の矛盾は補正値を出さず`needs_review`とする。明示operation assertionsとflagの矛盾も同様である。自由文は機械根拠として解釈しない。

## Protected Surfaces（強制下限）

| surface_id | 条件 | 下限 | approval | SHA | rollback | mandatory verification |
|---|---|---|---|---|---|---|
| `security_boundary` | 権限・sandbox・ACL・署名・信頼・入力検証境界 | `process_level:P4` | `explicit_human` | `required` | `full_required` | `security_tests+full_regression+integration+rollback_test` |
| `authentication` | 認証・認可・session・token・本人/権限判定 | `process_level:P4` | `explicit_human` | `required` | `full_required` | `auth_positive_negative+security_tests+full_regression+integration+rollback_test` |
| `secrets` | 秘密値・鍵・credentialの生成/保存/取得/伝送/rotation/削除 | `process_level:P4` | `explicit_human` | `required` | `full_required` | `secret_absence_scan+security_tests+full_regression+integration+rollback_test` |
| `distribution_installer` | 配布物・manifest・署名・installer・更新・uninstall | `process_level:P4` | `explicit_human` | `required` | `full_required` | `full_regression+integration+install_update_uninstall+manifest_hash+rollback_test` |
| `destructive_operation` | 削除・上書き・不可逆変換・広範な強制終了 | `process_level:P4` | `explicit_human` | `required` | `full_required` | `isolated_dry_run+full_regression+integration+recovery_test+rollback_test` |
| `user_data` | 利用者所有データの読取/書込/移動/変換/削除経路 | `process_level:P3` | `approved_contract` | `required` | `required` | `unit+related_regression+integration+data_integrity+recovery_test` |
| `persistent_schema` | 永続schema・migration・互換性・versioning | `process_level:P3` | `approved_contract` | `required` | `required` | `schema_validation+forward_backward_migration+related_regression+integration+rollback_test` |
| `process_stop` | PID選択・signal・timeout・kill・子process終了 | `process_level:P3` | `approved_contract` | `required` | `required` | `pid_identity+stop_scope+unit+related_regression+integration+recovery_test` |
| `external_app` | 外部アプリの起動・停止・操作または連携経路 | `process_level:P3` | `approved_contract` | `required` | `required` | `dependency_precheck+unit+related_regression+integration+limited_real_app_test+recovery_test` |

該当面は独立に判定し、複数なら最高下限・最厳要件をANDで採用する。広範・破壊的・不可逆なuser data操作は`destructive_operation`にも該当する。秘密値そのものをSHA、log、diff、test artifactへ出さない。SHAは該当する非秘密の対象、仕様、schema、manifestへ結び付ける。

保護面があれば変更前SHA、rollback plan、mandatory testsを必須とし、`route:lightweight`を禁止する。Protected Surface判定とImplementation Intensityは独立であり、`implementation_intensity:LOW`でも下限、承認、SHA、rollback、検証を緩和しない。`explicit_human`は作業ID・対象・範囲・SHA・安全工程・rollback・検証への明示承認、`approved_contract`は同項目を含む有効な承認済み契約を意味する。不足は`waiting_human`。人間、model、mock、隔離、preflight訂正も下限をwaiveできない。値欠落または矛盾は`needs_review`とし、機械出力は`state:needs_review`とする。終了コード0だけで検証合格にしない。

## Lightweight route

軽量ルートは安全な限定作業で分業、cache入力、無関係な全体回帰を省く経路であり、Work Packetを作らない。次の全条件が必要である。

- `process_level:P0`または`process_level:P1`、かつ`implementation_intensity:LOW`または`implementation_intensity:MID`。
- 変更可能パス、成功条件、最低検証が確定。
- 単一担当で完結し、交代・並列・引継ぎが不要。
- 局所的で既知interfaceと復元方法がある。
- 未解決failure、強制停止、承認外diffがない。

`process_level:P2` 以上、`implementation_intensity:HIGH`または`implementation_intensity:MAX`、外部アプリ、process間連携、永続設定、永続データ、user data、migration、release、配布物、manifest、installer、update/uninstall、破壊的・不可逆、失敗、非ゼロ終了、強制停止、test不合格後の修正/再実行、Protected Surface、認証/security境界、複数componentのいずれかは標準ルートを強制する。不明は`route:standard`かつ`needs_review`。

軽量時だけ複数sub-agent、同一ファイル二段階編集、focus cache入力、一時推論snapshot、handoff capsule、無関係な回帰を省略できる。仕様、scope、現在SHA、依存、承認、変更前SHA、差分確認、対象review、最低検証は省略できない。P0はdiffと該当静的検証、P1は差分確認・対象単体テストまたは限定検証・復元可能性が最低限である。終了コード0だけで合格にせず、期待した差分と成果を確認する。

scope/依存の拡大、二軸上昇、計画外ファイル・保護面・外部依存、test failure/非ゼロ/停止、追加担当・cache・回帰の必要、契約/仕様/対象SHA不一致で即停止する。停止後は二軸を再判定し、`route:standard`へ昇格する。軽量ルート内で修正、再試行、条件緩和を行わない。

```yaml
route: lightweight | standard
process_level: P0 | P1 | P2 | P3 | P4
implementation_intensity: LOW | MID | HIGH | MAX
scope_bounded: true | false
success_conditions_bound: true | false
minimum_tests_bound: true | false
single_actor: true | false
unresolved_failure: true | false
external_app: true | false
persistent_data: true | false
distribution_change: true | false
destructive_operation: true | false
protected_surface: true | false
route_reason: <判定根拠>
```

## Risk Evidence

```yaml
risk_evidence:
  failure_frequency: none | isolated | repeated
  ambiguity: low | medium | high
  blast_radius: local | component | cross_component | distribution
  known_solution_confidence: unknown | low | medium | high
  dependency_volatility: low | medium | high
  rollback_difficulty: easy | bounded | difficult | irreversible
  evidence_refs: [<log, diff, spec, manifest or test reference>]
```

全6軸と1件以上の証拠を必須とする。失敗回数だけでIntensityを上げず、既知解法でIntensity・Process Level・test下限を下げない。環境原因を実装失敗へ変換しない。根拠不足・矛盾は`needs_review`。Risk Evidence自体に承認、実装、test省略、完成判定の権限はない。

## 機械的正本と停止規則

`tools/process_classifier.py`がJSON入力を検証し、JSON出力として補正レベル、Protected Surface、承認、mandatory verification、route、state、理由を返す。引数なしはstdin、引数ありはそのJSONファイルを読む。正常判定は終了0、`needs_review`は終了2。

専用contract testは1回だけ実行し、非ゼロ後は再実行しない。ただしproduct/test未実行で原因がcommand path、quote、module spellingだけの`preflight_error:true`は、記録したうえでコマンド文字列の限定訂正1回だけ許可する。この訂正でもProcess Level、承認、SHA、rollback、必須検証、安全境界を緩和しない。二度目の起動失敗、test実行後の失敗は停止する。`preflight_error`で承認不足、SHA不一致、ファイル不存在、正本不明、workspace外参照、権限エラー、reparse point、秘密露出、rollback欠落を回避してはならない。
