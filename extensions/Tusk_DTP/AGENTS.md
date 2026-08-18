<!-- md-scope-document: IDTASK -->
# Tusk DTP extension: agent entry

This is the DTP / IdTask adapter. It owns adapter vocabulary, product rules,
and only product cache it explicitly validates. Core does not own those
contracts.

Before acting validate `EXTENSION-MANIFEST.json`, follow its
`required_read_order`, then read the target product entry, current Spec, Git
diff, and validated Context Cache when one is required.
Use Core workflow, evidence, guard,
and sync rules through `../../AGENTS.md`, `../../GENERAL.md`,
`../../ERROR_CODES.md`, and `../../SYNC_POLICY.md`.

This extension is installed as a packaging boundary only. Product source may be
absent, and historical context/focus cache is `needs_review` until source
identity, spec binding, hash, and relevant tests are verified. Do not claim
DTP runtime, renderer, UI, or E2E success from these files' presence.

Legacy `IDTASK_*` markers and IdTask-specific scripts belong here. New generic
process controls use Core `TUSK_*` markers. Keep adapter assets under this
extension (`tools/`, `work/`, and product folders), never in Core runtime.

Effective scope is derived at runtime from the activated extension, explicit
product workspace, current task and Spec, Git diff, and validated Context
Cache. Do not load archive, release, build, dist, vendor, `_internal`, Stock,
or temporary output unless the current Spec explicitly requires it.
