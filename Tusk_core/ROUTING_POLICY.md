<!-- md-scope-document: COMMON -->
# Routing Policy

## Purpose and canonical boundaries

This policy is the canonical contract for technical implementation difficulty, skim classification, implementation-provider routing, MAX escalation, and Execution/Proposal Authority. It does not define impact, safety procedure, approval gates, protected-surface floors, rollback requirements, or minimum test scope. Those belong to `PROCESS_POLICY.md`.

Skim therefore classifies two independent axes through separate canonical sources:

- technical difficulty: this `ROUTING_POLICY.md`;
- risk and safety procedure: `PROCESS_POLICY.md`.

Provider names are routing defaults, not authorization. Provider substitution does not change Process Level and does not waive an approved path, review, or test contract. Neither axis may be inferred from the other: a `LOW` implementation may require the highest Process Level, while a `MAX` implementation may require the lowest. Process Level meanings are intentionally not repeated here.

## Implementation Intensity

Implementation Intensity classifies only technical implementation difficulty. It controls the implementation provider and the amount of implementation context or cache supplied.

| Level | Technical difficulty | Default implementation route | Cache input ceiling |
|---|---|---|---:|
| `LOW` | Text, constants, isolated Markdown, or a mechanically bounded edit | lightweight implementation provider | 8 KiB |
| `MID` | Bounded logic in one feature with established interfaces | standard implementation provider | 8 KiB |
| `HIGH` | Complex logic, multiple internal dependencies, concurrency, or difficult diagnosis | `Terra/mid` implementation with high-reasoning review | 16 KiB |
| `MAX` | Exceptional implementation requiring the most capable route and focused review | highest-capability implementation and review route | 24 KiB |

Implementation Intensity owns only technical implementation difficulty, implementation-provider routing, and implementation context/cache volume. Process Level independently owns impact, protected surfaces, safety procedure, approval gates, rollback requirements, and minimum test scope.

## Skim classification

流し見担当は、承認前の設計図、対象差分、適用可能なキャッシュだけを読み取り、実装難易度と安全工程を分類する読み取り専用担当である。実装、修正、テスト、ビルド、再起動、停止操作、状態解除、完了判定を行わない。この文書は難度判定、入力、出力、停止条件を定義し、安全工程の判定は`PROCESS_POLICY.md`を参照してその規則を上書きしない。

流し見結果は次の単一レコードを必ず返す。

```yaml
implementation_intensity: LOW | MID | HIGH | MAX | null
intensity_reason: <technical evidence or null>
provider_route: <selected provider or null>
cache_input_ceiling_kib: 8 | 16 | 24 | null
automatic_max_count: 0 | 1 | null
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

## Provider routing and snapshot policy

Intensityの既定Providerは上表から選ぶ。Process Level、テスト数、作業優先度をProvider選択の代用にしない。Providerを置換してもIntensity、Process Level、安全下限、承認条件は変わらない。

| Intensity | Snapshot policy |
|---|---|
| `LOW` | `ON_FAILURE` |
| `MID` | `ONE_GENERATION` |
| `HIGH` | `TWO_GENERATIONS` |
| `MAX` | `THREE_GENERATIONS` |

Snapshot policyは入力候補の選定であり、流し見担当自身がキャッシュを書き換える許可ではない。`required_tests`はProcess Levelのテスト下限と個別仕様から導出し、Intensityから決めない。

## MAX gate

`MAX` is exceptional and must not be selected for ordinary implementation or repair. Start with the lowest justified level among `LOW`, `MID`, and `HIGH`.

Automatic escalation to `MAX` is permitted only when current evidence establishes at least one trigger:

1. `recurrent_error_or_stop`: errors or forced stops recur enough to show the current route is not converging; or
2. `terra_mid_impractical`: implementation is technically impractical for `Terra/mid` to perform reliably.

The record must contain the trigger, evidence, previous intensity, and work ID before implementation continues. A preference for a stronger model, vague low confidence, schedule pressure, or Process Level alone is invalid.

Only one automatic `MAX` activation is allowed per work unit. `automatic_max_count` starts at `0`, is held in transient run state, and is persisted when the run fails, is interrupted, or requires handoff. It must never exceed `1`, including after provider changes, task handoff, process restart, or revised attempts in the same work unit.

After one `MAX`, any further repair, reimplementation, or second activation stops before edits, tests, restarts, or additional implementation-agent dispatch. Set `needs_human_review`, present the remaining failure and proposed scope, and obtain explicit human approval. Approval permits one stated continuation and does not reset `automatic_max_count`.

流し見担当は`automatic_max_count`を変更しない。現行run状態が`1`なら`needs_review: true`と`review_reason: max_already_applied_requires_human`を返す。失敗・中断からの再開時に値が欠落または不明の場合も同様に停止する。新規runは`0`から始める。`automatic_max_count > 1`または初回MAX後の未承認継続は`needs_human_review`である。

## Execution Authority and Proposal Authority

役割分離は責任衝突を防ぐために使い、通常作業へ承認階層を追加するために使わない。

- `Execution Authority`: 有効な契約内で実行する権限。
- `Proposal Authority`: 規則、Process Level、Protected Surface、テスト範囲の改善案を提出する権限。
- Proposal Authorityは編集、実行、承認、状態解除、完成判定を許可しない。
- 安全水準の昇格提案は開発指揮が根拠を確認して契約へ反映できる。
- 安全水準の低下提案は人間の明示承認なしに適用しない。
- Protected Surface、強制条件、個別Spec下限は提案で迂回できない。
- 提案却下は実装失敗または`rework_count`へ算入しない。

| Role | Performs | Does not perform |
|---|---|---|
| 開発指揮 | 仕様確認、範囲決定、担当割当、最終判定 | 危険操作の人間承認を代行しない |
| 実装担当 | 指定範囲の実装、構文・静的確認 | テスト成功や完成を自己宣言しない |
| レビュー担当 | 差分と仕様の照合 | 必要がない限りコードを変更しない |
| 監視スクリプト | テスト起動、終了コード・件数・SHA・成果物の機械判定 | 原因推論、コード変更、承認要求を行わない |
| 解析担当 | 失敗時だけ構造化ログを調査する | 成功時に起動しない、単独で修正を開始しない |
| 人間 | `MAX`、破壊操作、workspace外、配布、認証・秘密、利用者データ、非常時rollbackを承認する | 通常の限定修正ごとに承認しない |

通常経路は`実装 → レビュー → 監視スクリプトがテスト → 成功なら完了`。成功時は解析担当やテスト担当エージェントを起動しない。

失敗時は監視スクリプトが停止し、構造化ログを解析担当へ渡し、開発指揮が原因と限定修正を確定し、実装担当が修正し、監視スクリプトが再テストする。`MAX_REWORK_COUNT`内は追加承認なしで進める。同じ失敗が2回続くか上限到達時はFocus Cacheへ地雷を保存して`waiting_human`へ移す。

人間承認が必要な例外は、`MAX`、破壊的・不可逆操作、workspace外変更、リリース・配布・Installer・更新・uninstall、認証・秘密情報・広範な利用者データ、Gitで安全に分離できない非常時rollbackである。それ以外はユーザーの作業指示を開始許可として通常経路を進める。

## Mandatory stop and prohibited actions

次のいずれかでは推測で補わず`needs_review: true`とし、編集・テスト・実行へ進まない。

- 必須入力、設計図、対象差分、適用仕様、対象パスが欠落または矛盾する。
- 影響範囲または技術難易度を独立して確定できない。
- `confidence < 0.8`。
- `affected_paths`に承認予定外または未解決のパスが含まれる。
- `MAX`条件または`automatic_max_count`を証拠で確認できない。
- 個別仕様とCore正本の優先関係を確定できない。

未確定軸は`null`とし、`review_reason`へ不足情報を機械判定可能な短い識別子で記録する。流し見担当は停止状態を解除しない。また、ファイルの作成・編集・削除・移動、設定変更、テスト・ビルド・製品コード・外部アプリ・監視ツールの実行、プロセス操作、承認・実装開始・完成・成功判定、一方の軸から他方への推定、根拠のないMAX選択、MAX使用回数の更新を行わない。
