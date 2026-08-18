<!-- md-scope-document: TUSK_SZ -->
# Tusk SZ error registry

These program-specific codes occupy the Core-approved `200-299` range.

## Force stop

| Code | Name | Condition |
|---|---|---|
| `F200` | `WORKSPACE_IDENTITY_INVALID` | Explicit workspace is missing or fails the selected profile identity. |
| `F201` | `DEPENDENCY_MISSING` | A required executable/module is absent or its bounded runtime import probe fails or times out. |
| `F202` | `EVIDENCE_PATH_INVALID` | Apply evidence is absent, equal to its root, or escapes its root. |
| `F203` | `EXECUTION_TIMEOUT` | A build, server readiness wait, browser scenario, or product renderer exceeds its bound. |
| `F204` | `ILLUSTRATOR_TEMPLATE_MISSING` | `illustrator/templates/card_v1.ai` is absent. |
| `F205` | `PROCESS_START_FAILED` | A required child process cannot be started. |
| `F206` | `RENDERER_FAILED` | Build or product renderer does not satisfy its artifact contract. |
| `F207` | `UI_FAILED` | The real browser UI assertions fail. |
| `F208` | `E2E_FAILED` | The existing interactive scenario or complete Illustrator chain fails. |
| `F209` | `RESULT_CONTRACT_INVALID` | Product or Tusk SZ result JSON is malformed or lacks required evidence. |
| `F210` | `CLEANUP_FAILED` | A process tree created by Tusk SZ cannot be confirmed stopped. |
| `F220` | `BOOTSTRAP_STAGE_INVALID` | Bootstrap apply lacks a valid contained stage. |
| `F221` | `BOOTSTRAP_DESTINATION_ESCAPE` | Required-data destination escapes the explicit workspace. |
| `F222` | `BOOTSTRAP_SOURCE_MISSING` | Required staged source is missing or outside the stage. |
| `F223` | `BOOTSTRAP_SOURCE_HASH_MISMATCH` | Required staged source hash differs from the parent manifest. |
| `F224` | `AUTHORITY_CHAIN_INVALID` | Global/project/child identity, running state, or allowed path does not authorize apply. |
| `F225` | `SYNC_STAGE_INVALID` | Synchronization staging is outside approved roots. |
| `F226` | `SYNC_PATH_ESCAPE` | A canonical-map path escapes the workspace or stage. |
| `SYNC-409` | `SYNC_CONFLICT` | Local/remote/baseline conflict or Drive identity/parent/duplicate ambiguity. |

## Minor issue

| Code | Name | Condition |
|---|---|---|
| `M200` | `RUNTIME_FALLBACK_USED` | Runtime resolution used PATH or a documented fallback after no explicit selection. |
| `M201` | `OPTIONAL_PREREQUISITE_MISSING` | An optional tool is absent and the selected mode can continue accurately. |
| `M202` | `LAYER_NOT_RUN` | A layer is intentionally not run and is reported without promotion. |
