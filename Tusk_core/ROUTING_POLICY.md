# Routing Policy

## Purpose and canonical boundaries

This policy is the canonical contract for technical implementation difficulty and MAX escalation. It does not define actor authority, impact, safety procedure, approval gates, protected-surface floors, rollback requirements, or minimum test scope. Actor authority belongs to `AUTHORITY_SEPARATION.md`; safety and process requirements belong to `PROCESS_POLICY.md`.

Classification therefore uses two independent axes through separate canonical sources:

- technical difficulty: this `ROUTING_POLICY.md`;
- risk and safety procedure: `PROCESS_POLICY.md`.

Neither axis may be inferred from the other: a `LOW` implementation may require the highest Process Level, while a `MAX` implementation may require the lowest. Process Level meanings are intentionally not repeated here.

## Implementation Intensity

Implementation Intensity classifies only technical implementation difficulty.

| Level | Technical difficulty |
|---|---|
| `LOW` | Text, constants, isolated Markdown, or a mechanically bounded edit |
| `MID` | Bounded logic in one feature with established interfaces |
| `HIGH` | Complex logic, multiple internal dependencies, concurrency, or difficult diagnosis |
| `MAX` | Exceptional implementation requiring the most capable route and focused review |

Process Level independently owns impact, protected surfaces, safety procedure, approval gates, rollback requirements, and minimum test scope. Changing the executing provider does not change Intensity, Process Level, safety floors, or approval conditions, and a review must not be replaced by a self-review of the implementer.

## MAX gate

`MAX` is exceptional and must not be selected for ordinary implementation or repair. Start with the lowest justified level among `LOW`, `MID`, and `HIGH`.

Automatic classification as `MAX` is permitted only when current evidence establishes at least one trigger:

1. `recurrent_error_or_stop`: errors or forced stops recur enough to show the current route is not converging; or
2. `high_route_impractical`: implementation is technically impractical for the `HIGH` route to perform reliably.

The classification must state the trigger, evidence, previous intensity, and work ID. A preference for a stronger model, vague low confidence, schedule pressure, or Process Level alone is invalid.

`MAX` may be classified automatically but must never be activated automatically. Before edits, tests, restarts, builds, or implementation-agent dispatch, stop and obtain explicit owner approval for the work ID, affected paths, proposed change, Process Level, rollback, and required tests. The approval is an `APPROVAL` event with `action` `max` and `target` equal to the plan reference; it is separate from the work approval. Missing approval, an approval for another plan, or an approval with narrower paths keeps the work stopped.

Approval permits only the stated MAX implementation and its approved verification. Any further repair, reimplementation, scope expansion, or later MAX activation stops again before edits or tests and requires a new explicit approval.

## Authority boundary

この文書は技術難度だけを決める。担当ごとの実行権限、提案権限、自己承認禁止、人間承認の責務は`AUTHORITY_SEPARATION.md`を正本とする。再作業、停止、承認が必要となる危険条件は`PROCESS_POLICY.md`を参照する。難度の判定や担当の変更を権限拡大、停止解除、テスト省略の根拠にしない。

## Failure analysis routing

解析担当は失敗時だけ読み取り専用で起動する。入力は現行Spec、対象差分、構造化された失敗証拠へ限定する。

解析結果は原因候補と修正候補であり、実装開始、状態解除、成功、完成を単独で決定しない。実ログと照合して原因を確定する担当が、必要な場合だけImplementation Intensityを一段階上げた限定修正を決める。MAXへ到達する場合はMAX gateを適用する。成功時、軽度問題だけの時、所有者による正常停止時は解析担当を起動しない。

## Mandatory stop and prohibited actions

次のいずれかでは推測で補わず`info_missing`で停止し、編集・テスト・実行へ進まない。

- 必須入力、設計図、対象差分、適用仕様、対象パスが欠落または矛盾する。
- 影響範囲または技術難易度を独立して確定できない。
- `affected_paths`に承認予定外または未解決のパスが含まれる。
- `MAX`条件またはMAX承認の記録を証拠で確認できない。
- 個別仕様とCore正本の優先関係を確定できない。

読み取り専用の担当は停止状態を解除しない。また、ファイルの作成・編集・削除・移動、設定変更、テスト・ビルド・製品コード・外部アプリ・監視ツールの実行、プロセス操作、承認・実装開始・完成・成功判定、一方の軸から他方への推定、根拠のないMAX選択、MAX承認の更新を行わない。
