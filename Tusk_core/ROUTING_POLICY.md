# Routing Policy

## Purpose and canonical boundaries

This policy is the canonical contract for technical implementation difficulty, skim classification, implementation-provider routing, and MAX escalation. It does not define actor authority, impact, safety procedure, approval gates, protected-surface floors, rollback requirements, or minimum test scope. Actor authority belongs to `AUTHORITY_SEPARATION.md`; safety and process requirements belong to `PROCESS_POLICY.md`.

Skim therefore classifies two independent axes through separate canonical sources:

- technical difficulty: this `ROUTING_POLICY.md`;
- risk and safety procedure: `PROCESS_POLICY.md`.

Provider names are routing defaults, not authorization. Provider substitution does not change Process Level and does not waive an approved path, review, or test contract. Neither axis may be inferred from the other: a `LOW` implementation may require the highest Process Level, while a `MAX` implementation may require the lowest. Process Level meanings are intentionally not repeated here.

## Implementation Intensity

Implementation Intensity classifies only technical implementation difficulty. It controls the implementation provider and the amount of implementation context or cache supplied.

| Level | Technical difficulty | Default implementation | Required review | Cache input ceiling |
|---|---|---|---|---:|
| `LOW` | Text, constants, isolated Markdown, or a mechanically bounded edit | `Luna/high` | `Terra/mid` | 8 KiB |
| `MID` | Bounded logic in one feature with established interfaces | `Luna/Ultra` | `Sol/low` | 8 KiB |
| `HIGH` | Complex logic, multiple internal dependencies, concurrency, or difficult diagnosis | `Terra/mid` | `Sol/mid` | 16 KiB |
| `MAX` | Exceptional implementation requiring the most capable route and focused review | highest-capability implementation route | highest-capability focused review | 24 KiB |

Implementation Intensity owns only technical implementation difficulty, implementation-provider routing, and implementation context/cache volume. Process Level independently owns impact, protected surfaces, safety procedure, approval gates, rollback requirements, and minimum test scope.

## Skim classification

流し見は`pre_skim`と`post_skim`の2 modeに分ける。どちらも読み取り専用で、対象全体から低推論の問題候補を抽出する。accept、設計、修正、実装、テスト、ビルド、再起動、停止操作、状態解除、完了判定を行わない。この文書は難度判定、入力、出力、停止条件を定義し、安全工程の判定は`PROCESS_POLICY.md`を参照してその規則を上書きしない。

### Pre-skim

`pre_skim`の必須入力はユーザー要求、現行Spec、対象コード全体、stage外の`orchestration_setup`が固定したsetup record・baseline identity record・actor binding set・承認・attempt・generation、適用可能な検証済みCacheである。出力は下記の完全な`routing_record`、低推論の`candidates`、`unresolved`とする。契約、強度、範囲を確認し、対象コードは断片でなく対象全体を読む。setup recordが参照する値を再計算、再生成、上書きせず、不一致は`needs_review`として返す。

`routing_record`は次の単一レコードを完全な形で必ず返す。

```yaml
implementation_intensity: LOW | MID | HIGH | MAX | null
intensity_reason: <technical evidence or null>
provider_route: <selected provider or null>
cache_input_ceiling_kib: 8 | 16 | 24 | null
max_activation_count: <non-negative integer or null>
max_approved: true | false | null
max_approval_id: <approval id or null>
max_trigger: null | recurrent_error_or_stop | terra_mid_impractical
max_evidence: null | <artifact or observation reference>
process_level: <value selected under PROCESS_POLICY.md or null>
process_level_reason: <impact and safety evidence or null>
confidence: <0.0 through 1.0>
affected_paths:
  - <normalized path>
risk_triggers:
  - <trigger or none>
risk_evidence:
  failure_frequency: none | isolated | repeated
  ambiguity: low | medium | high
  blast_radius: local | component | cross_component | distribution
  known_solution_confidence: unknown | low | medium | high
  dependency_volatility: low | medium | high
  rollback_difficulty: easy | bounded | difficult | irreversible
  evidence_refs: [<evidence reference>]
required_tests:
  - <test or none>
snapshot_policy: NONE | ON_FAILURE | ONE_GENERATION | TWO_GENERATIONS | THREE_GENERATIONS
needs_review: true | false
review_reason: <reason or null>
```

全フィールドを必須とする。`risk_evidence`およびProcess Levelは`PROCESS_POLICY.md`に従う。`affected_paths`、`risk_triggers`、`required_tests`は配列で記録し、該当なしも空欄ではなく`none`を明示する。`confidence`は根拠が揃った二軸判定全体の信頼度である。

### Post-skim

`post_skim`の必須入力は承認済み設計、実装契約、実装結果、完成差分の全体、対象ファイルの現在内容、`PROCESS_POLICY.md`で検証したresult identity recordである。出力は`reviewed_identity_record_ref`、`design_coverage`、低推論の`candidates`、`unplanned_changes`、`evidence_refs`、`unresolved`とする。設計への適合と計画外差分を完成差分全体で照合するが、accept、設計の変更、修正指示を行わない。

per-run dutyとして、post-skim担当は実行のたびに新しい`handoff_id`、新しい`run_id`、現在UTC、同じresult identity record R、直前のlatest-valid post-skimを指す`supersedes_handoff_ref`を持つrecordを提出する。初回だけ`supersedes_handoff_ref: null`とする。recordは担当自身がlogへ直接書かず、commander-controlled machine recorderへ渡す。

accepted/rejected envelope、record replay・conflict、latest-validの更新、invalidからvalidへのrecovery、stale、freshness、terminal後の禁止は`PROCESS_POLICY.md`だけを正本とする。本Policyはper-runの読取・提出duty以外のadmissionまたは状態意味を定義しない。

## Provider routing and snapshot policy

Intensityの既定Providerは上表から選ぶ。Process Level、テスト数、作業優先度をProvider選択の代用にしない。Providerを置換してもIntensity、Process Level、安全下限、承認条件は変わらない。

`Luna/high`または`Luna/Ultra`が利用できない場合は`Terra/mid`へ一度だけ切り替えられる。Provider利用可否の確認は作業単位で一度だけとし、接続失敗を反復しない。Provider変更自体は`rework_count`へ算入しない。レビューProviderを変更する場合も同等以上の読み取り専用レビュー能力を必要とし、実装担当による自己レビューへ置換しない。

| Intensity | Snapshot policy |
|---|---|
| `LOW` | `ON_FAILURE` |
| `MID` | `ONE_GENERATION` |
| `HIGH` | `TWO_GENERATIONS` |
| `MAX` | `THREE_GENERATIONS` |

Snapshot policyは入力候補の選定であり、流し見担当自身がキャッシュを書き換える許可ではない。`required_tests`はProcess Levelのテスト下限と個別仕様から導出し、Intensityから決めない。

## Provider operational roles

- `Sol`: Spec作成、変更許可、`MAX/HIGH/MID`のレビュー、失敗原因の確定、限定修正指示、最終受入を担当する。
- `Terra/mid`: `HIGH`実装、`LOW`レビュー、Luna実装Provider不在時の代替を担当する。
- `Luna/low`: 流し見と失敗ログ分析だけを行い、編集、テスト、再起動、停止操作、状態解除を行わない。
- `Luna/high`: `LOW`の限定実装を担当する。
- `Luna/Ultra`: `MID`の限定実装を担当する。
- `Antigravity Flash-Lite`: `Luna/low`不在時の流し見・失敗ログ分析だけを担当し、編集しない。
- `Luna/mid`: `HIGH/MAX`の担当交代時だけ、選択済み一時snapshotを引継ぎ用に圧縮する。新しい原因、修正案、成功判定を追加しない。

## MAX gate

`MAX` is exceptional and must not be selected for ordinary implementation or repair. Start with the lowest justified level among `LOW`, `MID`, and `HIGH`.

Automatic classification as `MAX` is permitted only when current evidence establishes at least one trigger:

1. `recurrent_error_or_stop`: errors or forced stops recur enough to show the current route is not converging; or
2. `terra_mid_impractical`: implementation is technically impractical for `Terra/mid` to perform reliably.

The record must contain the trigger, evidence, previous intensity, and work ID. A preference for a stronger model, vague low confidence, schedule pressure, or Process Level alone is invalid.

`MAX` may be classified automatically but must never be activated automatically. Before edits, tests, restarts, builds, or implementation-agent dispatch, set `needs_human_review` and obtain explicit human approval for the work ID, affected paths, proposed change, Process Level, rollback, and required tests. Record the approval as `max_approved: true` and a non-empty `max_approval_id`. Missing approval, an approval for another work ID, or an approval with narrower paths keeps the work stopped.

Approval permits only the stated MAX implementation and its approved verification. Any further repair, reimplementation, scope expansion, or later MAX activation stops again before edits or tests and requires a new explicit approval. `max_activation_count` is persisted across provider changes, task handoff, process restart, resume, and revise; approval does not reset it.

流し見担当は`max_activation_count`、`max_approved`、`max_approval_id`を変更しない。MAX分類時は`needs_review: true`と`review_reason: max_requires_explicit_human_approval`を返す。開発指揮が承認対象と現行契約を照合した後だけ`needs_human_review`を解除できる。失敗・中断・引継ぎ時に承認記録が欠落または不明なら停止を維持する。

## Authority boundary

この文書はProviderと技術難度だけを決める。担当ごとの実行権限、提案権限、自己承認禁止、人間承認の責務は`AUTHORITY_SEPARATION.md`を正本とする。再作業、状態遷移、停止、承認が必要となる危険条件は`PROCESS_POLICY.md`を参照する。Provider選択や変更を権限拡大、停止解除、テスト省略の根拠にしない。

## Failure analysis routing

解析Providerは失敗時だけ読み取り専用で起動する。`Luna/low`を第一候補、`Antigravity Flash-Lite`を一度だけ使える代替とし、接続を反復しない。入力は現行Spec、対象差分、構造化された失敗証拠へ限定する。Core guardの具体的なCLI、入力ファイル、通知結果は`tools/test_guard_monitor.py`を機械実装正本とする。

解析結果は原因候補と修正候補であり、実装開始、状態解除、成功、完成を単独で決定しない。`Sol`が実ログと照合して原因を確定し、必要な場合だけImplementation Intensityを一段階上げた限定修正を決める。MAXへ到達する場合はMAX gateを適用する。成功時、軽度問題だけの時、人間による正常停止時は解析Providerを起動しない。

## Mandatory stop and prohibited actions

次のいずれかでは推測で補わず`needs_review: true`とし、編集・テスト・実行へ進まない。

- 必須入力、設計図、対象差分、適用仕様、対象パスが欠落または矛盾する。
- 影響範囲または技術難易度を独立して確定できない。
- `confidence < 0.8`。
- `affected_paths`に承認予定外または未解決のパスが含まれる。
- `MAX`条件、`max_activation_count`、またはMAX承認記録を証拠で確認できない。
- 個別仕様とCore正本の優先関係を確定できない。

未確定軸は`null`とし、`review_reason`へ不足情報を機械判定可能な短い識別子で記録する。流し見担当は停止状態を解除しない。また、ファイルの作成・編集・削除・移動、設定変更、テスト・ビルド・製品コード・外部アプリ・監視ツールの実行、プロセス操作、承認・実装開始・完成・成功判定、一方の軸から他方への推定、根拠のないMAX選択、MAX承認・使用回数の更新を行わない。
