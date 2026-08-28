# Incubation Queue

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-012: Incubation Queue`
- Legacy filename: `specs/TCS-012_INCUBATION_QUEUE.md`

## Purpose and Requirement

InQを非権威の観測、改善候補、提案待ち領域として定義し、分類、状態遷移、採用境界を単一Authorityへまとめる。自動昇格、自動採用、テスト省略、Process Level低下を許可しない。

## Authority references

- InQ分類、状態、採用境界: `INCUBATION_SPEC.md`
- 保存と操作: `tools/inq.py`
- Authority割当: `AUTHORITY-MAP.json`

## Scope and Outcome

workspace内の原子的なInQ保存を対象とし、Core、Extension、製品Authorityを変更しない。evidenceとreviewerなしのverified、未登録Authorityへのproposed、adoptedからの自動編集を拒否する結果を記録する。

## Acceptance

InQ AuthorityとCLIが非権威性、状態遷移、Authority lookup、自動編集禁止を保持することを専用契約テストで確認する。

## History

- 2026-08-17: InQ正本、CLI、状態遷移、専用テストを追加した。
- 2026-08-17: 限定8件、Core全体102件、release integrityが成功した。
- 2026-08-21: legacy identityを保持してnumberless Specへ移行した。

## Non-authority boundary

本SpecはInQ採用の履歴と受入範囲を記録する。候補をAuthorityへ昇格せず、`INCUBATION_SPEC.md`、Core、Extension、製品正本を上書きしない。
