# Siege-Zeke rules and text-analysis handling

## Sources

The Tusk SZ managed rulebook is `../rulebook/siege-zeke-rulebook-current.md`.
Its registered source is
`D:\projects\txt-analyze\simple-zeke\docs\rules\siege-zeke-rulebook-current.md`.
The source audit establishes it as the current provisional anchor. A user's
explicit ruling outranks the anchor; older guides, DOCX exports, implementations,
and card-list inference are lower-priority supporting material.

The human Drive copy is a generated `★`-prefixed Markdown at the common
Siege-Zeke root. It is not accepted merely because it exists; its source and
generated hashes must match the global canonical map.

## TXT-ANALYZE order

Read `START-HERE.md`, `TXT-ANALYZE.md`, `TEXT-GRAMMAR.md`, project parent
`PROJECT.json`/`PROGRESS.md`, then the active child work item. Read only the
target card/ruling/runtime files needed by that child.

Keep these states separate:

- `ruled`: wording and behavior are decided.
- `parsed`: text compiles into the required intermediate data.
- `runtime`: game state behavior is connected and tested.
- `e2e`: the declared real board/UI scenario passed.
- `synced`: accepted artifacts were written and read back from Drive.

Compiler or unit success never proves runtime, UI, E2E, or sync. Ambiguous card
text returns to ruling; partial/manual parse cannot silently execute. Preserve
specific user rulings in card text, ruling records, IR, tests, and runtime.
