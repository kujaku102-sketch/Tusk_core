<!-- md-scope-document: COMMON -->
# Gemini Role Profile

**対象ランタイム**: Google Gemini / Antigravity エージェント専用プロファイル（Claude / Codex 用の定義は含まない）

## 1. 論理ロールとモデル割り当て

| 論理ロール (`role`) | 権限 (`access`) | 難易度 (`intensity`) | 標準モデル (`model_alias`) | 推論強度 (`thinking`) | 用途 |
|---|---|---|---|---|---|
| `lead` | `orchestrate` | - | `pro` | `high` | 全体設計、仕様照合、実装指示、リスク判定 |
| `skim` | `read_only` | - | `flash_lite` | `minimal` | 事前ファイル探索、差分確認、軽量調査 |
| `failure_analysis` | `read_only` | - | `flash` | `low` | 停止時の構造化ログ・エラー原因解析 |
| `review` | `review_only` | `LOW` / `MID` | `flash` | `medium` | 通常差分の仕様照合レビュー |
| `review` | `review_only` | `HIGH` / `MAX` | `pro` | `high` | 複雑ロジック・保護領域の厳密レビュー |
| `implementation` | `write_limited` | `LOW` | `flash_lite` | `low` | 定数変更、文言修正、機械的な小規模編集 |
| `implementation` | `write_limited` | `MID` | `flash` | `medium` | 単一機能内の通常実装・限定修正 |
| `implementation` | `write_limited` | `HIGH` | `pro` | `high` | 複数モジュール連携、並行処理、難解なバグ修正 |
| `implementation` | `write_limited` | `MAX` | `pro` | `high` | 特例難易度（※実行前に必ずユーザー明示承認が必要） |

## 2. 厳守ルール
- `skim` と `failure_analysis` は常に `read_only` とし、ファイル変更やテスト実行を行わない。
- `MAX` 難易度は自動分類できても**自動実行してはならない**。必ず実行前にユーザーの明示承認を得る。
- モデルの切り替えを「手戻り回数 (`rework_count`) のリセット」や「停止状態の自動解除」の根拠にしない。
