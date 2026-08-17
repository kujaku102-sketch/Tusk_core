<!-- md-scope-document: COMMON -->
# Incubation Queue (InQ)

InQは、観測、改善候補、再利用候補、規則変更案を正本へ入れる前に保持する
非権威の作業待ち領域。InQ内の項目は仕様、許可、正解、テスト省略根拠にならない。

## Storage

```text
<workspace>/work/inq/registry.json
```

workspaceはCLIへ明示し、Core配布物、拡張、製品ソースへInQデータを書かない。
registryはUTF-8 JSONとして原子的に更新する。

## Item contract

```text
inq_id
kind: observation | improvement | pattern | authority_proposal
scope: core | extension | project
summary
target_authority
evidence[]
state: observed | candidate | verified | proposed | adopted | rejected | stale
created_at_utc
updated_at_utc
reviewed_by[]
decision_reason
```

`evidence`はローカル相対パスまたは検証可能なIDだけを持つ。推論履歴、秘密情報、
成功ログ全文、会話全文を保存しない。

## State transitions

```text
observed -> candidate | rejected
candidate -> verified | rejected | stale
verified -> proposed | stale
proposed -> adopted | rejected | stale
adopted -> stale
rejected -> candidate
stale -> candidate | rejected
```

- `verified`には1件以上のevidenceとreviewerが必要。
- `proposed`には登録済み`target_authority`が必要。新規Authority候補は先にCreation Gateを通す。
- `adopted`にはdecision reasonとreviewerが必要。
- `adopted`は正本変更の証拠ではない。正本編集、Spec、テストは別の通常作業として行う。
- 自動昇格、自動採用、自動統合、InQ一致によるProcess Level低下を禁止する。

## Lifecycle

重複候補は自動結合せず別IDのまま報告する。依存、対象Authority、証拠が古くなった
項目は`stale`へ移す。release成果物へworkspaceのInQデータを含めない。
