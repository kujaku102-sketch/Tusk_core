<!-- md-scope-document: COMMON -->
# Sharpener Specification

## 境界

SharpenerはTusk Coreの通常実装ルートから独立する。Coreは`healthy`または明示的なwaiverだけを受理する。

## コマンド

- `check`: 読み取り専用監査。明示した`--output`だけは監査結果として生成できる。
- `repair`: `SHARPENER-CHECKS.json`で自動修復可能な操作だけを明示指定で実行する。
- `report`: 保存済み監査結果から、人間判断が必要な問題を抽出する。

## 初版監査

1. `reference_consistency`: AUTHORITY-MAPの正本・redirect実在性、退役済みScope AuthorityとWork Packet参照、Extensionのruntime scope契約。
2. `authority_conflicts`: concept、canonical、redirectの重複所有。
3. `manifest_catalog`: 配布manifestのpath/SHAとextension catalogの構造。
4. `error_codes`: F/Mコードと名称の重複、書式不正。
5. `test_map`: test path実在性、pattern/test重複。
6. `cache_freshness`: cache indexが存在する場合のSHA/mtime整合性と期限超過。

## 修復境界

初版で許可するのは`manifest_hashes`だけ。既存行・既存通常ファイルのSHA-256を原子的に更新する。欠落、重複、絶対path、親参照、symlink/reparseを検出した場合は変更しない。authority、policy、Spec、catalog、ERROR_CODES、TEST-MAPは自動修復しない。
