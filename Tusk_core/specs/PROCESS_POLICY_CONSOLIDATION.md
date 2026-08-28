# Process Policy Consolidation

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-005 Process Policy Consolidation`
- Legacy filename: `specs/TCS-005_PROCESS_POLICY.md`

## Purpose and Requirement

Process Level、機械補正、Protected Surface、軽量ルート、Risk Evidenceを`PROCESS_POLICY.md`へ統合し、1概念1正本とする。判定可能な規則は`tools/process_classifier.py`を機械的正本とし、欠落、型不一致、正規化違反、事実の矛盾を安全側へ停止させる。

## Authority references

- 人間向けProcess Authority: `PROCESS_POLICY.md`
- 機械判定: `tools/process_classifier.py`
- 技術難度とProvider routing: `ROUTING_POLICY.md`

## Scope and Outcome

変更対象は統合時の`PROCESS_POLICY.md`、classifier、専用テスト、legacy Specであった。宣言値、変更範囲、操作フラグ、Protected Surface、Risk Evidenceから安全側のProcess Levelを決め、レベルや検証下限を下げず、軽量ルートを限定する統合結果を記録する。Implementation Intensityは軽量ルート適格性以外へ作用せず、Provider routingを扱わない。

## Acceptance

`PROCESS_POLICY.md`とclassifierの契約が一致し、専用契約テストが安全側補正、Protected Surface、軽量ルート、入力拒否を検証できることを確認する。

## History

- 2026-08-17: 統合正本、JSON CLI、専用単体テストを追加した。
- 2026-08-17: `python -m unittest tests/test_process_classifier.py`を1回実行し、8件合格、終了コード0、再実行なし。
- 2026-08-17: 旧契約テスト互換性のため、固定語句、完全な表形式、機械判定レコードを正本へ復元した。
- 2026-08-21: legacy identityを保持してnumberless Specへ移行した。

## Non-authority boundary

本Specは統合の目的、範囲、履歴、受入を記録する。Process Levelやclassifier schemaを複製せず、`PROCESS_POLICY.md`と`tools/process_classifier.py`を上書きしない。
