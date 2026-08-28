# Authority Separation

役割分離は責任の衝突を防ぐために使い、通常作業へ承認階層を追加するために使わない。

## 実行権限と提案権限

- `Execution Authority`: 有効な契約内で実行する権限。
- `Proposal Authority`: 規則、Process Level、Protected Surface、テスト範囲の改善案を提出する権限。
- Proposal Authorityは編集、実行、承認、状態解除、完成判定を許可しない。
- Process Levelの昇格提案は開発指揮が根拠を確認して契約へ反映できる。
- Process Levelの低下提案は人間の明示承認なしに適用しない。
- Protected Surface、P4強制条件、個別Spec下限は提案で迂回できない。
- 提案却下は実装失敗または`rework_count`へ算入しない。

## 役割

| 役割 | 行うこと | 行わないこと |
|---|---|---|
| 開発指揮 | 全体進行、仕様・契約・承認の照合、実装指示 | 設計、編集、自己レビュー、危険操作の人間承認の代行を行わない |
| 実装担当 | 渡された実装契約の範囲だけを編集し、構文・静的確認を行う | 独自設計、独自探索、自己レビュー、テスト成功や完成宣言を行わない |
| レビュー担当 | 差分と仕様の読み取り専用照合 | コードを変更しない |
| 監視スクリプト | テスト起動、終了コード・件数・SHA・成果物の機械判定 | 原因推論、コード変更、承認要求を行わない |
| 解析担当 | 失敗時だけ構造化ログを調査する | 成功時に起動しない、単独で修正を開始しない |
| 人間 | `MAX`、破壊操作、workspace外、配布、認証・秘密、利用者データ、非常時rollbackを承認する | 通常の限定修正ごとに承認しない |

## Seven-stage orchestration roles and order

通常作業の役割、順序、兼任禁止はこの節だけを正本とする。七段階は直列で実行し、並立、省略、順序変更を許可しない。`design`、`final_reviewer`、`commander`、`implementer`は必ず別担当とする。`pre_skim`と`post_skim`は同一の`skim`担当でもよいが、その担当は他の役割を兼任しない。`design`と`design_receipt`は同一の`design`担当が担う。

stage外setup、generation、revision、retry、counter、evidence admission、freshness、recoveryの意味は`PROCESS_POLICY.md`だけを正本とする。本節はそれらを定義せず、Processでadmitされた同一work・attempt・generationのbindingを七段階へ割り当てる形だけを定義する。stage外setupを第八stage、role、handoff edgeとして追加しない。

| Stage | Actor role | Authority | Incompatibility |
|---|---|---|---|
| `pre_skim` | `skim` | `read-only` | 他役割と兼任しない |
| `design` | `design` | `read-only` | `final_reviewer`、`commander`、`implementer`と別担当 |
| `commander_window` | `commander` | `read-only` | 設計、編集、自己レビューを兼任しない |
| `implementation` | `implementer` | `write` | 設計、開発指揮、自己レビューを兼任しない |
| `post_skim` | `skim` | `read-only` | 他役割と兼任しない |
| `final_review` | `final_reviewer` | `read-only` | `design`、`commander`、`implementer`と別担当 |
| `design_receipt` | `design` | `read-only` | `final_reviewer`、`commander`、`implementer`と別担当 |

stageからactorへの割当は作業・generationごとのappend-only actor binding recordで固定する。1件のbinding recordは次のfieldを必須とする。

```yaml
schema_version: 3
record_type: actor_binding
work_id: <stable work id>
attempt_id: <stable attempt id>
generation: <non-negative integer>
actor_bindings_id: <binding set id>
binding_id: <unique id within actor_bindings_id>
stage: <one of the seven stage names>
actor_role: skim | design | commander | implementer | final_reviewer
actor_id: <stable actor id>
created_at_utc: <UTC timestamp>
```

bindingは`(work_id, attempt_id, generation, actor_bindings_id, binding_id)`のcomposite keyでだけlookupする。七stageを重複なく完全にcoverageする7 recordを必須とし、`stage`と`actor_role`の対応は上表と完全一致させる。stage名をroleとして機械転記しない。`design`と`design_receipt`は同じdesign `actor_id`を必須とする。`pre_skim`と`post_skim`のskim actorは同一でも別actorでもよい。それ以外のcross-roleで同一`actor_id`を共有しない。admission、append順、work・attempt・generationのfreshnessは`PROCESS_POLICY.md`を参照する。

`pre_skim`と`post_skim`の対象、推論制約、入力、出力の詳細は`ROUTING_POLICY.md`の`Skim classification`を参照する。

## 通常経路

```text
pre_skim → design → commander_window → implementation → post_skim → final_review → design_receipt
```

各stageは直前のhandoffと同じbinding setを使う。`final_review`は`design_receipt`を担う`design`担当へ判定を返す。`design_receipt`は第七stageでありterminalとして`target_stage: null`を記録し、受領結果のrecipientに`commander`を指定する。setup、generation、terminal後の扱い、recovery、停止は`PROCESS_POLICY.md`を参照する。

テスト開始判定は七段階のstageまたはroleではない。七段階完了後に`TEST_POLICY.md`のentry gateが判定する。

成功時は解析担当やテスト担当エージェントを起動しない。

テスト実行専用エージェントは配置しない。テストの起動、監視、機械判定は監視スクリプトが担当し、最終受入は開発指揮が行う。実装担当または解析担当をテスト成功の判定者として兼任させない。

## Handoff contract

すべてのhandoffは次の共通schemaを持つ。欠落、stage edgeとactor bindingの不一致、identity record参照の不一致、未解決blockerがある場合は`needs_review`とし、次stageへ進まない。schemaは別fileへ複製しない。

```yaml
schema_version: 3
record_type: handoff
work_id: <stable work id>
attempt_id: <stable attempt id>
generation: <non-negative integer>
handoff_id: <unique handoff id>
source_stage: <source orchestration stage>
target_stage: <next orchestration stage or null for terminal receipt>
actor_bindings_id: <validated binding set id>
source_binding_id: <binding for source_stage>
target_binding_id: <binding for target_stage or null>
recipient_actor_role: commander | null
recipient_binding_id: <commander binding id or null>
spec: <current spec path or identity>
affected_paths: [<normalized workspace-relative path>]
decision: <stage decision>
payload: <stage-specific mapping>
evidence_refs: [<evidence reference>]
unresolved: [<unresolved item or none>]
run_id: <unique post-skim run id or null>
supersedes_handoff_ref: <prior post-skim handoff id or null>
created_at_utc: <UTC timestamp>
```

`source_stage`と`target_stage`は下表の6連続edgeと一致させ、source/target bindingは同じ`actor_bindings_id`のcomposite lookupで解決する。stage名をactorのrole fieldへ入れてはならない。identityの生値、snapshot SHA、epochは共通top-levelへ置かず、`payload`内のidentity record referenceだけで受け渡す。identityの正本は`PROCESS_POLICY.md`とする。stage固有payloadの必須fieldは次の最小集合とする。

| Handoff edge | Required payload fields |
|---|---|
| `pre_skim` → `design` | `orchestration_setup_ref`, `baseline_identity_record_ref`, `routing_record`, `candidates` |
| `design` → `commander_window` | `baseline_identity_record_ref`, `changes_by_path`, `forbidden_paths`, `implementation_contract`, `success_conditions`, `rollback_plan`, `required_tests` |
| `commander_window` → `implementation` | `baseline_identity_record_ref`, `design_handoff_id`, `implementation_contract`, `approval_id` |
| `implementation` → `post_skim` | `implementation_result_ref`, `changed_paths`, `static_checks` |
| `post_skim` → `final_review` | `implementation_result_ref`, `reviewed_identity_record_ref`, `design_handoff_id`, `design_coverage`, `candidates`, `unplanned_changes` |
| `final_review` → `design_receipt` | `reviewed_identity_record_ref`, `post_skim_handoff_id`, `verdict`, `findings`, `corrections` |

| Terminal stage | Target stage | Recipient role | Required payload fields |
|---|---|---|---|
| `design_receipt` | `null` | `commander` | `reviewed_identity_record_ref`, `final_review_handoff_id`, `disposition`, `reason` |

`design_receipt`のterminal recordは共通schemaの`target_stage`・`target_binding_id`を`null`、`recipient_actor_role`を`commander`、`recipient_binding_id`を現行generationのcommander bindingとする。`disposition`は`accept | needs_rework | stop`のいずれかとする。同一generationのterminal後にstageへ再入場しない。次generationを開始できる条件は`PROCESS_POLICY.md`が定義する。test gateはstageではなく`TEST_POLICY.md`だけが定義する。

### Cumulative stage checkpoints

七段階のcheckpointは同一attempt・現行generationについて累積する。`pre_skim`はsetup、baseline B、七actor bindingを要求し、以降の`design`、`commander_window`、`implementation`はそれぞれ直前edgeのhandoffとtransitionを追加する。`post_skim`はimplementation result、result R、implementation edgeを追加し、`final_review`はlatest-valid post-skimとそのtransition、`design_receipt`はfinal-review handoffとtransitionを追加する。stageの順序と六edgeを定義する正本は本節だけである。

`run_id`と`supersedes_handoff_ref`は`post_skim` sourceの場合だけnon-nullを許し、他のhandoffでは両方を`null`とする。post-skim担当のper-run dutyは`ROUTING_POLICY.md`、accepted/rejected envelope、latest-valid、freshness、terminal後の扱いは`PROCESS_POLICY.md`を参照する。

## 失敗経路

```text
監視スクリプトが停止
→ 構造化ログを解析担当へ渡す
→ 解析証拠を設計担当が受け取る
→ Processの停止・recovery contractへ渡す
```

停止後のgeneration、revision、retry、counter、再開可否は`PROCESS_POLICY.md`だけを正本とし、この文書では定義しない。

## 実装委任契約

実装担当には、対象Spec、対象機能、参照可能パス、変更可能パス、変更禁止パス、参照する設計、選択済み変数バインド、現在の要求または失敗、実装要求、Implementation Intensityと理由、Process Levelと理由、Processがadmitしたattempt reference、必要な承認ID、使用するエラーコード、成功条件、テスト工程への引渡し条件を渡す。Protected Surfaceで要求される場合だけ変更前SHAとrollback条件を含める。欠落または矛盾がある場合は推測で補わず`needs_review`を返す。

実装担当は渡された実装契約だけを判断根拠とし、契約にない仕様、ログ、Cache、他ファイルを独自探索しない。追加参照または追加変更が必要なら編集を止め、必要な対象と理由を返す。

実装担当の返答は変更ファイル、実装内容、構文・静的確認、未解決事項に限定する。テスト成功、状態解除、完成を自己宣言しない。実装担当は1担当を既定とする。複数担当を使う場合は対象、理由、担当境界、依存関係、競合防止策を提示し、人間の明示承認後だけ開始する。同一ファイルへ複数writerを置かず、同じファイルの二段階編集はレビューで問題が確定した限定修正だけにする。

## 人間承認が必要な例外

- `MAX`
- 破壊的または不可逆な操作
- workspace外の変更
- リリース、配布、Installer、更新、uninstall
- 認証、秘密情報、広範な利用者データ
- Gitで安全に分離できない非常時rollback

上記以外は、ユーザーの作業指示を開始許可として通常経路を進める。

`MAX`は分類だけ自動化できるが、実装、修正、テスト、再起動、ビルド、実装担当の起動は自動化しない。対象work ID、変更範囲、修正内容、Process Level、rollback、必須テストに対する人間の明示承認と承認IDを記録した後だけ開始する。承認範囲を超える追加修正または再実装には新しい承認を必要とする。
