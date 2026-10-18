# Tusk Core error registry

This is the canonical parser-readable registry. `F` stops the guarded run; `M` records a non-fatal issue. `F182` is reserved for an interactive user stop and must be created by the outer execution mechanism, not forged in a log.

### 強制停止

| Code | Name | Condition |
|---|---|---|
| F026 | pipeline_fatal | Producer explicitly stopped the run. |
| F042 | path_safety_failure | A guarded path escaped its boundary. |
| F120 | contract_invalid | Required test contract is invalid. |
| F121 | artifact_invalid | Required output artifact is invalid. |
| F122 | completion_invalid | Done declaration is invalid. |
| F123 | minor_threshold_exceeded | Minor issue threshold reached. |
| F182 | user_requested_stop | Interactive user stop only. |
| F999 | core_reject | Core rejected an operation; `reason` is `core_reject_<ContractError string>`. |

### 軽度問題

| Code | Name | Condition |
|---|---|---|
| M020 | recoverable_issue | A recoverable task issue occurred. |
| M021 | retry_scheduled | A bounded retry was scheduled. |
| M040 | input_warning | Input is usable with a warning. |
| M041 | output_warning | Output needs review. |
| M060 | data_warning | Data requires review. |
| M061 | id_warning | Identifier requires review. |
| M120 | review_needed | Human or independent review is needed. |
| M141 | cache_conflict | Cache conflict requires review. |
| M180 | user_attention | User attention is needed without stopping. |
