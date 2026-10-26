<!-- md-scope-document: COMMON -->
# Tusk Core Error Policy

## 1. エラーコード体系 (`[F|M][1-9][0-9]{2}`)
すべてのエラーコードは **先頭1文字（重大度）＋ 3桁の数字（`XYZ`）** で表す（旧 `0XX` 番台や文字列レガシーコードは廃止）。

### 先頭文字（重大度：ガードモニターの挙動を決定）
- **`F` (Force Stop)**: 即座にプロセス停止・作業中断を実行し、原因解析へ回す。
- **`M` (Minor Issue)**: 軽度問題として記録し処理を継続する（閾値超過時は `F123` で強制停止）。

### 百の位 `X`（領域・ドメイン分類）
- **`1XX` 〜 `5XX`【Core指定・固定領域】**（全プロジェクト共通。[`ERROR_CODES.md`](file:///C:/Users/Masaya.Futamata/Documents/Tusk_core_rb/Tusk_core/ERROR_CODES.md) で定義された番号のみ有効）
  - **`1XX`**: **Core**（テスト契約・成果物検証・監視整合性・手動停止）
  - **`2XX`**: **作業周り**（進捗ハング・反復ループ/手戻り上限・スコープ境界・セッション競合）
  - **`3XX`**: **データ周り**（入出力データ破損・ID/件数不一致・スキーマ検証）
  - **`4XX`**: **通信周り**（API認証・タイムアウト・レート制限・フォールバック）
  - **`5XX`**: **プロセス競合・他ソフト連携周り**（Supervisor消失・二重起動ロック・プロセス残留・外部アプリ異常）
- **`6XX` 〜 `9XX`【製品自由領域】**（Extension・製品仕様ごとに自由に割り当て可能）
  - ガードモニターは **`[F|M][6-9][0-9]{2}` の形式と必須フィールドさえ満たしていれば、製品が何であれ無条件で正規コードとして受理**し、`F` なら強制停止、`M` なら軽度問題カウントとして同一挙動で処理する。

### 十の位 `Y`・一の位 `Z`（サブ分類と連番）
- **`X0Z`**: 基本エラー・契約/入出力エラー
- **`X1Z` 〜 `X2Z`**: 状態異常・閾値超過・競合エラー
- **`X8Z`**: 人間介入・UI/コンソール起因

---

## 2. 構造化ログマーカー文法
監視対象プロセスは、以下の1行マーカーをログへ出力する。

### 強制停止 (`TUSK_FORCE_STOP`)
```text
[TUSK_FORCE_STOP] run_id=<id> code=F201 component=<name> step=<step> reason=<no_space_reason>
```

### 軽度問題 (`TUSK_MINOR_ISSUE`)
```text
[TUSK_MINOR_ISSUE] run_id=<id> code=M301 component=<name> step=<step> target=<target> detail=<no_space_detail>
```

### 進捗報告 (`TUSK_PROGRESS`)
```text
[TUSK_PROGRESS] run_id=<id> component=<name> step=<step> current=<int> total=<int|unknown>
```

- `F182`（ユーザー手動停止）はガードモニターのコンソール `/stop` コマンド専用であり、ログマーカーからの注入は拒否される。
