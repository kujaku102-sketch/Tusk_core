---
name: siege-zeke-bootstrap
description: Detect and prepare a governed Siege-Zeke development environment, including Tusk Core/SZ installation, explicit project registration, portable required data, Google authentication availability, and a non-secret producer display. Use when starting or handing off any Siege-Zeke project on a new PC or agent, when required project data may be missing, or when local Drive authentication must be created without copying tokens.
---

# Siege-Zeke bootstrap

1. Read `../../../AGENTS.md`, `../../../TUSK_SZ_SPEC.md`, then the selected
   project parent's `PROJECT.json` and `PROGRESS.md`.
2. Require explicit `--workspace` and `--project`. Never infer either from this
   skill's parent path.
3. Run `scripts/siege_zeke_bootstrap.py` without `--apply` first. Treat the JSON
   report as inspection evidence, not product readiness.
4. If required portable data is missing, use only the source and hash declared
   by the project `REQUIRED-DATA.json`. Apply needs a contained staging source
   and writes only declared destinations.
5. If Google authentication is missing, read
   `references/AUTHENTICATION.md`. Create credentials locally on that PC; never
   copy token or client-secret bytes into Tusk SZ, Drive, evidence, or chat.
6. Record only `{ "producer": "WKZ" }` for this environment. Producer display
   is attribution, not authorization.
7. Stop if the project parent, required data, source hash, credential locator,
   or destination containment is ambiguous.

Read `references/BOOTSTRAP-CONTRACT.md` for the report and apply contract.
