# Tusk_core Gen2

AIは[AGENTS.md](AGENTS.md)から、
規則は[Tusk_core/POLICY.md](Tusk_core/POLICY.md)から読む。

Python 3.12とrequirements.txtの実行時依存を用意。
ライブラリとして使う場合は `Tusk_core` をimport pathへ置く。

```python
from runtime.recorder import Recorder

record = Recorder("/absolute/path/to/evidence")
record.start(
    {"source_ref": "owner-request", "text": "指定した変更をローカルで確認する"},
    "/absolute/path/to/source", ["app.py"],
    [{"path": "app.py", "contains": "def main"}],
    implementer="developer", owner="owner", risk="P1",
    classification={
        "components": ["app"],
        "paths": [{"path": "app.py", "component": "app", "effect": "modify"}],
        "operations": {key: False for key in (
            "external_app", "persistent_settings", "persistent_data", "migration",
            "release", "distribution", "installer", "update_or_uninstall",
            "destructive_or_irreversible", "security_boundary", "broad_user_data")},
        "surfaces": {key: False for key in (
            "security_boundary", "authentication", "secrets", "distribution_installer",
            "destructive_operation", "user_data", "persistent_schema", "process_stop",
            "external_app")},
    },
)
record.open(actor="developer")
# この間に、指定範囲のコードを編集する。
record.result(actor="developer")
record.verify_static(actor="developer")
record.close(actor="owner")
```

classificationはscopeの各ファイルの作用、操作の種類、保護面の申告。Coreは申告とprofileの規則で
ファイル内容から判定した結果の厳しい方から下限を計算し、下限より低いriskを拒否する。
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

Coreは共通workflow、記録、静的条件の検査、復帰・予算の検査を提供。
本人認証、任意codeの隔離、モデル起動、テスト実行、repo接続、配布組立は提供しない。
実行結果と担当identityは信頼されたローカル呼出側の申告として扱う。

配布物と公開ソースには試験や開発記録を含めない。追加・欠落したファイルや内容変更がある場合は公開前検査をやり直す。

Apache License 2.0。LICENSEとNOTICEを参照。
