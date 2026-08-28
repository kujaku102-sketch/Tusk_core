# Proposal Authority and Safety Appeal

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-004 Proposal Authority and Safety Appeal`
- Legacy filename: `specs/TCS-004_PROPOSAL_AUTHORITY.md`

## Purpose and Requirement

改善案12〜13でExecution AuthorityとProposal Authorityを分離し、安全水準の変更提案とその適用権限を区別する。提案は編集、実行、承認、状態解除の権限を与えず、安全水準の低下は人間の明示承認を必要とする。

## Authority references

- Execution/Proposal AuthorityとSafety Appeal: `AUTHORITY_SEPARATION.md`
- Process LevelとProtected Surfaceの下限: `PROCESS_POLICY.md`
- Single Authority Principle: `GENERAL.md`と`AUTHORITY-MAP.json`

## Scope and Outcome

契約改善、Process Level、Protected Surface、テスト範囲に関する提案境界を対象とする。legacy SpecはProtected Surface、P4強制条件、個別Spec下限を異議申立てで迂回しない結果を`COMPLETED`として記録した。

## Acceptance

参照Authorityと契約テストが「提案できる」と「適用できる」を区別し、安全水準の低下を自動適用しないことを確認する。

## History

- 2026-08-17: 改善案12〜13を`COMPLETED`として正式化した。
- 2026-08-21: legacy identityを保持してnumberless Specへ移行した。

## Non-authority boundary

本Spec自体は提案の採用、承認、編集、状態遷移を実行しない。権限規則を再掲せず、`AUTHORITY_SEPARATION.md`と安全Authorityを上書きしない。
