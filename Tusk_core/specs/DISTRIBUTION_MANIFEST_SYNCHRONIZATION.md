# Distribution Manifest Synchronization

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-010: Distribution manifest synchronization`
- Legacy filename: `specs/TCS-010_DISTRIBUTION_MANIFEST_SYNC.md`

## Purpose and Requirement

配布対象を現行Core正本、互換redirect、実行Tool、配布テストへ同期し、削除済み契約テストをmanifestから除外する。

## Authority references

- 配布対象とhash: `DISTRIBUTION-MANIFEST.json`
- Integrity方針と検証: `INTEGRITY_POLICY.md`と`tools/integrity_gate.py`

## Scope and Outcome

managed file集合の同期を対象とする。`archive/`、`specs/`、runtime state、manifest自身はhash対象外という既存境界を保持し、legacy Specはmanaged file不存在とSHA不一致を0件にした結果を記録した。

## Acceptance

manifestのmanaged pathとSHAが配布対象に一致し、Integrity Authorityのrelease検証がその集合を検証できることを確認する。

## History

- 2026-08-17: 現行Core構成からmanifestを再生成した。
- 2026-08-17: release integrityとCore全体94件が成功した。
- 2026-08-21: legacy identityを保持してnumberless Specへ移行した。

## Non-authority boundary

本Specは同期の目的、境界、履歴を記録する。managed file集合やSHAを複製せず、`DISTRIBUTION-MANIFEST.json`とIntegrity Authorityを上書きしない。
