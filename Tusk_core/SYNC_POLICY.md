<!-- md-scope-document: COMMON -->
# Tusk Core sync policy

Google Drive is a collaboration transport, not a distributed lock. Work from a
local synced copy or checkout; Core tools require a local path, never a Drive URL.

## Single writer

Name one writer for each Git-scoped task before edits. Other agents may inspect,
review, or test artifacts read-only but do not write the same tracked files.
The writer attaches start/final recursive manifests and SHA-256 evidence.

## Handoff

1. Stop writes and capture the manifest and relevant hashes.
2. Wait for Drive sync, then inspect expected paths locally and remotely.
3. The next writer compares the received manifest with its baseline before edits.
4. After work, repeat the capture and store the evidence with the Git change or
   failure record.

## SYNC-409

If both sides changed the same logical artifact, required identity/hash differs,
parentage is ambiguous, or duplicate names make a path uncertain: preserve both
candidates and their manifests, do not auto-merge/delete/trash/select a newer
timestamp, transition to `waiting_human`, and request a human resolution.

Multi-writer use is prohibited until an intentional Drive/local conflict test
documents safe behavior for the actual sync client and tools.
