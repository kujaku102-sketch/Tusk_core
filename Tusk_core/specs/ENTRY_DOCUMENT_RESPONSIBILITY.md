# Entry Document Responsibility

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-009: Entry document responsibility`
- Legacy filename: `specs/TCS-009_ENTRY_DOCUMENTS.md`

## Purpose and Requirement

`START-HERE.md`、`AGENTS.md`、`README.md`の入口責務を分離し、詳細規則を重複せず各Authorityへ参照させる。

## Authority references

- 読み順と参照導線: `START-HERE.md`
- AI作業境界、権限、安全契約: `AGENTS.md`
- 人間向け概要、導入、代表コマンド: `README.md`

## Scope and Outcome

入口3文書を対象とし、`START-HERE.md`を短い導線、`AGENTS.md`を作業境界、`README.md`を人間向け概要へ限定した。詳細規則は各Authorityへ委譲した。

## Acceptance

入口3文書の責務が区別され、詳細規則の重複を作らず、既存Core契約との参照整合を保つことを確認する。

## History

- 2026-08-17: 入口3文書を責務別に縮約した。
- 2026-08-17: focused 13件、Core全体94件が成功した。
- 2026-08-21: legacy identityを保持してnumberless Specへ移行した。

## Non-authority boundary

本Specは入口文書の責務と履歴を記録する。AI境界、Process、Routing、Test、Errorの詳細規則を再掲せず、それぞれのAuthorityを上書きしない。
