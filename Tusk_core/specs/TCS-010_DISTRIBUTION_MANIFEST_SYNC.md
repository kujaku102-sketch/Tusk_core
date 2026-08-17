<!-- md-scope-document: COMMON -->
# TCS-010: Distribution manifest synchronization

## 実装状態

状態: `COMPLETED`

## 要求

- 配布対象を現行Core正本、互換redirect、実行Tool、配布テストへ同期する。
- 削除済み旧契約テストをmanifestから除外する。
- `archive/`、`specs/`、runtime state、manifest自身をhash対象外とする。

## 成功条件

- managed fileの不存在とSHA不一致が0件になる。
- integrity release検証とCore全体テストが成功する。

## 変更履歴

- 2026-08-17: 現行Core構成からmanifestを再生成。release integrity成功、Core全体94件成功。
