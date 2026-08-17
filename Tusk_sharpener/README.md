<!-- md-scope-document: COMMON -->
# Tusk Sharpener

Tusk自身のIntegrity / Authenticity / Consistencyを独立して検査する。

```powershell
python sharpener.py check --target ..\Tusk_core
python sharpener.py check --target ..\Tusk_core --workspace .. --output work\sharpener-report.json
python sharpener.py report --input work\sharpener-report.json
python sharpener.py repair --target ..\Tusk_core --action manifest_hashes
```

初版の監査対象は参照整合性、authority競合、manifest/catalog、ERROR_CODES、TEST-MAP、キャッシュ鮮度の6系統。`repair`は既存manifest行のSHA-256再計算だけを実装し、行追加・削除や規範変更は行わない。

