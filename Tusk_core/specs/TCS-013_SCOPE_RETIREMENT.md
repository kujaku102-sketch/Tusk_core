<!-- md-scope-document: COMMON -->
# TCS-013 Scope Authority Retirement

## Status

COMPLETED

## Requirement

独立したMarkdown Scope Authorityを廃止し、作業対象を選択済みExtension、現在のtaskとSpec、Git diff、検証済みContext Cacheから実行時に導出する。Coreとworkspaceの`AGENTS.md`は詳細仕様を再掲せず、正本を選ぶブートローダーとする。

## Changes

- `markdown_scope`を`AUTHORITY-MAP.json`から削除した。
- `MD_SCOPE_RULES.md`を配布manifestから外し、archiveへ退役した。
- DTP/SZ Extension manifestへ`runtime_scope`契約を追加した。
- DTPの旧`Work Packet`参照を現行Spec、Git diff、Context Cacheへ置換した。
- Core/root `AGENTS.md`を入口、境界、禁止事項、正本参照へ縮小した。
- Sharpenerへ退役Scope、旧Work Packet、Extension runtime scopeの監査を追加した。

既存`md-scope-document`コメントは互換情報として残すが、Authorityや入力判定には使用しない。

## Verification

- DTP/SZ manifest release integrity: pass
- Sharpener focused tests: 9/9 pass
- Core focused tests: 10/10 pass
- Core full tests: 102/102 pass
- Core release integrity: pass
- Sharpener Core audit: healthy, issues 0

