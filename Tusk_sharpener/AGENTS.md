<!-- md-scope-document: COMMON -->
# Tusk Sharpener Agent Contract

- SharpenerはTusk Coreから独立した自己監査コンポーネントとする。
- `check`と`report`は対象を変更しない。
- `repair`は明示された安全な生成物だけを変更し、規範文書、authority、Spec、コードの意味を変更しない。
- 不明な状態、競合、欠落、対象外修復は`needs_human_review`として報告する。
- Sharpener自身へ通常のImplementation Intensity / Process Level判定を再帰適用しない。

