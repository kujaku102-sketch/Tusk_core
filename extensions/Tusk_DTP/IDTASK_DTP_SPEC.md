<!-- md-scope-document: IDTASK -->
# IdTask 固有 DTP パイプライン仕様拡張

正本パス: `extensions/Tusk_DTP/IDTASK_DTP_SPEC.md`

## 1. 概要
本ドキュメントは `Tusk_core` の共通ルールから分離された、IdTask固有のDTP・InDesign・翻訳パイプライン・エラーログ文法・フォーカスキャッシュおよびコンテキストキャッシュの実装バインド仕様を定義する。

---

## 2. IdTask固有規則と昇格条件 (`GENERAL.md` 由来)

### IdTask強制昇格条件
以下の処理が伴うタスクの作業強度は常に `MAX` とする：
- InDesign、COM接続、プロセス停止、監視安全装置、インストーラ、ビルド、配布物作成、データ削除・移動、TSVのID・順序・原文、翻訳メモリ、学習データ確定処理

### IdTaskログ文法
新規コードは以下の完全形式を1行で出力し、直後にログをflushすること：
```text
[IDTASK_FORCE_STOP] code=Fxxx run_id=<RUN_ID> component=<COMPONENT> step=<STEP> reason=<REASON>
[IDTASK_MINOR_ISSUE] code=Mxxx run_id=<RUN_ID> component=<COMPONENT> step=<STEP> target=<TARGET> detail=<DETAIL>
```
- IdTask共通エラーコードの正本は `Tusk_DTP/ERROR_CODES.md` とする。
- 使用可能範囲は `F000-F199` および `M000-M199` とする。

### 共通監視ツール
- 現行実装: `IdTaskAct2/tools/test_guard_monitor.py`
- 正本: `IdTaskAct2/specs/029_common_test_guard_blueprint.md`
- 実行テストでは `--stop-on-force` を指定し、軽度問題の発生率（一意なtargetが全対象の20%以上、または新規Mログが50件以上）で `F123` を発行して強制停止する。

---

## 3. フォーカスキャッシュ IdTask実装バインド (`FOCUS_CACHE_SPEC.md` 由来)

- 実装状態: 🟡 `[進行中 / IN_PROGRESS]` (Spec-030)
- 引き継ぎ: `IdTaskAct2/specs/030_focus_cache_handoff.md`
- IdTask実装・進捗正本: `IdTaskAct2/specs/030_focus_cache_implementation_plan.md`
- 保存構成: `work/focus_cache/` 配下
- JSON Schema正本: `IdTaskAct2/tools/schemas/focus_cache_record.schema.json`
- ID形式: `FC-<SCOPE>-<SPEC>-<3桁連番>` （例: `FC-A1D-009-001`, `FC-A2-020-003`, `FC-COMMON-GEN-001`）

---

## 4. コンテキストキャッシュ IdTask現行バインド (`CONTEXT_CACHE_SPEC.md` 由来)

- 規模単位: Act (`act1`, `act1dev`, `act2`, `act3`)
- 配置: `work/context_cache/<act>/` （共通索引: `work/context_cache/common/`）
- IdTask固有正本: `IdTaskAct2/specs/016_idtask_context_cache_and_token_saving.md`
- Act別差分: `IdTaskAct2/context_cache/*_saving_plan.md`
- 生成・差分読込・ログ要約は `idtask-context-cache` スキルを使用し、必ず対象Actを1つ指定する。

---

## 5. 変更履歴
- 2026-08-10: `Tusk_core` の構造分離に伴い、`IDTASK` スコープセクションを抽出し本ファイルへ集約・新規作成。
