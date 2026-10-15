# Tusk Core: agent bootloader

Tusk Coreはドメイン非依存の実装・テスト契約を提供する。製品規則、製品ソース、
製品履歴をCoreへ混ぜない。

## Authority and loading

1. ユーザー要求と対象の現行Specを確認する。
2. `AUTHORITY-MAP.json`が指定する正本だけを読む。
3. 呼出側が選択したExtensionがある場合だけ、`EXTENSION_POLICY.md`に従ってその入口と`required_read_order`を読む。
4. 必要な場合だけCacheを読む。Focus Cacheは`EXTENSION_POLICY.md`、Context Cacheは作業領域の文書に従う。

Scopeは文書から取得しない。選択済みExtension、現在のtaskとSpec、Git diff、必要時のCacheから
実行時に導出する。

## Execution boundary

- 現在のGit branch、base、diff、ユーザー要求、現行Spec、テスト結果を境界とする。
- 指定外ファイルと無関係なユーザー変更を戻さない。
- 同一ファイルへ複数writerを置かない。未承認の並列化、破壊操作、配布、秘密操作をしない。
- 再作業、停止、再開は`POLICY.md`と`PROCESS_POLICY.md`を正本とする。

## Canonical references

- 共通規約: `POLICY.md`
- Extension: `EXTENSION_POLICY.md`
- 実装経路: `ROUTING_POLICY.md`
- 安全工程: `PROCESS_POLICY.md`
- エラー: `ERROR_POLICY.md` / `ERROR_CODES.md`
- 権限: `AUTHORITY_SEPARATION.md`
- 整合性: `INTEGRITY_POLICY.md`

終了コード、成果物、件数、SHA、test reportを証拠とし、成功ログだけで完了判定しない。
