<!-- md-scope-document: COMMON -->
# Tusk Core error registry

This is the canonical parser-readable registry. `F` stops the guarded run; `M` records a non-fatal issue. `F182` is reserved for an interactive user stop and must be created by the guard console, not forged in a log.

### 強制停止

| Code | Name | Condition |
|---|---|---|
| F020 | supervisor_lost | Required supervisor disappeared. |
| F021 | progress_stalled | No valid progress within the fixed interval. |
| F022 | repeated_issue | Repetition threshold reached. |
| F023 | process_identity_mismatch | Registered process identity changed. |
| F024 | process_stop_incomplete | Guard could not stop registered process. |
| F025 | process_registry_invalid | Process registry is invalid. |
| F026 | pipeline_fatal | Producer explicitly stopped the run. |
| F080 | translation_fatal | Adapter translation failed fatally. |
| F042 | path_safety_failure | A guarded path escaped its boundary. |
| F120 | contract_invalid | Required test contract is invalid. |
| F121 | artifact_invalid | Required output artifact is invalid. |
| F122 | completion_invalid | Done declaration is invalid. |
| F123 | minor_threshold_exceeded | Minor issue threshold reached. |
| F124 | monitor_integrity_failure | Monitor integrity check failed. |
| F182 | user_requested_stop | Interactive user stop only. |

### 軽度問題

| Code | Name | Condition |
|---|---|---|
| M020 | recoverable_issue | A recoverable task issue occurred. |
| M021 | retry_scheduled | A bounded retry was scheduled. |
| M040 | input_warning | Input is usable with a warning. |
| M041 | output_warning | Output needs review. |
| M060 | data_warning | Data requires review. |
| M061 | id_warning | Identifier requires review. |
| M080 | translation_warning | Translation was skipped or degraded. |
| M100 | style_fallback | Adapter used an approved fallback. |
| M120 | review_needed | Human or independent review is needed. |
| M141 | cache_conflict | Cache conflict requires review. |
| M180 | user_attention | User attention is needed without stopping. |

## 7. 既存コード互換表

| Legacy | Code |
|---|---|
| STALL_30M | F021 |
| LOOP_DETECTED | F022 |
| PROCESS_LOST | F020 |
| PIPELINE_FATAL | F026 |
| ARTIFACT_INVALID | F121 |
| TRANSLATION_FATAL | F080 |
| TRANSLATION_SKIP | M080 |
| CACHE_CONFLICT | M141 |
| STYLE_FALLBACK | M100 |
| REVIEW_NEEDED | M120 |
