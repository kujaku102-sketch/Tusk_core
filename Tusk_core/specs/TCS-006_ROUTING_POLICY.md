<!-- md-scope-document: COMMON -->
# TCS-006 Routing Policy Consolidation

状態: `COMPLETED`

## Requirement

`IMPLEMENTATION_INTENSITY.md`、`SKIM_DECISION.md`、`AUTHORITY_SEPARATION.md`に分散した技術難度、流し見、Provider routing、MAX gate、Execution/Proposal Authorityを、内容を失わず`ROUTING_POLICY.md`へ統合する。Process Levelの意味と安全工程は複製せず`PROCESS_POLICY.md`を正本として参照する。

## Change boundary

- 追加可能: `ROUTING_POLICY.md`、`specs/TCS-006_ROUTING_POLICY.md`、`tests/test_routing_policy.py`
- 変更禁止: 旧3文書、入口文書、他TCS、既存テスト、製品コード
- 旧文書は削除・スタブ化しない。

## Success conditions

- COMMONスコープの新正本が存在する。
- Intensity、Skim単一出力、Provider routing、MAX gate、Execution/Proposal Authorityを保持する。
- Process Level値の意味を再掲せず`PROCESS_POLICY.md`を参照する。
- MAX自動適用は1回に限定し、その後は人間レビューで停止する。
- 安全水準低下は人間承認必須で、Protected Surface等の下限を迂回しない。
- 専用テストが成功する。

## Implementation record

- 追加: `ROUTING_POLICY.md`
- 追加: `specs/TCS-006_ROUTING_POLICY.md`
- 追加: `tests/test_routing_policy.py`
- 旧文書は参照のみで変更していない。
- 専用テスト: `python -m unittest tests/test_routing_policy.py` 成功。

## Unresolved

なし。旧文書の参照移行・スタブ化・削除は後続TCSの対象とする。
