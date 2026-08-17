<!-- md-scope-document: COMMON -->
# Focus Cache: 地雷記録

## 目的

同じ失敗を繰り返さないため、失敗した箇所、原因、正解パターン、発生回数だけを保存する。成功、作業履歴、思考履歴、承認履歴、テスト証拠は保存しない。

## 正本

```text
work/focus_cache/LANDMINES.md
```

記録は次の固定形式とする。

```markdown
## <error_key>

- 発生回数: <1以上の整数>
- 地雷: <失敗する条件>
- 原因: <確認済み原因、未確定なら「調査中」>
- 正解パターン: <次回行うべき操作、未確定なら「調査中」>
- 対象: <機能またはworkspace相対パス>
- 最終確認: <YYYY-MM-DD>
```

例：

```markdown
## indesign.recovery_dialog_hang

- 発生回数: 1
- 地雷: InDesignの復元ダイアログでプロセスがハングする
- 原因: 異常終了後のリカバリキャッシュが残っている
- 正解パターン: 起動前に対象のInDesign Recoveryフォルダを消去する
- 対象: InDesign起動処理
- 最終確認: 2026-08-16
```

## 更新規則

- 新しい`error_key`だけ新規追加する。
- 同じ`error_key`は新規追加せず、`発生回数`を1加算して`最終確認`を更新する。
- 原因または正解パターンに新しい検証事実がある場合だけ本文を更新する。
- 推測した原因を確定表示しない。未確定は`調査中`とする。
- 解決済みでも削除しない。次回の回避確認に使う。
- 並び順は発生回数の降順、同数は`error_key`昇順とする。
- 保存は同一フォルダの一時ファイルへUTF-8で書き、flush後に原子的に置換する。
- 更新直前の正本を`LANDMINES.previous.md`として1世代だけ保持する。
- 秘密情報、会話全文、生の思考履歴、長いログを保存しない。

## 利用規則

- 修正開始時に対象と一致する地雷だけを読む。
- 地雷は注意事項であり、自動修正命令や成功証拠ではない。
- 成功時はFocus Cacheを更新しない。
- 原因調査や修正が失敗した場合だけ更新する。
- `error_key`を名称変更して同じ失敗を別件として登録しない。

## 廃止する機構

次はFocus Cacheの正本運用から廃止する。

- revision鎖
- reservation
- evidence、reasoning、decision、patternの種別
- promotion
- transient、handoff、推論スナップショット
- applicability、stale、dependency SHAの全件照合
- extension間共有
- 成功記録と成功ログ

旧Focus CacheのJSON、CLI、Schema、索引は移行証拠として保持できるが、新規作業では入力、更新、完了判定へ使用しない。
