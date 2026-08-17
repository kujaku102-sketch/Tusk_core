# Tusk-flash

Antigravity上のGemini Flashに特化した、独立・軽量なTuskディストリビューション。

- 文法準拠の構造化入出力
- 現在構造だけを保存するContext Cache
- 最大3子への責務分割と並列起動
- timeout、終了コード、文法違反を検出するTest Guard

Extension、複数Provider、Sharpener、Focus Cache、承認階層は持たない。

## Quick check

```powershell
python -m unittest discover -s tests -p "test_*.py"
python runtime/context_cache.py --root . --output work/context/project.json
```

`agy`がPATHにあればGemini 3.6 Flash Mediumを既定で使う。変更する場合だけ`TUSK_FLASH_AGENT_COMMAND`へ、`{slice}`と`{result}`を含むAntigravity起動コマンドをJSON文字列配列で設定する。shell文字列は実行しない。

既定起動は`--sandbox`を使用する。`runtime/antigravity.permissions.example.json`を参考に、Slice読込とfocused testに必要なコマンドだけをAntigravityの`permissions.allow`へ事前追加する。既存`settings.json`を上書きせず、`allow`配列へ必要項目だけをマージする。`--dangerously-skip-permissions`は使用しない。

```powershell
$env:TUSK_FLASH_AGENT_COMMAND = '["your-command","--task","{slice}","--output","{result}"]'
python runtime/orchestrator.py run --plan work/tasks/plan.json
```

Tusk-flashはGoogle、Antigravityその他の提供者による公式・提携・認定製品ではない。名称は互換対象の識別だけに使用する。

Apache License 2.0。詳細は`LICENSE`を参照。
