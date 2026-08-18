<!-- md-scope-document: TUSK_WORKSPACE_MIGRATOR -->
# Workspace Migrator Specification

## Purpose

旧Tusk Coreの構造を現行Coreへ上書きせず、旧Extensionの静的資産だけを
レビュー可能なstageへ複製する。旧`work/runs`は件数とパスだけをinventoryし、
成功証拠、現行Cache、active Extensionへ昇格しない。

## Commands

- `inspect`: 読み取り専用。候補Extension、対象ファイル、除外件数、旧run件数、
  conflictをJSONで返す。
- `stage --apply`: 選択した候補を
  `<workspace>/work/migrations/<migration-id>/staged_extensions/`へ新規作成する。

## Selection

- 候補は`<legacy-root>/extensions/Tusk_*`直下だけ。
- `AGENTS.md`を持つ候補だけstage可能。
- `work`、`archive`、build、dist、node_modules、仮想環境、Cache、秘密値、
  bytecode、既存manifestは複製しない。
- symlink、junction、reparse pointは走査・複製しない。
- stageした静的ファイルから新しい`EXTENSION-MANIFEST.json`を生成し、入口、
  top-level Spec、エラーコードの`required_read_order`を保持する。

## Safety

- legacy rootとworkspaceは別の既存絶対ディレクトリでなければならない。
- legacy rootは一切変更しない。
- active `extensions/`、Core、Sharpener、Runtime Adapterは変更しない。
- 既存migration IDまたは既存stage先を上書きしない。
- stageは一時ディレクトリへ作成後、同一親内のrenameで確定する。
- stage成功はExtensionの導入、有効化、runtime、UI、E2E成功を証明しない。

## Output

結果は`schema_version`、`state`、`legacy_root`、`workspace`、
`migration_id`、候補・stage済みExtension、除外一覧、旧run件数を持つJSONとする。
情報不足、競合、危険パスは`state:needs_review`で停止する。
