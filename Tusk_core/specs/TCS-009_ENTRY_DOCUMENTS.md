<!-- md-scope-document: COMMON -->
# TCS-009: Entry document responsibility

## 実装状態

状態: `COMPLETED`

## 要求

- `START-HERE.md`は20行以内の参照導線に限定する。
- `AGENTS.md`はAIの作業境界・権限・安全契約を保持する。
- `README.md`は人間向け概要、導入、代表コマンドだけを保持する。
- 詳細規則を3文書へ重複記載せず、各正本へ参照させる。

## 成功条件

- 3文書の責務が専用契約テストで区別される。
- 既存Core契約テストとCore全体テストが成功する。

## 変更履歴

- 2026-08-17: 入口3文書を責務別に縮約。focused 13件、Core全体94件成功。
