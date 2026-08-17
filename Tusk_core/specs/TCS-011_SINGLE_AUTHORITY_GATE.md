<!-- md-scope-document: COMMON -->
# TCS-011: Single Authority and Creation Gate

## 実装状態

状態: `COMPLETED`

## 要求

- `GENERAL.md`へSingle Authority Principleを追加する。
- 概念と正本の対応を`AUTHORITY-MAP.json`へ一元化する。
- 新規Markdown AuthorityはCreation Gateを既定とする。
- 外部モデルを設計者ではなく読み取り専用監査担当として制限する。
- 監査レポートを一時JSON証拠とし、正本化しない。

## 変更可能パス

- `GENERAL.md`
- `AGENTS.md`
- `AUTHORITY-MAP.json`
- `tools/authority_auditor.py`
- `tests/test_authority_auditor.py`
- `TEST-MAP.json`
- 本Spec

## 成功条件

- 現行Authority監査が問題0件で成功する。
- 既存概念は既存正本へ戻される。
- 未確認の新規概念は拒否され、独立概念だけ新規Authority候補を許可する。
- 監査とCreation Gateがファイルを変更しない。
- Core全体テストとrelease integrityが成功する。

## 変更履歴

- 2026-08-17: 原則、Authority map、監査Tool、Creation Gate、専用テストを追加。専用4件、Core全体98件成功。Authority監査0件。
