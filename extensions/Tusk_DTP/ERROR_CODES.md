<!-- md-scope-document: IDTASK -->
# IdTaskエラーコード規則

## 1. 正本

この文書をIdTask共通エラーコードの正本とする。`GENERAL.md`は運用規則、個別仕様は使用コードと検出条件だけを持つ。

共通監視ツールでの検出源、優先順位、停止動作は`IdTaskAct2/specs/029_common_test_guard_blueprint.md`を正本とする。

## 2. 形式

```text
F000-F199: 現行互換の強制停止
M000-M199: 現行互換の軽度問題
F200-F299: IdTask新規固有の強制停止
M200-M299: IdTask新規固有の軽度問題
```

- `000-199`は現行実装・テスト・ログ契約との互換番号帯、`200-299`は新規IdTask固有番号帯とする。
- 完全なコードは接頭辞を含む4文字とする。
- `F`は後続停止、関連プロセス停止、強制停止レポートの対象とする。Luna通知は障害原因の解析が必要なFだけに行う。
- `M`は記録して処理を継続し、Lunaへ自動送信しない。
- 同じ数字でも`F`と`M`は別コードとして管理する。
- `F000`と`M000`は分類不能用。恒久利用せず`needs_review`を付ける。

### COMMON意味キーの現行バインド

| COMMON意味キー | IdTask現行コード | 扱い |
|---|---|---|
| `USER_REQUESTED_STOP` | `F182` | 既存監視・テスト互換のため維持。障害解析通知と再作業回数加算の対象外 |

- `F182`の即時改番は監視実装、仕様029、単体テスト、既存ログ契約への影響が大きいため行わない。
- 新規のIdTask固有コードは`F200-F299`または`M200-M299`へ割り当てる。
- `F182`を200番台へ移行する場合は、独立Specで互換期間、旧新コード対応、ログ読取互換、監視テストを定義する。

## 3. 番号帯

| 範囲 | 分野 |
|---|---|
| `000` | 分類不能 |
| `001-019` | 環境、設定、依存関係 |
| `020-039` | プロセス、実行、停止、ループ |
| `040-059` | ファイル、パス、入出力 |
| `060-079` | データ、ID、件数、形式 |
| `080-099` | 翻訳、エージェント、ブリッジ、通信 |
| `100-119` | InDesign、JSX、スタイル、レイアウト |
| `120-139` | PDF、画像、成果物、検証 |
| `140-159` | キャッシュ、チェックポイント、学習 |
| `160-179` | GUI、パッケージ、インストーラ、バージョン |
| `180-189` | ユーザー操作、手動復旧 |
| `190-199` | 将来拡張用 |

## 4. 登録規則

1. 新しいコードは実装前に個別仕様とこの文書へ登録する。
2. 一つの完全コードへ複数の意味を割り当てない。
3. 登録済みコードの意味と重大度を後から変更しない。
4. 廃止コードは再利用せず`retired`として残す。
5. 実装計画には使用するコード、検出条件、既定動作だけを抜粋する。
6. 実装担当は実装計画にないコードを追加・変更しない。
7. `F`と`M`の変更が必要な場合は、開発指揮へ提案して承認を得る。
8. エラー理由、対象、直前工程はコード番号へ埋め込まず構造化ログへ書く。

## 5. ログ形式

```text
[IDTASK_FORCE_STOP] code=Fxxx run_id=<RUN_ID> component=<COMPONENT> step=<STEP> reason=<REASON>
[IDTASK_MINOR_ISSUE] code=Mxxx run_id=<RUN_ID> component=<COMPONENT> step=<STEP> target=<TARGET> detail=<DETAIL>
```

- 強制停止マーカーへ`Mxxx`、軽度問題マーカーへ`Fxxx`を指定してはならない。
- ログは1行で出力し、直後にflushする。
- 既存の文字列コードは移行完了まで互換入力としてだけ受け付ける。

## 6. 初期登録コード

### 強制停止

| コード | 名前 | 検出条件 |
|---|---|---|
| `F000` | `UNKNOWN_FATAL` | 分類不能な継続不能エラー |
| `F001` | `REQUIRED_ENV_MISSING` | 必須環境がない |
| `F002` | `DEPENDENCY_MISSING` | 必須モジュール、DLL、補助ファイルがない |
| `F003` | `VERSION_MISMATCH` | 必須バージョンと一致しない |
| `F004` | `CONFIG_INVALID` | 必須設定が不正 |
| `F005` | `PERMISSION_DENIED` | 必須操作の権限がない |
| `F020` | `PROCESS_LOST` | 必須プロセスが消失 |
| `F021` | `PROCESS_STALLED` | 30分以上進捗がない |
| `F022` | `LOOP_DETECTED` | 同一状態を閾値以上反復 |
| `F023` | `MULTIPLE_INSTANCE_CONFLICT` | 多重起動が競合 |
| `F024` | `RESIDUAL_PROCESS_BLOCKING` | 残存プロセスが次工程を妨害 |
| `F025` | `UNHANDLED_EXCEPTION` | 未処理例外で継続不能 |
| `F026` | `PIPELINE_FATAL` | パイプライン全体が継続不能 |
| `F040` | `INPUT_MISSING` | 必須入力がない |
| `F041` | `INPUT_INVALID` | 必須入力が破損または対象外形式 |
| `F042` | `OUTPUT_WRITE_FAILED` | 必須成果物を書き込めない |
| `F043` | `FILE_LOCKED` | 必須ファイルのロックを解除できない |
| `F044` | `PATH_INVALID` | 必須パスが不正 |
| `F045` | `STORAGE_EXHAUSTED` | 保存領域が不足 |
| `F060` | `DATA_FORMAT_INVALID` | 必須データ形式が不正 |
| `F061` | `DATA_COUNT_MISMATCH` | 必須件数が一致しない |
| `F062` | `DATA_ID_MISMATCH` | ID集合が一致しない |
| `F063` | `DATA_ORDER_MISMATCH` | 必須順序が一致しない |
| `F064` | `REQUIRED_FIELD_EMPTY` | 必須欄が空 |
| `F065` | `DATA_DUPLICATE` | 禁止された重複がある |
| `F066` | `DATA_INTEGRITY_FAILED` | 整合性検証に失敗 |
| `F080` | `TRANSLATION_FATAL` | 翻訳工程を継続できない |
| `F081` | `AGENT_UNAVAILABLE` | 必須翻訳エージェントを利用できない |
| `F082` | `BRIDGE_UNAVAILABLE` | 必須ブリッジへ接続できない |
| `F083` | `EXTERNAL_RESPONSE_INVALID` | 外部応答が空または不正 |
| `F084` | `RATE_LIMIT_OR_QUOTA` | クォータ不足で継続不能 |
| `F100` | `INDESIGN_UNAVAILABLE` | 必須InDesignへ接続できない |
| `F101` | `JSX_FAILED` | JSX実行が失敗 |
| `F102` | `STYLE_APPLICATION_FAILED` | 必須スタイルを適用できない |
| `F103` | `LAYOUT_FAILED` | 必須レイアウト処理が失敗 |
| `F120` | `ARTIFACT_MISSING` | 必須成果物がない |
| `F121` | `ARTIFACT_INVALID` | 成果物が破損または不正 |
| `F122` | `VALIDATION_FAILED` | 必須検証に失敗 |
| `F123` | `QUALITY_THRESHOLD_FAILED` | 品質閾値を満たさない |
| `F124` | `HASH_MISMATCH` | SHA-256が一致しない |
| `F140` | `CHECKPOINT_INVALID` | チェックポイントが不正 |
| `F141` | `CACHE_FATAL` | 必須キャッシュが利用不能 |
| `F142` | `LEARNING_DATA_INVALID` | 学習登録条件を満たさない |
| `F160` | `PACKAGE_INCOMPLETE` | 配布パッケージの必須物がない |
| `F161` | `INSTALL_FAILED` | インストールが失敗 |
| `F162` | `GUI_START_FAILED` | GUIを起動できない |
| `F163` | `VERSION_INCONSISTENT` | バージョン構成が一致しない |
| `F180` | `MANUAL_RECOVERY_REQUIRED` | 自動復旧不能で手動対応が必要 |
| `F181` | `UNSUPPORTED_OPERATION` | 未対応操作が要求された |
| `F182` | `USER_REQUESTED_STOP` | ユーザーが監視コンソールから安全停止を要求 |

### 軽度問題

| コード | 名前 | 検出条件 |
|---|---|---|
| `M000` | `UNKNOWN_MINOR` | 分類不能だが継続可能 |
| `M001` | `ENV_FALLBACK_USED` | 代替環境へ切り替えて継続 |
| `M002` | `OPTIONAL_DEPENDENCY_MISSING` | 任意依存がない |
| `M020` | `RETRY_SUCCEEDED` | 許可済みの限定再試行で成功 |
| `M021` | `TRANSIENT_TIMEOUT` | 一時的タイムアウトから復帰 |
| `M040` | `OPTIONAL_FILE_MISSING` | 任意ファイルがない |
| `M041` | `EXISTING_OUTPUT_SKIPPED` | 既存成果物を安全にスキップ |
| `M060` | `DATA_SKIPPED_SAFE` | 許容されたデータだけをスキップ |
| `M061` | `DATA_MINOR_CONFLICT` | 継続可能なデータ衝突 |
| `M080` | `TRANSLATION_SKIP` | 許容件数内の翻訳スキップ |
| `M081` | `AGENT_RETRYABLE_ERROR` | 外部エージェントの一時エラー |
| `M100` | `STYLE_FALLBACK` | 代替スタイルを適用 |
| `M101` | `LAYOUT_FALLBACK` | 代替レイアウト処理を適用 |
| `M120` | `QUALITY_NEEDS_REVIEW` | 成果物はあるが人間確認が必要 |
| `M140` | `CACHE_MISS` | キャッシュ不一致により通常処理へ移行 |
| `M141` | `CACHE_CONFLICT` | 継続可能なキャッシュ衝突 |
| `M160` | `OPTIONAL_PACKAGE_FILE_MISSING` | 任意同梱物がない |
| `M180` | `USER_NOTICE` | ユーザーへの状態通知だけが必要 |

## 7. 既存コード互換表

| 既存コード | 新コード |
|---|---|
| `STALL_30M` | `F021` |
| `LOOP_DETECTED` | `F022` |
| `PROCESS_LOST` | `F020` |
| `PIPELINE_FATAL` | `F026` |
| `ARTIFACT_INVALID` | `F121` |
| `TRANSLATION_FATAL` | `F080` |
| `TRANSLATION_SKIP` | `M080` |
| `CACHE_CONFLICT` | `M141` |
| `STYLE_FALLBACK` | `M100` |
| `REVIEW_NEEDED` | `M120` |

既存コードを直ちに削除しない。個別実装とテストを通過したコードから順次移行する。
