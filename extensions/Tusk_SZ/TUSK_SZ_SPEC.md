<!-- md-scope-document: TUSK_SZ -->
# Tusk SZ execution and evidence contract

## Boundary

Tusk SZ is the shared Siege-Zeke development gateway. Global configuration owns
Drive root access, bootstrap, rulebook packaging, producer display, and project
registry. Each project parent owns architecture, canonical/sync mapping,
required portable data, progress, and child index. Each work-item child owns one
approved implementation or synchronization unit. Product edits require all
three levels to resolve.

Tusk SZ orchestrates existing product commands; it does not silently rewrite
the game, card rules, Vite application, Playwright scenario, Illustrator JSX,
or template. Product files remain governed by their workspace and active child.

Common Drive root is `1yLQKxHxHjktl7frBAVZ-Vh7Sjm18G-T3`. Global access is
direct-child inventory only. Deeper reads/writes need a project canonical map.
Use staged three-way comparison and fixed-ID readback. `SYNC-409` forbids
automatic conflict resolution.

Authentication is a bootstrap prerequisite. Tusk SZ records provider, scope,
safe local locator, presence, and reauthorization instructions only. It never
packages credential contents. Producer is the non-secret display `WKZ`.

Supported profiles:

| Profile | Exact identity | Renderer | UI | E2E |
|---|---|---|---|---|
| `web` | `package.json` name `simple-zeke`, required scripts and files | Vite production build | live browser assertions from the existing smoke scenario | existing interactive tutorial/deck scenario |
| `illustrator` | Siege-Zeke package and C-03 orchestrator/layout | existing `render_card.ps1` plus result JSON/PNG contract | `not_applicable` | complete orchestrator-to-PNG result |

## CLI

```powershell
python tools/tusk_sz.py --profile web --workspace D:\path\simple-zeke
python tools/tusk_sz.py --profile illustrator --workspace D:\path\siege-zeke
python tools/tusk_sz.py --profile web --workspace D:\path\simple-zeke `
  --evidence-dir <workspace-root>\work\runs\<RUN-ID>\web --apply
```

Inspection is the default. A real run requires both `--apply` and
`--evidence-dir`. Unless `--evidence-root` is explicit, evidence must be a
strict descendant of Core `work/runs`. Relative paths are resolved before the
containment check; equality with the root and traversal outside it are rejected.

Web inspection is read-only but not path-only: it starts bounded Node probe
processes that actually import the resolved Vite API and the Playwright module.
Each probe has a positive `--probe-timeout` (default 10 seconds), captures no
product output file, and records sanitized exit/timeout/detail metadata. A Vite
import failure blocks renderer, UI, and E2E with `F201`. A Playwright import
failure leaves renderer `ready` but blocks UI and E2E with `F201`. File presence
alone never produces `ready`.

Runtime resolution order is explicit CLI argument, profile environment
variable, `PATH`, then documented platform fallbacks. Reports record the
selected path and origin without exposing environment values.

## Web execution

1. Verify product identity and run bounded Vite/Playwright ESM import probes.
2. Run the existing Vite build with a fixed timeout. This can prove only the
   renderer layer.
3. Refuse an occupied port, start the existing static server in a new process
   group, and wait for a bounded HTTP readiness probe.
4. Run the existing Playwright smoke scenario with a fixed timeout.
5. Treat its tab assertions as UI evidence and its interaction-flow assertions
   as E2E evidence. Both reference the same raw browser log but have separate
   criteria in the result.
6. Stop only the server process tree created by this run and record cleanup.

An HTTP 200 response alone is not UI success. A build or Node unit test is not
UI/E2E success.

## Illustrator execution

Inspection verifies workspace identity, PowerShell, orchestrator, JSX, Python
package, and `illustrator/templates/card_v1.ai`. A missing template emits
`F204`, sets renderer and E2E to `blocked`, keeps UI `not_applicable`, and never
claims a PNG.

With `--apply`, `--card-id` is mandatory and must match the safe normalized
ASCII form `[A-Z][A-Z0-9]{0,15}-[0-9]{1,6}`. The adapter invokes the existing
PowerShell orchestrator with a bounded timeout. Renderer success requires an
exit code of zero, a valid product result JSON with `ok: true`, and a non-empty
PNG strictly below `<workspace>/build/output/` with a `.png` suffix and valid
PNG signature. Relative product output paths resolve against the workspace;
outside paths and arbitrary files are rejected. E2E success requires the same
complete chain. `--audit-only` may
prove a template audit but leaves E2E `not_run`; it does not prove PNG output.

## Result states and markers

Layer states are `passed`, `failed`, `blocked`, `ready`, `not_run`, and
`not_applicable`. The final atomic UTF-8 JSON follows
`schemas/tusk_sz_result.schema.json` and contains exact commands, dependencies,
identity checks, evidence paths, cleanup, and layer details.

New output uses only:

```text
[TUSK_PROGRESS] run_id=... component=tusk_sz step=...
[TUSK_MINOR_ISSUE] code=M2xx program_id=TUSK_SZ run_id=... component=tusk_sz step=... target=... detail=...
[TUSK_FORCE_STOP] code=F2xx program_id=TUSK_SZ run_id=... component=tusk_sz step=... reason=...
```
