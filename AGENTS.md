# Tusk-flash

Antigravity上のGemini Flashを、単独実行または最大3つの非重複Task Sliceへ分割して使う。

1. `policy/GRAMMAR.md`を読む。
2. `runtime/context_cache.py`で現在の構造を取得する。
3. `runtime/task_splitter.py`で`DIRECT`、`SPLIT`、`STOP`を決定する。
4. `SPLIT`では各子の`writable_paths`を重複させない。
5. 子は指定範囲だけを編集し、`agent_result.schema.json`準拠の結果を返す。
6. `runtime/test_guard.py`を通してfocused testを実行する。
7. コードまたは契約不良の修正は最大2回。同一失敗の再発、保護対象、破壊操作、認証・秘密情報は`STOP`とする。

成功時は結果だけを返す。失敗時はコード、対象Slice、短いログ、次の行動を返す。推論履歴、成功ログ、無関係な文書を保存しない。
