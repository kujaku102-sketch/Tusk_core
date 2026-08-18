# Authentication handoff

- Producer display on this workspace/PC: `WKZ`.
- Provider: Google OAuth for Drive operations.
- Required scope for synchronization: `https://www.googleapis.com/auth/drive`.
- Preferred credential locator on this PC: `D:\google_integration\token.json`.
- The locator is configuration, not portable project data.

If the credential is absent, authorize on the current PC using an approved
OAuth client and save the resulting token only at the local credential locator.
Confirm Drive list/read access before enabling writes. Do not paste, log, hash,
upload, package, or hand off `token.json`, `credentials.json`, access tokens,
refresh tokens, client secrets, or bearer URLs. A new PC creates its own local
authorization; it does not receive WKZ's token file.
