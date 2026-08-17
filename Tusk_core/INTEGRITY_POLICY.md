<!-- md-scope-document: COMMON -->
# Integrity Policy

SHA-256は配布物の同一性確認に使い、通常開発の承認には使わない。

## 強制検証

- 初回導入
- update、repair、uninstall
- release・Installerビルド
- 読み取り専用Coreの変更検出
- 拡張の追加、交換、更新、有効化

releaseではCoreと有効化対象拡張のmanifestを全件検証し、不一致が1件でもあれば停止する。

## 開発権限

workspace直下の`developer.key.json`を初回だけtrust登録する。登録時にキーのSHA-256とworkspace絶対パスをPC側の`%LOCALAPPDATA%/Tusk/trusted_developer_keys.json`へ保存する。

以降、次を全て満たす場合だけ開発中のmanifest不一致を警告扱いにできる。

- modeが`development`
- `developer.key.json`のSHA-256が登録値と一致
- workspace絶対パスが登録値と一致
- 対象がキーの`allowed_scopes`内
- release、Installer、配布検証ではない

キーJSON、workspace、scopeのいずれかが変わった場合は権限を失効し、再trustを要求する。環境変数だけで権限を有効化しない。

## 開発時

- manifest不一致は変更一覧を表示して続行できる。
- ファイル編集ごとにmanifestを更新しない。
- 実装、レビュー、テスト合格後にmanifestを一度だけ再生成する。
- runtime、外部依存物、workspace外、秘密情報、破壊操作は開発権限の対象外とする。
- 開発権限が有効でもrelease成果物は生成できない。

## 配布時

- 開発権限を無視する。
- Core、runtime、有効化した拡張を全件SHA検証する。
- `developer.key.json`とPC側trust storeを配布物へ含めない。
- manifest不一致時はビルド、導入、更新、起動を停止する。

Gitは開発差分と非常時rollbackの管理に使い、SHA認証とは分離する。独立Gitリポジトリ、baseline commit、分離可能な今回差分がない場合は自動rollbackしない。
