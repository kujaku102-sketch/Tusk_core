<!-- md-scope-document: TUSK_WORKSPACE_MIGRATOR -->
# Workspace Migrator error codes

| Code | Meaning |
|---|---|
| `TUSK_MIGRATION_INVALID_ROOT` | legacy rootまたはworkspaceが不正、同一、または必要構造を欠く |
| `TUSK_MIGRATION_INVALID_ID` | migration IDが空、危険、または許可文字外 |
| `TUSK_MIGRATION_INVALID_EXTENSION` | Extension名、入口、または選択対象が不正 |
| `TUSK_MIGRATION_UNSAFE_PATH` | workspace外、symlink、junction、reparse pointを検出 |
| `TUSK_MIGRATION_DESTINATION_EXISTS` | migration IDまたはstage先が既に存在する |
| `TUSK_MIGRATION_WRITE_REQUIRES_APPLY` | stage書込に`--apply`がない |
