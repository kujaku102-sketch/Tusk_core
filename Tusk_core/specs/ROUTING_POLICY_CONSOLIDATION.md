# Routing Policy Consolidation

## Status

状態: `COMPLETED`

## Legacy identity

- Legacy heading: `TCS-006 Routing Policy Consolidation`
- Legacy filename: `specs/TCS-006_ROUTING_POLICY.md`

## Purpose and Requirement

技術難度、流し見、Provider routing、MAX gateを内容を失わず`ROUTING_POLICY.md`へ統合する。Process Levelと安全工程は`PROCESS_POLICY.md`、Execution/Proposal Authorityは`AUTHORITY_SEPARATION.md`を参照する。

## Authority references

- Routing Authority: `ROUTING_POLICY.md`
- Process Authority: `PROCESS_POLICY.md`
- Execution/Proposal Authority: `AUTHORITY_SEPARATION.md`

## Scope and Outcome

統合時の`ROUTING_POLICY.md`、legacy Spec、`tests/test_routing_policy.py`を対象とした。Intensity、Skim単一出力、Provider routing、MAX gateを保持し、Process Levelの意味を再掲せず、MAXの自動分類と人間承認を分離する結果を記録する。旧3文書は当時参照のみで変更しなかった。

## Acceptance

Routing Authorityが必要なsectionと契約を保持し、安全水準低下やMAX適用がAuthority境界を迂回しないことを専用契約テストで確認する。

## History

- 2026-08-17: `ROUTING_POLICY.md`、legacy Spec、`tests/test_routing_policy.py`を追加した。
- 2026-08-17: `python -m unittest tests/test_routing_policy.py`が成功した。
- 2026-08-18: Authority正本分離と、MAXの自動分類・人間承認必須というユーザー裁定を反映した。
- 2026-08-21: legacy identityを保持してnumberless Specへ移行した。

## Non-authority boundary

本Specは統合履歴と受入範囲を記録する。Intensity、Provider、Skim、MAXの機械規則を複製せず、`ROUTING_POLICY.md`を上書きしない。
