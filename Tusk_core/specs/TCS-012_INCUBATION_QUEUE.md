<!-- md-scope-document: COMMON -->
# TCS-012: Incubation Queue

## 実装状態

状態: `COMPLETED`

## 要求

- InQを非権威の観測・改善候補・提案待ち領域として定義する。
- 単一`INCUBATION_SPEC.md`へ分類、状態遷移、採用境界をまとめる。
- workspace配下へ原子的に保存し、Core・拡張・製品正本を変更しない。
- 自動昇格、自動採用、テスト省略、Process Level低下を禁止する。

## 成功条件

- evidenceとreviewerなしにverifiedへ進めない。
- 未登録Authorityへproposedを作れない。
- adoptedでも正本を自動編集しない。
- Core全体テストとrelease integrityが成功する。

## 変更履歴

- 2026-08-17: InQ正本、CLI、状態遷移、専用テストを追加。限定8件、Core全体102件成功。
