<!-- md-scope-document: TUSK_SZ -->
# Tusk SZ extension: agent entry

`Tusk_SZ` is the Siege-Zeke development gateway and product adapter. It owns
governed work-file discovery/access, environment and authentication bootstrap,
global/project/work-item routing, canonical synchronization, and the existing
layer-specific Simple Zeke and Illustrator orchestration.

Before acting, read `TUSK_SZ_SPEC.md`, `ERROR_CODES.md`, and the selected
product workspace's own `AGENTS.md` and `README.md`. Core workflow, evidence,
and synchronization rules remain in `../../AGENTS.md`, `../../GENERAL.md`,
`../../ERROR_CODES.md`, and `../../SYNC_POLICY.md`.

Product source is external and must be supplied with `--workspace`; never infer
it from this package's parent directory. Default CLI behavior is read-only
inspection. `--apply` is required for a real build, server, browser, COM, or
renderer process and requires a contained evidence directory.

Run the adapter through `tools/tusk_sz.py`. A successful unit test, dependency
probe, web build, HTTP readiness probe, or Illustrator export must not be
promoted to another layer. Final evidence always separates `renderer`, `ui`,
and `e2e`.

For any Siege-Zeke development task, read `GLOBAL.json`, then the registered
project parent's `PROJECT.json` and `PROGRESS.md`, then exactly one child work
item. Do not edit product files from a global request without this parent/child
contract. Use `skills/siege-zeke-bootstrap/` on a new PC or missing environment;
use `skills/siege-zeke-drive-sync/` for Drive inventory, staging, comparison,
pull, push, or verification. Read
`references/SIEGE_ZEKE_RULES_AND_TEXT_ANALYSIS.md` before rule or card-text work.

The producer display for this workspace/PC is `WKZ`. It is attribution only.
Credentials remain local and secret; their absence triggers local OAuth
bootstrap, never token copying.
