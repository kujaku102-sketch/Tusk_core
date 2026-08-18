<!-- md-scope-document: TUSK_WORKSPACE_MIGRATOR -->
# Tusk Workspace Migrator: agent entry

This extension stages legacy Tusk extension assets for review under the current
workspace. It never patches Core, activates an extension, deletes a legacy
file, or treats historical evidence as current success evidence.

Before acting, read `WORKSPACE_MIGRATOR_SPEC.md` and `ERROR_CODES.md`. Default
behavior is read-only `inspect`. A write requires the explicit `stage` action
and `--apply`; writes are restricted to
`<workspace>/work/migrations/<migration-id>/`.

The legacy root is input only. Do not infer it from the current workspace, and
do not follow symlinks, junctions, reparse points, or paths outside the selected
legacy extension. Staged extensions remain inactive until their generated
manifest is reviewed and the Core extension manager enables them separately.
