# Core Orchestration Evidence Specification

## Status

状態: `ACTIVE`

本Specはschema v3 Core共通契約の現行実装targetを記録する。テスト通過や運用完了は別の実行証拠なしに主張しない。

## Provenance

抽出元は旧`specs/TCS-014_SEVEN_STAGE_ORCHESTRATION.md`、`specs/TCS-015_ROOT_REMEDIATION_ORCHESTRATION.md`、`specs/TCS-016_GOVERNANCE_BOOTSTRAP_RECOVERY.md`である。旧Specのtask固有recovery値や一時的な実装境界はactive contractへ継承しない。

## Purpose and Requirement

Core orchestrationのstage・role境界と、その実行証拠をSingle Authority Principleに従って既存Authority、Tool、Testへ接続する。Specは採用済みのcross-record validation、evidence freshness、test entry gateだけを記録し、機械schemaを複製しない。

## Authority references

- 七stageの順序、role分離、binding、handoff shape: `AUTHORITY_SEPARATION.md`
- setup、state、identity、evidence admission、freshness、recovery: `PROCESS_POLICY.md`
- pre/post-skimの読取・提出責務: `ROUTING_POLICY.md`
- test entry gateとcomponent-root selector contract: `TEST_POLICY.md`
- focused mapping: `TEST-MAP.json`
- evidence path/serialization safety: `tools/orchestration_evidence_common.py`
- commander-controlled writer: `tools/orchestration_evidence_log.py`
- accepted cross-record validation: `tools/orchestration_evidence_validator.py`
- receipt再検証とguard順序: `tools/test_guard_monitor.py`
- Single Authority Principle: `GENERAL.md`と`AUTHORITY-MAP.json`

## Adopted orchestration contract

採用されたstage順序は`pre_skim → design → commander_window → implementation → post_skim → final_review → design_receipt`である。roleの兼任禁止と例外、binding、handoff shapeは`AUTHORITY_SEPARATION.md`だけを正本とする。test entry gateは七stageの外にあり、第八stage、role、handoff edgeとして扱わない。

各意味は1つの既存AuthorityまたはToolだけが所有する。別Spec、fixture、receiptは参照を保持できるが、同じ機械規則を再定義しない。

## Adopted evidence semantics

validator v3はtrusted streamのうちaccepted recordだけをcross-record indexへ入れ、rejected recordはfindingとして保持する。approval/attemptとgeneration-scoped recordを別composite keyで管理し、CLI指定work・attemptの現行generationを選ぶ。`pre_skim | design | commander_window | implementation | post_skim | final_review | design_receipt | test_gate`の八checkpointを実際の累積prefixとして検証し、later-stage不備は要求prefixから隔離する一方、stream integrity、scope escape、generation gap/supersessionは常にblockingとする。より高いgenerationのrecovery開始後に旧receiptへfallbackしない。

post-skimは候補local findingsがblockingでないlatest-validだけが後続consumerへ進む。invalid finding自体はstream全体ではnonblockingであり、invalidまたはrejected candidateはlatest-validを進めず、後続のvalid candidateは直前latest-validを正しくsupersedeする。各generationのstage evidenceは`handoff_i < transition_i < handoff_(i+1)`とterminalまでsequenceで交互化し、UTCを後退させない。setup、binding-stage、implementation result、非post edge、terminalはsingleton、post候補は対応transitionまで複数可、state transition IDはattempt-global singletonである。result、scope、events、sequenceまたはconsumer参照が変化したreceiptはstaleであり、再利用しない。同一identityと同一canonical payloadのreplayはcollapseし、同一identityの異payloadはconflictとして拒否する。

test selectorは`TEST-MAP.json`と`tests/`を直下に持つcomponent rootを基準にし、changed pathはそのcomponent root相対で解決する。workspace相対snapshot pathをselector pathとして暗黙転用しない。

## Writer, path safety, and full-payload principle

evidence writerは承認済みcommander-controlled recorderであり、approvalを推測しない。accepted/rejected envelopeを同じappend-only streamへ記録し、semantic admissionはvalidatorの共有`validate_submission`だけへ委譲する。canonical JSON、payload SHA、hashed work path、workspace相対path、nearest-existing-ancestorの`lstat`、symlink/reparse/junction拒否、root containment、TOCTOU再照合はshared path-safety primitiveを使う。

hash、ID、receipt、summaryは完全payloadの代替ではない。identityとreceiptは`sha256-path-snapshot-v1`のfull canonical snapshot payloadを保持し、path順、file/absent state、file SHA、sizeまでexactに検証する。generation N>0のbaseline promotionは直前R payloadを新Bへ完全一致で昇格する。

## Guard and test entry

guardは製品registry読込、lock取得、process照会、selector実行、製品起動より前にvalidatorを`attempt_id`と`target: test_gate`で再実行する。test contractはworkspace、work、attempt、target、full validation receipt、receipt SHAのexact field setを持つ。embedded receiptとactual receiptのcanonical bytesおよび両SHAが完全一致する場合だけgateを開き、partial、hash-only、R-ID-only、extra、mutationを拒否する。

## Explicit exclusions

本Specは固定work ID、固定approval ID、固定generation、固定history count、固定remediation depth、固定attempt indexをCore共通宣言として採用しない。root-remediation、one-shot recovery、固定`MAX/P3`宣言も採用しない。revisionまたはretryの一律禁止をCore共通orchestration contractへ持ち込まない。これらは旧task固有provenanceであり、必要な場合は現行task、Process Authority、明示承認から導出する。

## Scope and Outcome

対象はCore共通のorchestration evidence contractと、その既存Authority・Tool・Testへの参照である。旧抽出sourceへのactive依存を除去し、採用済み意味をnumberless Specから辿れる状態にする。

## Acceptance

active dependencyが本Specと参照Authorityへ解決され、writer・validator・guardの実装契約がschema v3、generic generation recovery、八checkpoint、full payload、latest-valid、stale、replay、conflict、full receipt再検証を保持していることを静的に確認する。動的テスト結果はこの記述から推定しない。

## History

- 2026-08-21: 旧抽出sourceから採用済みCore共通契約を抽出した。
- 2026-08-21: schema v3のgeneric generation model、八checkpoint、full validation receiptを現行実装targetへ更新した。

## Non-authority boundary

本Specは機械schema、task固有approval、recovery ledger、Process state、test selector実装を定義しない。参照先AuthorityとToolが不一致の場合は推測で統合せず`needs_review`とする。
