---
name: siege-zeke-drive-sync
description: Inventory, stage, compare, pull, push, and verify registered Siege-Zeke Drive artifacts using fixed IDs and conflict-safe three-way comparison. Use for any Tusk_SZ project synchronization, including TXT-ANALYZE canonical files, rulebook Markdown, project handoff packages, or Drive/local checkpoint reconciliation.
---

# Siege-Zeke Drive synchronization

1. Read `../../../AGENTS.md`, `../../../TUSK_SZ_SPEC.md`, the project
   `PROJECT.json`, `CANONICAL-MAP.json`, and active child specification.
2. Require explicit local workspace, project parent, run staging directory, and
   operation. Default to `inventory`/`compare`; never write during discovery.
3. Ground the Siege-Zeke root ID `1yLQKxHxHjktl7frBAVZ-Vh7Sjm18G-T3`, then
   validate each configured fixed file ID and parent before transfer.
4. Pull remote bytes into the contained run stage. Never download directly over
   a working file.
5. The agent uses the installed Drive connector to inventory, download to stage,
   update fixed IDs, and read back bytes. The bundled script is deliberately
   local-only: use `scripts/siege_zeke_sync.py compare` for staged
   local/remote/baseline decisions and `apply-local` for approved replacement.
   If both sides changed, IDs/parents differ, or names duplicate, preserve both
   and stop `SYNC-409`.
6. Local apply uses atomic replacement only for approved mapped paths. The
   script does not implement Drive push. The agent must update existing fixed
   IDs through the connector and fetch each file again for byte verification.
7. Update the accepted checkpoint after byte-for-byte verification, never after
   an upload request alone.

Read `references/DRIVE-ACCESS.md` for classifications and forbidden operations.
