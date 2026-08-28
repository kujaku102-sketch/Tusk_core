# Error Policy Consolidation

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-008: Error Policy consolidation`
- Legacy filename: `specs/TCS-008_ERROR_POLICY.md`

## Purpose and Requirement

人間向けのエラーコード空間とmarker文法を`ERROR_POLICY.md`へ統合し、parserが読む具体的コード一覧を`ERROR_CODES.md`へ維持する。`ERROR_CODES_SPEC.md`は互換redirectとして責務を限定する。

## Authority references

- 人間向けError Authority: `ERROR_POLICY.md`
- 機械registry: `ERROR_CODES.md`
- 互換入口: `ERROR_CODES_SPEC.md`

## Scope and Outcome

監視ツールのregistry入力パスを変更せず、新旧責務を区別する統合を対象とした。legacy Specは専用・監視回帰53件とCore全体91件の成功を記録した。

## Acceptance

人間向け方針、機械registry、互換redirectの責務が分離され、監視toolの入力契約が維持されることを確認する。

## History

- 2026-08-17: 方針正本、互換redirect、専用契約テストを追加した。
- 2026-08-17: 個別・監視回帰53件、Core全体91件が成功した。
- 2026-08-21: legacy identityを保持してnumberless Specへ移行した。

## Non-authority boundary

本Specはエラー規則やコード一覧を複製せず、`ERROR_POLICY.md`と`ERROR_CODES.md`を上書きしない。新しいerror codeを割り当てるAuthorityではない。
