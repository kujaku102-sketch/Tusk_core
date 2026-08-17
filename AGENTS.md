<!-- md-scope-document: COMMON -->
# Tusk workspace bootloader

1. `Tusk_core/START-HERE.md`と`Tusk_core/AGENTS.md`を読む。
2. `Tusk_sharpener/sharpener.py check --target Tusk_core`が`healthy`、または明示的waiverであることを確認する。
3. `Tusk_core/extensions.json`とローカルactivationを照合する。
4. manifest検証済みで有効なExtensionだけを読む。
5. 現在のtask、現行Spec、Git diff、必要なCacheから実行範囲を導出する。

Coreへ製品固有規則を入れない。Extension、Runtime Adapter、Cache、Sharpenerの責務を混在させない。

