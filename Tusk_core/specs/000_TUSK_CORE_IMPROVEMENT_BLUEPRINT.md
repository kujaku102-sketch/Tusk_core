# Tusk Core改善Spec設計図

## 状態

- `SUPERSEDED_BY_INDIVIDUAL_SPECS`
- 本文はSpec分割前の設計図とmigration provenanceであり、現行Authorityまたは個別Specを上書きしない。
- IdTask固有機能は対象外。

## 情報源

- 共有会話: `https://chatgpt.com/share/6a80c392-8284-83e8-83c2-18e7dc57dd0b`
- 現行Authority: `GENERAL.md`、`ROUTING_POLICY.md`、`PROCESS_POLICY.md`、`TEST_POLICY.md`、`ERROR_POLICY.md`、`AUTHORITY_SEPARATION.md`、`AUTHORITY-MAP.json`

## Active individual specifications

- `specs/CORE_ROUTING_BASELINE.md`
- `specs/RISK_EVIDENCE.md`
- `specs/PROPOSAL_AUTHORITY_AND_SAFETY_APPEAL.md`
- `specs/PROCESS_POLICY_CONSOLIDATION.md`
- `specs/ROUTING_POLICY_CONSOLIDATION.md`
- `specs/TEST_POLICY_CONSOLIDATION.md`
- `specs/ERROR_POLICY_CONSOLIDATION.md`
- `specs/ENTRY_DOCUMENT_RESPONSIBILITY.md`
- `specs/DISTRIBUTION_MANIFEST_SYNCHRONIZATION.md`
- `specs/SINGLE_AUTHORITY_AND_CREATION_GATE.md`
- `specs/INCUBATION_QUEUE.md`
- `specs/SCOPE_AUTHORITY_RETIREMENT.md`
- `specs/CORE_ORCHESTRATION_EVIDENCE_SPEC.md`

## Legacy identity table

| Legacy heading | Legacy filename | Current disposition |
|---|---|---|
| `TCS-001 Core Routing Baseline` | `specs/TCS-001_CORE_ROUTING_BASELINE.md` | `specs/CORE_ROUTING_BASELINE.md` |
| `TCS-002 Extension Knowledge` | `specs/TCS-002_EXTENSION_KNOWLEDGE.md` | `archive/retired/TCS-002_EXTENSION_KNOWLEDGE.md` (`FROZEN`) |
| `TCS-003 Risk Evidence` | `specs/TCS-003_RISK_EVIDENCE.md` | `specs/RISK_EVIDENCE.md` |
| `TCS-004 Proposal Authority and Safety Appeal` | `specs/TCS-004_PROPOSAL_AUTHORITY.md` | `specs/PROPOSAL_AUTHORITY_AND_SAFETY_APPEAL.md` |
| `TCS-005 Process Policy Consolidation` | `specs/TCS-005_PROCESS_POLICY.md` | `specs/PROCESS_POLICY_CONSOLIDATION.md` |
| `TCS-006 Routing Policy Consolidation` | `specs/TCS-006_ROUTING_POLICY.md` | `specs/ROUTING_POLICY_CONSOLIDATION.md` |
| `TCS-007: Test Policy consolidation` | `specs/TCS-007_TEST_POLICY.md` | `specs/TEST_POLICY_CONSOLIDATION.md` |
| `TCS-008: Error Policy consolidation` | `specs/TCS-008_ERROR_POLICY.md` | `specs/ERROR_POLICY_CONSOLIDATION.md` |
| `TCS-009: Entry document responsibility` | `specs/TCS-009_ENTRY_DOCUMENTS.md` | `specs/ENTRY_DOCUMENT_RESPONSIBILITY.md` |
| `TCS-010: Distribution manifest synchronization` | `specs/TCS-010_DISTRIBUTION_MANIFEST_SYNC.md` | `specs/DISTRIBUTION_MANIFEST_SYNCHRONIZATION.md` |
| `TCS-011: Single Authority and Creation Gate` | `specs/TCS-011_SINGLE_AUTHORITY_GATE.md` | `specs/SINGLE_AUTHORITY_AND_CREATION_GATE.md` |
| `TCS-012: Incubation Queue` | `specs/TCS-012_INCUBATION_QUEUE.md` | `specs/INCUBATION_QUEUE.md` |
| `TCS-013 Scope Authority Retirement` | `specs/TCS-013_SCOPE_RETIREMENT.md` | `specs/SCOPE_AUTHORITY_RETIREMENT.md` |
| `TCS-014 Seven-stage Orchestration` | `specs/TCS-014_SEVEN_STAGE_ORCHESTRATION.md` | extracted into `specs/CORE_ORCHESTRATION_EVIDENCE_SPEC.md` |
| `TCS-015 Root Remediation Orchestration` | `specs/TCS-015_ROOT_REMEDIATION_ORCHESTRATION.md` | adopted portions extracted into `specs/CORE_ORCHESTRATION_EVIDENCE_SPEC.md` |
| `TCS-016 Governance Bootstrap Recovery` | `specs/TCS-016_GOVERNANCE_BOOTSTRAP_RECOVERY.md` | adopted portions extracted into `specs/CORE_ORCHESTRATION_EVIDENCE_SPEC.md` |

## 改善案13件の棚卸し

| No. | 改善案 | 正式化結果 |
|---:|---|---|
| 1 | Implementation Intensity / Process Levelの二軸化 | Core Routing Baselineで完了記録 |
| 2 | 流し見役の二軸判定 | Core Routing Baselineで完了記録 |
| 3 | Process Level P0-P4 | Core Routing Baselineで完了記録 |
| 4 | 低リスク軽量ルート | Core Routing Baselineで完了記録 |
| 5 | Protected Surface | Core Routing Baselineで完了記録 |
| 6 | Process Levelの機械補正 | Core Routing Baselineで完了記録 |
| 7 | Extension単位Shared Focus | 現行Focus方針と衝突するためretired/FROZEN |
| 8 | Focus Knowledge Promotion | 自動昇格を採用せずretired/FROZEN |
| 9 | Shared知識の適用範囲・寿命 | 独立仕様が必要なためretired/FROZEN |
| 10 | Focusを強度決定主体にしない | 解決済みとして凍結 |
| 11 | Risk評価軸の拡張 | Risk Evidenceで完了記録 |
| 12 | Execution Authority / Proposal Authority分離 | Proposal Authority and Safety Appealで完了記録 |
| 13 | 安全レベルへの異議・昇格提案 | Proposal Authority and Safety Appealで完了記録 |

## 設計原則

1. Work Packetは復活させず、Git差分、対象Spec、検証済みContext Cacheから作業境界を導出する。
2. Focus CacheはLandmine情報の正本責務を越えて共有知識registryへ拡張しない。
3. 知識は実行権限を与えず、Implementation IntensityやProcess Levelを下げる根拠にしない。
4. 機械補正は安全下限を下げない。
5. 通常作業へ独自の承認階層を追加しない。
6. テストはscript主体とし、成功時に解析担当を起動しない。
7. 1概念1Authorityとし、個別SpecはAuthorityを複製しない。

## 依存関係と正式化順

Core Routing Baselineを基礎とし、Proposal Authority and Safety Appealで権限を分離し、Risk Evidenceで安全側補正根拠を正式化した。Extension Knowledge案は必要性と独立仕様が具体化するまでretired/FROZENを維持する。後続の各consolidation、Creation Gate、InQ、Scope retirement、orchestration evidence extractionは上記active individual specificationsから参照する。

## 非採用

- Work Packetの再導入
- Focus Cacheの旧JSON/schema/promotion/handoff復活
- 成功ログのFocus保存
- 知識一致によるテスト省略
- AIの自己承認
- 推論スコアだけによるProcess Level低下

## History

- 2026-08-17: 改善案1〜6、11〜13を完了記録へ正式化し、改善案7〜9をFROZEN、改善案10を解決済みとして凍結した。
- 2026-08-21: active参照をnumberless individual specsへ移し、旧headingとfilenameをlegacy identity tableへ保持した。

## Non-authority boundary

本blueprintはhistoryとdependencyの案内であり、Authority、machine schema、approval、state、test resultを生成しない。active individual specificationまたは現行Authorityと衝突する場合は常に後者を優先する。
