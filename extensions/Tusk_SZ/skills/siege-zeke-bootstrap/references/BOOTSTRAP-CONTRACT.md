# Bootstrap contract

- Inspection checks Core/SZ roots, the registered project, producer display,
  workspace identity, required portable files, runtimes, and authentication
  presence.
- `ready` means the declared prerequisites exist. It does not prove parsing,
  runtime, renderer, UI, E2E, or Drive synchronization.
- Apply may copy only a missing required-data item whose source SHA-256 matches
  the project manifest and whose destination is strictly below the workspace.
- Existing destinations are never overwritten by bootstrap.
- Reports redact values following `token`, `secret`, `password`, or
  `authorization`; credential files are represented only by a safe locator and
  boolean presence.
