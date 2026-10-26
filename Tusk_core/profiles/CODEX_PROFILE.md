<!-- md-scope-document: COMMON -->
# Codex Role Profile

**対象ランタイム**: OpenAI Codex エージェント専用プロファイル（Gemini / Claude 用の定義は含まない）

## 1. 論理ロールとモデル割り当て

| 論理ロール (`role`) | 権限 (`access`) | 難易度 (`intensity`) | 標準モデル (`model_alias`) | 推論強度 (`reasoning_effort`) | 用途 |
|---|---|---|---|---|---|
| `lead` | `orchestrate` | - | `gpt-6-sol` | `high` | 全体設計、仕様照合、実装指示、リスク判定 |
| `skim` | `read_only` | - | `gpt-6-luna` | `low` | 事前ファイル探索、差分確認、軽量調査 |
| `failure_analysis` | `read_only` | - | `gpt-6-luna` | `low` | 停止時の構造化ログ・エラー原因解析 |
| `review` | `review_only` | `LOW` | `gpt-6-luna` | `medium` | 小規模変更のレビュー |
| `review` | `review_only` | `MID` / `HIGH` | `gpt-6-sol` | `medium` | 通常・複雑変更の仕様照合レビュー |
| `review` | `review_only` | `MAX` | `gpt-6-astra` | `high` | 保護領域・特例変更の最上位レビュー |
| `implementation` | `write_limited` | `LOW` | `gpt-6-luna` | `high` | 定数変更、文言修正、機械的な小規模編集 |
| `implementation` | `write_limited` | `MID` | `gpt-6-sol` | `low` | 単一機能内の通常実装・限定修正 |
| `implementation` | `write_limited` | `HIGH` | `gpt-6-sol` | `medium` | 複数モジュール連携、複雑なロジック実装 |
| `implementation` | `write_limited` | `MAX` | `gpt-6-astra` | `high` | 特例難易度（※実行前に必ずユーザー明示承認が必要） |

## 2. 厳守ルール
- `skim` と `failure_analysis` は常に `read_only` とし、ファイル変更やテスト実行を行わない。
- `MAX` 難易度は自動分類できても**自動実行してはならない**。必ず実行前にユーザーの明示承認を得る。
- モデルの切り替えを「手戻り回数 (`rework_count`) のリセット」や「停止状態の自動解除」の根拠にしない。
