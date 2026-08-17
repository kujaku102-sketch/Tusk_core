<!-- md-scope-document: COMMON -->
# TCS-005 Process Policy Consolidation

状態: `COMPLETED`

## 要求

Process Level、機械補正、Protected Surface、軽量ルート、Risk Evidenceを`PROCESS_POLICY.md`へ統合し、1概念1正本にする。判定可能な規則は`tools/process_classifier.py`を機械的正本とし、標準ライブラリだけでJSON入出力する。既存5文書は移行期間中そのまま維持する。

## 成功条件

- 宣言値、変更範囲、操作フラグ、Protected Surface、Risk Evidenceから安全側のProcess Levelを決定する。
- 判定はレベルを下げず、Protected Surfaceの承認・検証下限を緩和しない。
- 軽量ルートは全許可条件が成立し、禁止条件がない場合だけ選ぶ。
- 欠落、型不一致、正規化違反、事実の矛盾は`needs_review`とし、補正値を出さない。
- Implementation Intensityは軽量ルート適格性以外へ作用せず、Provider routingを扱わない。
- 専用テストを規定どおり1回だけ実行し、全件合格する。

## 変更可能パス

- `PROCESS_POLICY.md`
- `tools/process_classifier.py`
- `tests/test_process_classifier.py`
- `specs/TCS-005_PROCESS_POLICY.md`

## 禁止事項

- 旧文書の削除、スタブ化、内容変更
- 他の正本、ツール、テスト、Specの変更
- 名前から意味的リスクを推測する処理
- 安全下限の引下げ

## 実装結果

- 統合正本、JSON CLI、専用単体テストを追加した。
- 検証: `python -m unittest tests/test_process_classifier.py`を1回実行し、8件合格（終了コード0）。再実行なし。

## 変更履歴

- 2026-08-17: TCS-005を正式化し実装。
- 2026-08-17: 統合後の旧契約テスト互換性を回復するため、固定語句、完全な表形式、機械判定レコードを正本へ復元。
