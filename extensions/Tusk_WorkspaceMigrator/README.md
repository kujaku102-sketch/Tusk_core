# Tusk Workspace Migrator

旧Tusk Core内のExtension静的資産を、新Workspaceのレビュー用領域へ隔離して
stageする一回限りの移行Extension。

旧Core、旧`work/`、現行Core、active `extensions/`は変更しない。

```powershell
py -3 tools/workspace_migrator.py inspect `
  --legacy-root D:\Tusk_core `
  --workspace D:\Tusk_workspace

py -3 tools/workspace_migrator.py stage `
  --legacy-root D:\Tusk_core `
  --workspace D:\Tusk_workspace `
  --migration-id MIG-20260819-001 `
  --extension Tusk_DTP `
  --extension Tusk_SZ `
  --apply
```

stage先は`D:\Tusk_workspace\work\migrations\MIG-20260819-001\`。生成した
manifestと除外一覧をレビューしてから、別操作でactive `extensions/`へ導入する。
