# Process Policy

Process Policyは変更の危険度、必須安全工程、テスト下限を決める正本である。技術的難度を決めるImplementation Intensityとは独立する。一方から他方を推定・変更しない。複数条件では常に最も高い下限と最も厳しい要件を採用し、作業中の範囲拡大時は再判定する。

## 停止の書き方

停止はPOLICY.mdの`STOP`で記録し、`reason`は次の値で始める。

| reason | 意味 |
|---|---|
| `approval_missing` | 承認不足、非ゼロ終了、編集不能、人間操作待ち |
| `limit_reached` | 再作業上限の到達、危険領域への拡大、MAX承認範囲を超える追加修正 |
| `info_missing` | 技術情報または読み取り専用レビューの根拠が不足している |
| `owner_abandon` | 所有者が終了を指示した |
| `unclassified` | 上のいずれにも分類できない。推測で分類しない |

停止中に許すのは、指定された読み取り専用レビュー担当によるSpec、差分、ログ、証拠の確認だけである。レビュー担当は停止を直接解除せず、確認範囲、根拠、判定、未解決事項を返す。停止は自動処理、実装担当、レビュー担当、外側の実行機構が独自に解除しない。完了後に未解決エラー、未検証条件、承認外差分を検出した場合は完成判定を取り消す。

## Rework and resume

- 環境、Provider、CLI、テスト起動経路の失敗を製品コードの失敗へ算入しない。分類を分け、同じ失敗を名称変更で分割しない。
- 非ゼロ終了、計画外依存、編集不能、STOP後に別案や再実行へ自動移行しない。
- 停止時は現在差分、失敗テスト、エラーコード、ログ末尾、成果物、Focus Cache更新の有無を保存する。

停止後の操作は、所有者の承認に結合したRECOVERY(新世代)、限定復元(restore)、CLOSE abandoned、SUCCESSORだけとする。RECOVERYは現在差分、修正方針、失敗履歴を維持し、停止時から対象Spec、対象パス、差分に外部変更がないことを確認する。範囲、安全工程、最大強度、必須テストを変える場合は再確定し、MAXまたは危険領域なら新しい承認を得る。限定復元は今回の作業差分だけをGitで一意に分離でき、対象提示と明示承認を得た場合だけ行い、既存のユーザー変更、失敗証拠、ログ、Focus Cacheを戻さない。abandonedは未完了として差分と証拠を保存し、その後の再開には新しいwork_idを使う。曖昧な続行指示は直前の停止作業を機械的に一意特定できる場合だけRECOVERYとして扱う。

### Recovery authorization

再作業上限の超過、連続失敗、版不一致などにより続行できない場合、停止理由、失敗証拠、現在差分、影響範囲、具体的な原因と解決策、変更する版・対象パス、検証方法、復元方法、残る不確実性を説明して所有者の明示承認を得る。原因が未確定なら未確定と明記し、その解決策に含める調査を具体化する。単なる「続行」で制限を解除しない。承認はRECOVERYのapprovalとして新世代へ結合する。

版不一致は、正本と採用版を特定して承認済み解決策で整合させる。既存証拠を上書きせず、対応する現行schema・baseline・契約で再検証する。不一致や破損を合格扱いにする許可ではない。承認はMAX承認、Protected Surface、安全工程、変更可能範囲、配布時の完全性検証、成功条件を解除しない。

## Process Level P0-P4

Process LevelはP0〜P4とし、planの`risk`へ記録する。複数条件に該当する場合は最も高いProcess Levelを採用する。

| Process Level | 影響範囲 | 必須の安全工程 | テスト下限 |
|---|---|---|---|
| `P0` | 文言、読取専用調査、実行経路へ影響しない文書・メタデータ | 対象とdiffを確認し、コード・設定・成果物が変わらないことを確認 | 該当する構文、schema、リンク、diff-check |
| `P1` | 単一ファイルまたは単一機能の局所的で容易に復元可能な変更 | 現在差分、変更可能パス、復元方法 | 対象単体テストまたは限定検証 |
| `P2` | 複数ファイル、同一コンポーネントの複数経路、永続設定・互換契約 | 依存先、互換条件、backupまたはrollback | 対象テストと関連回帰 |
| `P3` | 複数コンポーネント、外部アプリ、プロセス間連携、永続データ、移行 | 隔離環境、停止・復旧、成果物保全、外部依存確認 | 単体、関連回帰、統合、必要時は限定実機 |
| `P4` | release、installer、distribution、security境界、破壊的・不可逆操作、広範な利用者データ | 明示承認、完全backup/rollback、監視、停止、成果物/manifest検証 | 全体回帰、統合、必要な実機、install/update/recovery/rollback |

外部アプリを実際に起動・停止・操作する場合は最低P3とする。永続設定または利用者データを書き換える場合は最低P2とする。配布物、インストーラ、更新・アンインストール、破壊的操作はP4とする。隔離やmock、既知解法、読取専用の先行調査は製品変更の影響範囲を下げない。個別仕様が厳しければ追加要件を優先する。

作業契約の項目は、planの`request.text`に`process_level`、理由、`affected_components`、`safety_steps`、`minimum_tests`として書く。不記載、理由不足、範囲不確定は実装・実行へ進まず、`info_missing`で停止する。

## Mechanical correction

補正は承認・編集・実行・テスト選定前に行い、宣言値を決して下げない。入力は宣言レベル、`classification`(対象component一覧、scopeと同じ順で1件ずつの対象パス(path・component・effect。effectはcreate/modify/delete/read_only)、全操作フラグ11種、全Protected Surface 9種)とする。パスに`..`、絶対パス、重複、空componentを許さない。パスcomponentは対象component一覧に存在しなければならない。内容と名前による判定は、profileに決めた規則で、上げる方向にだけ使う。規則は`config/policy-profile.json`の`classification_rules`に置き、規則に無いものは推測しない。

下限は`P0=0`〜`P4=4`として次の最大値である。

```text
corrected_process_level = max(declared, scope, operation, protected_surface)
```

- scope: writeなしで最大1 componentはP0、1 write/1 componentはP1、複数write/1 componentはP2、writeが複数componentならP3。
- operation: persistent settingsはP2。external app、persistent data、migrationはP3。release、distribution、installer、update/uninstall、破壊・不可逆、security boundary、広範なuser dataはP4。

追加パス、component、true flag、厳しい保護下限は結果を低下させない。承認後の事実削除は下方補正でなくscope変更として再分類する。補正の根拠は宣言値、補正値、変更有無、各補正理由(rule/from/required/evidence)として記録する。

必須値の欠落・不正値、非boolean flag、非正規化・workspace外パス、未知の保護面、根拠なし、異なる権威入力の矛盾は補正値を出さず`info_missing`で停止する。明示operation assertionsとflagの矛盾も同様である。自由文は機械根拠として解釈しない(profileの規則が見るのは、最初のPLANのbaselineの内容とscopeのpathだけである)。

Coreは plan の classification から下限を計算し、申告と規則判定(`detected`)の厳しい方を採って`floor`・`protected`・`corrections`をplanに保存し、下限より低いriskを`risk_below_floor`で拒否する。規則判定が申告より厳しいときは拒否せず、判定の方へ上書きして`corrections`に記録する。判定は最初のPLANだけで行い、RESULTでは再判定しない。
RESULTでは、最初のPLANのbaselineと比べて`read_only`の内容が変わった、または`modify`が無くなった場合を`effect_result_mismatch`で拒否する。申告`create`が無いまま、`delete`が残ったままの場合は拒否せず、RESULTの`unfulfilled`(「無いので作れ」「残っているので消せ」)に記録し、statusとfocusに出す。`unfulfilled`が残ってもCLOSE completedは止めない。

## Protected Surfaces(強制下限)

| surface_id | 条件 | 下限 | 承認 | rollback | mandatory verification |
|---|---|---|---|---|---|
| `security_boundary` | 権限・sandbox・ACL・署名・信頼・入力検証境界 | `P4` | 所有者のplan承認 | `full_required` | `security_tests+full_regression+integration+rollback_test` |
| `authentication` | 認証・認可・session・token・本人/権限判定 | `P4` | 所有者のplan承認 | `full_required` | `auth_positive_negative+security_tests+full_regression+integration+rollback_test` |
| `secrets` | 秘密値・鍵・credentialの生成/保存/取得/伝送/rotation/削除 | `P4` | 所有者のplan承認 | `full_required` | `secret_absence_scan+security_tests+full_regression+integration+rollback_test` |
| `distribution_installer` | 配布物・manifest・署名・installer・更新・uninstall | `P4` | 所有者のplan承認 | `full_required` | `full_regression+integration+install_update_uninstall+manifest_hash+rollback_test` |
| `destructive_operation` | 削除・上書き・不可逆変換・広範な強制終了 | `P4` | 所有者のplan承認 | `full_required` | `isolated_dry_run+full_regression+integration+recovery_test+rollback_test` |
| `user_data` | 利用者所有データの読取/書込/移動/変換/削除経路 | `P3` | 不要(P4のときだけ) | `required` | `unit+related_regression+integration+data_integrity+recovery_test` |
| `persistent_schema` | 永続schema・migration・互換性・versioning | `P3` | 不要(P4のときだけ) | `required` | `schema_validation+forward_backward_migration+related_regression+integration+rollback_test` |
| `process_stop` | PID選択・signal・timeout・kill・子process終了 | `P3` | 不要(P4のときだけ) | `required` | `pid_identity+stop_scope+unit+related_regression+integration+recovery_test` |
| `external_app` | 外部アプリの起動・停止・操作または連携経路 | `P3` | 不要(P4のときだけ) | `required` | `dependency_precheck+unit+related_regression+integration+limited_real_app_test+recovery_test` |

承認はPOLICY.mdのとおりP4の開始に要る。保護対象のdesign/final reviewは承認の有無に関わらず必要である。

該当面は独立に判定し、複数なら最高下限・最厳要件をANDで採用する。広範・破壊的・不可逆なuser data操作は`destructive_operation`にも該当する。秘密値そのものをSHA、log、diff、test artifactへ出さない。

保護面があればrollback plan、mandatory testsを必須とし、軽量な作業経路を使わない。Protected Surface判定とImplementation Intensityは独立であり、`LOW`でも下限、承認、rollback、検証を緩和しない。不足は`approval_missing`で停止する。人間、model、mock、隔離、preflight訂正も下限をwaiveできない。値欠落または矛盾は補正値を出さず`info_missing`で停止する。終了コード0だけで検証合格にしない。

## 軽量な作業の条件

P0/P1の通常作業は、次の全条件を満たす場合だけ、分業、cache入力、無関係な全体回帰を省ける。

- Process LevelがP0またはP1、かつIntensityがLOWまたはMID。
- 変更可能パス、成功条件、最低検証が確定。
- 単一担当で完結し、交代・並列・引継ぎが不要。
- 局所的で既知interfaceと復元方法がある。
- 未解決failure、強制停止、承認外diffがない。

P2以上、HIGHまたはMAX、外部アプリ、process間連携、永続設定、永続データ、user data、migration、release、配布物、manifest、installer、update/uninstall、破壊的・不可逆、失敗、非ゼロ終了、強制停止、test不合格後の修正/再実行、Protected Surface、認証/security境界、複数componentのいずれかは通常の全工程を強制する。不明も全工程とし、`info_missing`で停止する。

省略できない項目は、仕様、scope、現在のsnapshot、依存、承認、差分確認、対象review、最低検証である。P0はdiffと該当静的検証、P1は差分確認・対象単体テストまたは限定検証・復元可能性が最低限である。終了コード0だけで合格にせず、期待した差分と成果を確認する。

scope/依存の拡大、二軸上昇、計画外ファイル・保護面・外部依存、test failure/非ゼロ/停止、追加担当・cache・回帰の必要、契約/仕様/対象snapshotの不一致で即停止し、二軸を再判定して全工程へ移る。この条件内で修正、再試行、条件緩和を行わない。
