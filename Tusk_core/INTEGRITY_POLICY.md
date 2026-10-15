# Integrity Policy

SHA-256は配布物の同一性確認に使い、通常開発の承認には使わない。

配布対象のテキストはリポジトリ直下の`.gitattributes`に従ってLFで保存・checkoutする。manifestはそのraw bytesから生成する。release検証は開発用作業コピーだけでなく、Gitから新規checkoutした配布構成でも実施する。検証時に改行を正規化して不一致を隠さない。

## 強制検証

- 初回導入
- update、repair、uninstall
- release・Installerビルド
- 読み取り専用Coreの変更検出

releaseではCoreと配布対象のmanifestを全件検証し、不一致が1件でもあれば停止する。

## 開発時

- ファイル編集ごとにmanifestを更新しない。
- 実装、レビュー、テスト合格後にmanifestを一度だけ再生成する。

## 配布時

- Core、runtime、配布対象を全件SHA検証する。
- manifest不一致時はビルド、導入、更新、起動を停止する。

Gitは開発差分と非常時rollbackの管理に使い、SHA認証とは分離する。独立Gitリポジトリ、baseline commit、分離可能な今回差分がない場合は自動rollbackしない。
