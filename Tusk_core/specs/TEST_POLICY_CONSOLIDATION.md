# Test Policy Consolidation

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-007: Test Policy consolidation`
- Legacy filename: `specs/TCS-007_TEST_POLICY.md`

## Purpose and Requirement

人間向けテスト方針を`TEST_POLICY.md`へ統合し、focused/component/fullの責務、focused未対応変更の安全側補正、上位gate非代替、起動前経路不備の限定補正を明確にする。機械対応表と選択処理は別の正本へ維持する。

## Authority references

- 人間向けテスト方針: `TEST_POLICY.md`
- 機械対応表: `TEST-MAP.json`
- 選択処理: `tools/test_selector.py`

## Scope and Outcome

統合時の`TEST_POLICY.md`、`TEST-MAP.json`、legacy Spec、専用契約テストを対象とした。旧`TEST_SELECTION.md`を互換redirectとし、新規参照を禁止した。テスト本体実行前の経路不備だけを限定補正し、fixture不一致を通常の限定修正として分離した。

## Acceptance

人間向けAuthority、機械対応表、selectorの責務が分離され、専用契約テストがstage、安全側補正、上位gate非代替、focused mappingを確認する。

## History

- 2026-08-17: `TEST_POLICY.md`、focused mapping、専用契約テストを追加し、1件成功した。
- 2026-08-17: 起動前経路不備に限る1回補正契約を追加した。
- 2026-08-17: `test_tusk_manager` fixtureをLF固定バイト列へ修正し、focused 3件、Core全体89件が成功した。
- 2026-08-21: 専用契約テストとlegacy identityをnumberless namingへ移行した。

## Non-authority boundary

本Specは統合履歴と受入を記録する。stage対応表、selector処理、製品固有tierを複製せず、`TEST_POLICY.md`、`TEST-MAP.json`、`tools/test_selector.py`を上書きしない。
