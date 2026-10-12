# Tusk_core Gen2

Coreと動作に必要な最小構成を配布する。AIは[AGENTS.md](AGENTS.md)から、
規則は[Tusk_core/POLICY.md](Tusk_core/POLICY.md)から読む。

Python 3.12とrequirements.txtの実行時依存を用意する。
ライブラリとして使う場合は `Tusk_core` をimport pathへ置く。
Coreの設置先と作業対象、記録先は分ける。記録版は5であり、旧記録を自動変換しない。

```python
from runtime.recorder import Recorder

record = Recorder("/absolute/path/to/evidence")
record.start(
    {"source_ref": "owner-request", "text": "指定した変更をローカルで確認する"},
    "/absolute/path/to/source", ["app.py"],
    [{"path": "app.py", "contains": "def main"}],
    implementer="developer", owner="owner",
)
record.open(actor="developer")
# この間に、指定範囲のコードを編集する。
record.result(actor="developer")
record.verify_static(actor="developer")
record.close(actor="owner")
```

上の静的確認は指定した内容条件だけを検査する。機能試験が必要ならplanのchecksへ
明示し、外部の試験結果を対象snapshotと結合して取り込む。
P2以上、保護対象、公開候補では独立reviewが必要となる。
実行、復元、公開、切替は外側の操作機構と明示承認を使う。

```powershell
Push-Location Tusk_core
python -m pip install -r requirements.txt
python -B -m runtime.cli status --state C:\workspace\evidence
Pop-Location
```

Coreは共通workflow、記録、静的条件の検査、復帰・予算の検査を提供する。
本人認証、任意codeの隔離、モデル起動、テスト実行、repo接続、配布組立は提供しない。
実行結果と担当identityは信頼されたローカル呼出側の申告として扱う。
実行機構を持たない環境では該当操作を起動できない。

配布物と公開ソースには試験や開発記録を含めない。追加・欠落したファイルや内容変更が
ある場合は公開前検査をやり直す。通常のlocal完了は公開未評価である。

Apache License 2.0。LICENSEとNOTICEを参照。
