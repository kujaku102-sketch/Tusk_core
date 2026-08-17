<!-- md-scope-document: COMMON -->
# TCS-008: Error Policy consolidation

## 実装状態

状態: `COMPLETED`

## 要求

- 人間向けのコード空間・marker文法を`ERROR_POLICY.md`へ統合する。
- parserが読む具体的なコード一覧は`ERROR_CODES.md`に維持する。
- `ERROR_CODES_SPEC.md`は互換リダイレクトとする。

## 成功条件

- 監視ツールのregistry入力パスを変更しない。
- 新旧責務が専用契約テストで区別される。
- Core全体テストが成功する。

## 変更履歴

- 2026-08-17: 方針正本、互換リダイレクト、専用契約テストを追加。個別・監視回帰53件、Core全体91件成功。
