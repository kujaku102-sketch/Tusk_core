# Risk Evidence

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-003 Risk Evidence`
- Legacy filename: `specs/TCS-003_RISK_EVIDENCE.md`

## Purpose and Requirement

改善案11のRisk Evidenceを、固定スコアや実装難度の代理ではなく安全側補正の根拠として扱う。改善案10は解決済みとして凍結し、失敗回数だけで実装難度を上げず、環境原因と実装原因を分離する。

## Authority references

- Risk Evidenceの評価軸とProcess補正: `PROCESS_POLICY.md`
- 流し見への入力と技術難度: `ROUTING_POLICY.md`
- Landmineの限定された証拠責務: `FOCUS_CACHE_SPEC.md`

## Scope and Outcome

Risk Evidenceの構造化入力と安全側補正への利用を対象とする。legacy Specは`PROCESS_POLICY.md`の6評価軸を流し見へ渡し、環境原因を無関係な実装難度へ変換せず、補正根拠に限定する結果を記録した。

## Acceptance

参照Authorityと契約テストがRisk Evidenceの評価軸、原因分離、安全水準を下げない補正を保持していることを確認する。

## History

- 2026-08-17: 改善案11を`COMPLETED`、改善案10を解決済みとして記録した。
- 2026-08-21: legacy identityを保持してnumberless Specへ移行した。

## Non-authority boundary

本SpecはRisk Evidenceの採用目的と履歴だけを記録する。評価軸の機械schema、補正値、routing判断を複製せず、`PROCESS_POLICY.md`と実装Toolを上書きしない。
