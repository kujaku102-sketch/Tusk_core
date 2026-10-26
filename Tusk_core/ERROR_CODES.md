<!-- md-scope-document: COMMON -->
# Tusk Core Error Registry

- **`1XX` 〜 `5XX`**: Core指定の固定エラーコード（本ファイルで統制）
- **`6XX` 〜 `9XX`**: 製品・Extension自由割り当て領域（`[F|M][6-9][0-9]{2}` はガードモニターで自動受理）

### 強制停止

| Code | Name | Condition |
|---|---|---|
| F101 | contract_invalid | 必須テスト契約または成果物リストが不正・欠損（旧F120）。 |
| F102 | artifact_invalid | 成果物の更新時刻・フォーマット・記録が不正（旧F121）。 |
| F103 | completion_invalid | 完了宣言（doneファイル）または必須チェックが不正（旧F122）。 |
| F104 | monitor_integrity_failure | 契約または成果物のSHA-256が一致しない（旧F124）。 |
| F123 | minor_threshold_exceeded | 軽度問題（Mコード）の発生件数または対象割合が上限を超過。 |
| F182 | user_requested_stop | ユーザーによるコンソールからの明示的な手動停止（`/stop` 専用）。 |
| F201 | progress_stalled | 一定時間（30分）有効な進捗更新がない。 |
| F202 | repeated_or_rework_exceeded | 同一エラーの連続反復、または手戻り上限（`MAX_REWORK_COUNT = 3`）を超過。 |
| F203 | path_safety_failure | 監視パスまたは変更対象がワークスペース・スコープ境界を逸脱。 |
| F204 | session_conflict | セッション停止中に対象スコープのファイルが外部で改変された。 |
| F205 | session_waiting_human | 仕様不足や承認待ちにより人間の判断を待つため停止。 |
| F206 | pipeline_fatal | 実行タスクが致命的失敗により明示的にパイプラインを停止。 |
| F301 | data_corrupted | 入力データの破損・読込不能。 |
| F302 | data_count_or_id_mismatch | 必須ID集合または件数の不一致。 |
| F303 | schema_validation_failed | データスキーマ検証の致命的失敗。 |
| F401 | api_auth_failed | API認証失敗または権限不足。 |
| F402 | communication_timeout | 外部通信のタイムアウトまたは接続断。 |
| F403 | quota_or_rate_exhausted | APIクォータ枯渇または回復不能なレート制限。 |
| F501 | supervisor_lost | 必須Supervisorプロセスが消失。 |
| F502 | process_lock_or_mismatch | プロセス識別子不一致または既存ガードロックとの競合。 |
| F503 | process_stop_incomplete | 停止処理後も対象プロセスが残留。 |
| F504 | process_registry_invalid | プロセス登録情報が不正、または外部連携アプリが応答不能。 |

### 軽度問題

| Code | Name | Condition |
|---|---|---|
| M120 | review_needed | 人間または独立レビュアーによる確認が必要。 |
| M180 | user_attention | 処理は継続するがユーザーへの通知が必要。 |
| M201 | retry_scheduled | 上限内の一時リトライをスケジュールした。 |
| M202 | cache_conflict | キャッシュ競合が発生し原本確認へフォールバックした。 |
| M301 | input_data_warning | 入力データに軽微な警告があるが処理可能。 |
| M302 | output_data_warning | 出力データの軽微な要確認事項。 |
| M303 | id_or_unit_warning | 識別子や単位・数値表現の軽微な要確認事項。 |
| M401 | transient_network_warning | 一時的な通信警告から復帰した。 |
| M402 | fallback_response_used | 承認済みの通信/スタイルフォールバックを使用した。 |
| M501 | external_app_warning | 外部連携アプリケーションからの非致命的警告。 |
