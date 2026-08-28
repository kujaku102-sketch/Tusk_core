# Scope Authority Retirement

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-013 Scope Authority Retirement`
- Legacy filename: `specs/TCS-013_SCOPE_RETIREMENT.md`

## Purpose and Requirement

独立したMarkdown Scope Authorityを退役させ、作業対象を選択済みExtension、現在のtaskとSpec、Git diff、検証済みContext Cacheから実行時に導出する。Coreとworkspaceの`AGENTS.md`は正本を選ぶbootloaderとする。

## Authority references

- workspace/Coreのload orderとboundary: 各`AGENTS.md`
- Authority登録: `AUTHORITY-MAP.json`
- Extension runtime scope: 検証済み各Extension manifest
- 退役契約の監査: Sharpenerの現行監査規則

## Scope and Outcome

`markdown_scope`をAuthority mapから削除し、`MD_SCOPE_RULES.md`を配布manifestから外してarchiveへ移し、DTP/SZ Extensionへ`runtime_scope`契約を追加した。DTPの旧Work Packet参照を現行Spec、Git diff、Context Cacheへ置換し、Core/root `AGENTS.md`を入口と境界へ縮約した。既存`md-scope-document`コメントは互換情報として残すが、Authorityや入力判定に使用しない。

## Acceptance

退役Scopeや旧Work PacketがAuthorityとして復活せず、Extension runtime scopeとbootloader境界が現行監査で検証可能であることを確認する。

## History

- 2026-08-17: Scope Authority退役を実装した。
- Verification record: DTP/SZ manifest release integrity pass、Sharpener focused 9/9、Core focused 10/10、Core full 102/102、Core release integrity pass、Sharpener Core audit healthy・issues 0。
- 2026-08-21: legacy identityを保持してnumberless Specへ移行した。

## Non-authority boundary

本Specは退役結果と検証履歴を記録する。新しいScope Authority、Work Packet、固定scope schemaを作らず、`AGENTS.md`やExtension manifestの現行境界を上書きしない。
