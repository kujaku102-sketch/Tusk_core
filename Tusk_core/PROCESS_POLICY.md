<!-- md-scope-document: COMMON -->
# Process Policy

Process Policyは変更の危険度、必須安全工程、テスト下限、実行経路を決める正本である。技術的難度とProviderを決めるImplementation Intensityとは独立する。一方から他方を推定・変更しない。複数条件では常に最も高い下限と最も厳しい要件を採用し、作業中の範囲拡大時は再判定する。

## Process Level P0-P4

記録は`process_level:P0`〜`process_level:P4`とし、優先度は`priority:<value>`へ分離する。複数条件に該当する場合は最も高いProcess Levelを採用する。

| Process Level | 影響範囲 | 必須の安全工程 | テスト下限 |
|---|---|---|---|
| `process_level:P0` | 文言、読取専用調査、実行経路へ影響しない文書・メタデータ | 対象とdiffを確認し、コード・設定・成果物が変わらないことを確認 | 該当する構文、schema、リンク、diff-check |
| `process_level:P1` | 単一ファイルまたは単一機能の局所的で容易に復元可能な変更 | 変更前SHA、変更可能パス、復元方法 | 対象単体テストまたは限定検証 |
| `process_level:P2` | 複数ファイル、同一コンポーネントの複数経路、永続設定・互換契約 | 依存先、互換条件、backupまたはrollback | 対象テストと関連回帰 |
| `process_level:P3` | 複数コンポーネント、外部アプリ、プロセス間連携、永続データ、移行 | 隔離環境、停止・復旧、成果物保全、外部依存確認 | 単体、関連回帰、統合、必要時は限定実機 |
| `process_level:P4` | release、installer、distribution、security境界、破壊的・不可逆操作、広範な利用者データ | 明示承認、完全backup/rollback、監視、停止、成果物/manifest検証 | 全体回帰、統合、必要な実機、install/update/recovery/rollback |

外部アプリを実際に起動・停止・操作する場合は最低`process_level:P3`とする。永続設定または利用者データを書き換える場合は最低`process_level:P2`とする。配布物、インストーラ、更新・アンインストール、破壊的操作は`process_level:P4`とする。隔離やmock、既知解法、読取専用の先行調査は製品変更の影響範囲を下げない。個別仕様が厳しければ追加要件を優先する。

作業契約には最低限`process_level`、理由、`affected_components`、`safety_steps`、`minimum_tests`を記録する。不記載、理由不足、範囲不確定は`needs_review`とし、実装・実行へ進まない。

## Mechanical correction

機械補正は承認・編集・実行・テスト選定前に行い、宣言値を決して下げない。入力は宣言レベル、正規化済みworkspace相対の一意な対象パス（componentとeffect付き）、対象component、全操作フラグ、全Protected Surface、Risk Evidence、軽量ルート事実とする。パスに`..`、絶対パス、重複、空componentを許さない。パスcomponentは対象component一覧に存在しなければならない。意味的リスクを名前から推測しない。

下限は`P0=0`〜`P4=4`として次の最大値である。

```text
corrected_process_level = max(declared, scope, operation, protected_surface, risk_evidence)
```

- scope: writeなしで最大1 componentはP0、1 write/1 componentはP1、複数write/1 componentはP2、writeが複数componentならP3。
- operation: persistent settingsはP2。external app、persistent data、migrationはP3。release、distribution、installer、update/uninstall、破壊・不可逆、security boundary、広範なuser dataはP4。
- Risk Evidence: `cross_component`または`difficult`はP3、`distribution`または`irreversible`はP4の根拠にできる。

追加パス、component、true flag、厳しい保護下限は結果を低下させない。承認後の事実削除は下方補正でなくscope変更として再分類する。出力は宣言値、補正値、変更有無、各補正理由（rule/from/required/evidence）、レビュー状態・理由を含む。

必須値の欠落・不正値、非boolean flag、非正規化・workspace外パス、未知の保護面、根拠なし、異なる権威入力の矛盾は補正値を出さず`needs_review`とする。明示operation assertionsとflagの矛盾も同様である。自由文は機械根拠として解釈しない。

## Protected Surfaces（強制下限）

| surface_id | 条件 | 下限 | approval | SHA | rollback | mandatory verification |
|---|---|---|---|---|---|---|
| `security_boundary` | 権限・sandbox・ACL・署名・信頼・入力検証境界 | `process_level:P4` | `explicit_human` | `required` | `full_required` | `security_tests+full_regression+integration+rollback_test` |
| `authentication` | 認証・認可・session・token・本人/権限判定 | `process_level:P4` | `explicit_human` | `required` | `full_required` | `auth_positive_negative+security_tests+full_regression+integration+rollback_test` |
| `secrets` | 秘密値・鍵・credentialの生成/保存/取得/伝送/rotation/削除 | `process_level:P4` | `explicit_human` | `required` | `full_required` | `secret_absence_scan+security_tests+full_regression+integration+rollback_test` |
| `distribution_installer` | 配布物・manifest・署名・installer・更新・uninstall | `process_level:P4` | `explicit_human` | `required` | `full_required` | `full_regression+integration+install_update_uninstall+manifest_hash+rollback_test` |
| `destructive_operation` | 削除・上書き・不可逆変換・広範な強制終了 | `process_level:P4` | `explicit_human` | `required` | `full_required` | `isolated_dry_run+full_regression+integration+recovery_test+rollback_test` |
| `user_data` | 利用者所有データの読取/書込/移動/変換/削除経路 | `process_level:P3` | `approved_contract` | `required` | `required` | `unit+related_regression+integration+data_integrity+recovery_test` |
| `persistent_schema` | 永続schema・migration・互換性・versioning | `process_level:P3` | `approved_contract` | `required` | `required` | `schema_validation+forward_backward_migration+related_regression+integration+rollback_test` |
| `process_stop` | PID選択・signal・timeout・kill・子process終了 | `process_level:P3` | `approved_contract` | `required` | `required` | `pid_identity+stop_scope+unit+related_regression+integration+recovery_test` |
| `external_app` | 外部アプリの起動・停止・操作または連携経路 | `process_level:P3` | `approved_contract` | `required` | `required` | `dependency_precheck+unit+related_regression+integration+limited_real_app_test+recovery_test` |

該当面は独立に判定し、複数なら最高下限・最厳要件をANDで採用する。広範・破壊的・不可逆なuser data操作は`destructive_operation`にも該当する。秘密値そのものをSHA、log、diff、test artifactへ出さない。SHAは該当する非秘密の対象、仕様、schema、manifestへ結び付ける。

保護面があれば変更前SHA、rollback plan、mandatory testsを必須とし、`route:lightweight`を禁止する。Protected Surface判定とImplementation Intensityは独立であり、`implementation_intensity:LOW`でも下限、承認、SHA、rollback、検証を緩和しない。`explicit_human`は作業ID・対象・範囲・SHA・安全工程・rollback・検証への明示承認、`approved_contract`は同項目を含む有効な承認済み契約を意味する。不足は`waiting_human`。人間、model、mock、隔離、preflight訂正も下限をwaiveできない。値欠落または矛盾は`needs_review`とし、機械出力は`state:needs_review`とする。終了コード0だけで検証合格にしない。

## Lightweight route

軽量ルートは安全な限定作業で分業、cache入力、無関係な全体回帰を省く経路であり、Work Packetを作らない。次の全条件が必要である。

- `process_level:P0`または`process_level:P1`、かつ`implementation_intensity:LOW`または`implementation_intensity:MID`。
- 変更可能パス、成功条件、最低検証が確定。
- 単一担当で完結し、交代・並列・引継ぎが不要。
- 局所的で既知interfaceと復元方法がある。
- 未解決failure、強制停止、承認外diffがない。

`process_level:P2` 以上、`implementation_intensity:HIGH`または`implementation_intensity:MAX`、外部アプリ、process間連携、永続設定、永続データ、user data、migration、release、配布物、manifest、installer、update/uninstall、破壊的・不可逆、失敗、非ゼロ終了、強制停止、test不合格後の修正/再実行、Protected Surface、認証/security境界、複数componentのいずれかは標準ルートを強制する。不明は`route:standard`かつ`needs_review`。

軽量時だけ複数sub-agent、同一ファイル二段階編集、focus cache入力、一時推論snapshot、handoff capsule、無関係な回帰を省略できる。仕様、scope、現在SHA、依存、承認、変更前SHA、差分確認、対象review、最低検証は省略できない。P0はdiffと該当静的検証、P1は差分確認・対象単体テストまたは限定検証・復元可能性が最低限である。終了コード0だけで合格にせず、期待した差分と成果を確認する。

scope/依存の拡大、二軸上昇、計画外ファイル・保護面・外部依存、test failure/非ゼロ/停止、追加担当・cache・回帰の必要、契約/仕様/対象SHA不一致で即停止する。停止後は二軸を再判定し、`route:standard`へ昇格する。軽量ルート内で修正、再試行、条件緩和を行わない。

```yaml
route: lightweight | standard
process_level: P0 | P1 | P2 | P3 | P4
implementation_intensity: LOW | MID | HIGH | MAX
scope_bounded: true | false
success_conditions_bound: true | false
minimum_tests_bound: true | false
single_actor: true | false
unresolved_failure: true | false
external_app: true | false
persistent_data: true | false
distribution_change: true | false
destructive_operation: true | false
protected_surface: true | false
route_reason: <判定根拠>
```

## Risk Evidence

```yaml
risk_evidence:
  failure_frequency: none | isolated | repeated
  ambiguity: low | medium | high
  blast_radius: local | component | cross_component | distribution
  known_solution_confidence: unknown | low | medium | high
  dependency_volatility: low | medium | high
  rollback_difficulty: easy | bounded | difficult | irreversible
  evidence_refs: [<log, diff, spec, manifest or test reference>]
```

全6軸と1件以上の証拠を必須とする。失敗回数だけでIntensityを上げず、既知解法でIntensity・Process Level・test下限を下げない。環境原因を実装失敗へ変換しない。根拠不足・矛盾は`needs_review`。Risk Evidence自体に承認、実装、test省略、完成判定の権限はない。

## 機械的正本と停止規則

`tools/process_classifier.py`がJSON入力を検証し、JSON出力として補正レベル、Protected Surface、承認、mandatory verification、route、state、理由を返す。引数なしはstdin、引数ありはそのJSONファイルを読む。正常判定は終了0、`needs_review`は終了2。

専用contract testは1回だけ実行し、非ゼロ後は再実行しない。ただしproduct/test未実行で原因がcommand path、quote、module spellingだけの`preflight_error:true`は、記録したうえでコマンド文字列の限定訂正1回だけ許可する。この訂正でもProcess Level、承認、SHA、rollback、必須検証、安全境界を緩和しない。二度目の起動失敗、test実行後の失敗は停止する。`preflight_error`で承認不足、SHA不一致、ファイル不存在、正本不明、workspace外参照、権限エラー、reparse point、秘密露出、rollback欠落を回避してはならない。
