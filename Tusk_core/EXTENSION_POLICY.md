<!-- md-scope-document: COMMON -->
# Extension・Skill・キャッシュ共通規約

## 1. 正本と責務
Coreは製品固有の規則を持たず、共通契約と安全基盤だけを所有する。
Extensionは製品仕様、ドメイン知識、接続設定、Skill、製品別Cacheを所有する。

## 2. Extensionの標準配置と宣言 (`extensions/Tusk_<name>/`)

```text
<workspace>/
  extensions/Tusk_<name>/
    EXTENSION-MANIFEST.json
    AGENTS.md
    products/<product_id>/
    skills/<skill_id>/SKILL.md
    focus_cache/
```

- **選択的読込**: `work/settings/extensions.enabled.json` で有効化され、`EXTENSION-MANIFEST.json` のSHA-256検証を通過したExtensionの `AGENTS.md` だけを読む。フォルダが存在するだけの未有効化Extensionは読まない。
- **制作・追加の5ステップ**:
  1. 既存のExtension・製品・Skillで扱えるか確認し、重複正本を作らない。
  2. 製品仕様、入出力、変更可能範囲、成功条件、必須検証を定義する。
  3. 宣言と `EXTENSION-MANIFEST.json` を整備し、パス安全性とSHA-256を検証する。
  4. 最小の独立動作を確認し、関連回帰テストを通す。
  5. `tusk_manager.py ext install` / `enable` で有効化する。
- **必須 Extension**: `tusk_manager.py` (実体は `extensions/Tusk_Basic_skills/skills/tusk-manager/scripts/tusk_manager.py`) を収録する `Tusk_Basic_skills` は常に有効とし、無効化・削除しない (`tusk_manager` も拒否する)。`init` は `extensions/Tusk_Basic_skills` があれば有効一覧に入れる。

## 3. Skill整備規則 (`skills/<skill_id>/SKILL.md`)
- Skillは繰り返し使う作業手順とツール接続をまとめる。製品仕様やCore規則の全文を `SKILL.md` に複製せず、正本への参照を記載する。
- `SKILL.md` には名前、目的、発動条件、対象外、入出力、実行手順、検証方法を記載する。
- 実行時は今回の作業に該当するSkillだけを読む。無関係な `references/` は読み込まない。
- 単発の未検証対策を既定手順にしない。反復失敗が既存手順の不足に起因する場合は新規Skillを乱造せず既存Skillを更新する。

## 4. Context Cache（コンテキストキャッシュ：差分・構造索引）
大規模な制作物を毎回全文走査せず、現在の構成と変更差分（`added` / `modified` / `unchanged` / `deleted`）だけを特定するためのスコープ単位キャッシュ。

- **保存先**: `work/context_cache/<scope_key>/context_manifest.json`（全体一覧は `work/context_cache/common/workspace_manifest.json`）
- **スコープ定義**: `work/settings/context_scopes.json` に `scope_key` ごとの `source_root` と `inputs` を定義する。
- **運用手順**:
  1. 作業開始時に `tusk_manager.py context --scope <scope_key>`（dry-run）で前回キャッシュからの差分（追加・変更・削除ファイル）を確認する。
  2. 対象が正しければ `--write` で `context_manifest.json` を更新し、**未変更 (`unchanged`) ファイルの全文再読込をスキップして変更分と直接参照仕様だけを読む**。
  3. `AGENTS.md` や対象仕様、ディレクトリ構成が変わった場合、またはSHA不一致が起きた場合はキャッシュを無効化して原本を確認する。
- **安全境界**: コンテキストキャッシュは原本の索引であり、テスト合格や完成判定の証拠にはならない。`.git`、`__pycache__`、`.env`、秘密鍵（`.pem`, `.key`, `credentials.json` 等）は走査対象から自動除外する。

## 5. Focus Cache（フォーカスキャッシュ：既知の地雷・再発防止）
実装・テスト・運用で確認した「既知の失敗パターン（地雷）」と「検証済み対策」を記録し、同じ轍を踏まないためのキャッシュ。

- **保存先**:
  - 共通または単体作業の地雷: `work/focus_cache/LANDMINES.md`（[`tools/landmine_cache.py`](file:///C:/Users/Masaya.Futamata/Documents/Tusk_core_rb/Tusk_core/tools/landmine_cache.py) で記録）
  - 特定Extension固有の地雷: `extensions/Tusk_<name>/focus_cache/LANDMINES.md`
- **必須項目**: `error_key`、`発生回数`、`地雷`（症状・発生条件）、`原因`（未確定なら `調査中`）、`正解パターン`、`対象`、`最終確認`（日付）。
- **Context Cacheとの違い**:
  - **Context Cache** ＝ 「どのファイルが存在し、どれが変更されたか」の**構造・差分索引**。
  - **Focus Cache** ＝ 「過去にどう壊れ、どう直したか」の**失敗・地雷知識**。
