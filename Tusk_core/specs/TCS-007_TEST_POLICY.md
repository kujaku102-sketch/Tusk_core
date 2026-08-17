<!-- md-scope-document: COMMON -->
# TCS-007: Test Policy consolidation

## 実装状態

🟢 `[完了 / COMPLETED]` (TCS-007): 人間向けテスト方針を単一正本へ統合し、専用契約テストを通過。

## 要求

- `TEST_POLICY.md`をfocused/component/fullの人間向け正本とする。
- 機械的な対応表は`TEST-MAP.json`、選択処理は`tools/test_selector.py`を正本とする。
- 未対応のfocused変更はcomponentへ補正し、下位stageで上位stageを代替しない。
- テスト本体実行前の経路不備だけを`preflight_error`として1回自動補正する。
- 旧`TEST_SELECTION.md`は互換リダイレクトとし、新規参照を禁止する。

## 変更可能パス

- `TEST_POLICY.md`
- `TEST-MAP.json`
- `specs/TCS-007_TEST_POLICY.md`
- `tests/test_tcs007_test_policy_contract.py`

## 禁止事項

- 他のCore方針、入口文書、他TCSを変更しない。
- テスト対応表や選択ロジックをMarkdownへ重複実装しない。

## 成功条件

- 新正本が3 stage、focusedの安全側補正、上位gate非代替を定義する。
- 新正本の変更が専用契約テストへfocused mappingされる。
- 専用契約テストが1回で成功する。

## 変更履歴

- 2026-08-17: `TEST_POLICY.md`、focused mapping、専用契約テストを追加。1件成功。
- 2026-08-17: 経路・作業ディレクトリ・import経路の起動前不備に限り、1回自動補正して続行する契約を追加。fixture不一致は通常の限定修正として分離。
- 2026-08-17: `test_tusk_manager`のfixtureをLF固定バイト列へ修正し、focused 3件成功。Core全体89件成功。
