<!-- md-scope-document: COMMON -->
# Claude Role Profile

**対象ランタイム**: Anthropic Claude エージェント専用プロファイル（Gemini / Codex 用の定義は含まない）

## 1. 論理ロールとモデル割り当て

| 論理ロール (`role`) | 権限 (`access`) | 難易度 (`intensity`) | 標準モデル (`model_alias`) | 推論強度 (`effort`) | 用途 |
|---|---|---|---|---|---|
| `lead` | `orchestrate` | - | `opus` (Opus 5.5) | `medium` | 全体設計、仕様照合、実装指示、リスク判定 |
| `skim` | `read_only` | - | `haiku` | `low` | 事前ファイル探索、差分確認、軽量調査 |
| `failure_analysis` | `read_only` | - | `sonnet` | `low` | 停止時の構造化ログ・エラー原因解析 |
| `review` | `review_only` | `LOW` / `MID` / `HIGH` | `sonnet` | `medium` | 差分と仕様の読み取り専用レビュー |
| `review` | `review_only` | `MAX` | `opus` (Opus 5.5) | `medium` | 保護領域・特例変更の最上位レビュー |
| `implementation` | `write_limited` | `LOW` | `haiku` | `low` | 定数変更、文言修正、機械的な小規模編集 |
| `implementation` | `write_limited` | `MID` | `sonnet` | `medium` | 単一機能内の通常実装・限定修正 |
| `implementation` | `write_limited` | `HIGH` | `sonnet` | `high` | 複数モジュール連携、複雑なロジック実装 |
| `implementation` | `write_limited` | `MAX` | `opus` (Opus 5.5) | `medium` | 特例難易度（※実行前に必ずユーザー明示承認が必要） |

## 2. 厳守ルール
- `skim` と `failure_analysis` は常に `read_only` とし、ファイル変更やテスト実行を行わない。
- `MAX` 難易度は自動分類できても**自動実行してはならない**。必ず実行前にユーザーの明示承認を得る。
- モデルの切り替えを「手戻り回数 (`rework_count`) のリセット」や「停止状態の自動解除」の根拠にしない。
