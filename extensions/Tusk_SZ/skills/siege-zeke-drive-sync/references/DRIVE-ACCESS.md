# Drive access contract

Common Siege-Zeke root: `1yLQKxHxHjktl7frBAVZ-Vh7Sjm18G-T3`.

Tusk SZ may list the root and direct children. Deeper access requires a project
parent mapping or an approved child work item. `canonical_source` is read-only
unless the child owns its update; `working` is limited to child allowed paths;
`generated` needs declared validation; `asset` and `archive` are read-only by
default; `transport` is never canonical by existence; `secret` is forbidden.

No operation may delete, trash, change sharing, broadly move, create a duplicate
canonical name, select authority by timestamp, or merge concurrent changes.
