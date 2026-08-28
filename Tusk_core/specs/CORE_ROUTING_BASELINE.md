# Core Routing Baseline

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-001 Core Routing Baseline`
- Legacy filename: `specs/TCS-001_CORE_ROUTING_BASELINE.md`

## Purpose and Requirement

改善案1〜6で確認したImplementation IntensityとProcess Levelの二軸、流し見、軽量ルート、Protected Surface、Process Level機械補正のbaselineを記録する。各概念の責務を移動せず、独立した二軸表現、安全側のProcess Level補正、軽量ルートの安全境界を維持することが目的である。

## Authority references

- 技術難度、流し見、Provider routing: `ROUTING_POLICY.md`
- Process Level、Protected Surface、軽量ルート、機械補正: `PROCESS_POLICY.md`と`tools/process_classifier.py`
- Execution/Proposal Authority: `AUTHORITY_SEPARATION.md`

## Scope and Outcome

Core共通routing baselineを対象とする。legacy Specは`LOW/P4`と`MAX/P0`を独立に表現できること、Process Levelを低下させないこと、`P2+`・Protected Surface・失敗後に軽量ルートへ入らないことを完了条件として記録した。

## Acceptance

上記Authorityと対応する契約テストが二軸の独立性、安全下限、流し見の権限境界を保持していることを確認する。具体的な機械判定はAuthorityとToolに従い、本Specから生成しない。

## History

- 2026-08-17: 改善案1〜6のbaselineを`COMPLETED`として正式化した。
- 2026-08-21: legacy identityを保持してnumberless Specへ移行した。

## Non-authority boundary

本Specはbaselineの目的、履歴、受入範囲を記録する非機械Authorityである。routing値、Process Level補正、承認、実行可否を再定義せず、参照先AuthorityとToolを上書きしない。
