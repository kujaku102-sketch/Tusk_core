from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


NAME_RE = re.compile(r"^Tusk_[A-Za-z0-9._-]+$")


def get_default_workspace() -> Path:
    return Path.cwd()


def calculate_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------
# 1. 初期導入 (Init / Bootstrap)
# ---------------------------------------------------------
def init_workspace(workspace: Path, core_source: Optional[Path] = None) -> Dict[str, Any]:
    ws = workspace.resolve()
    ws.mkdir(parents=True, exist_ok=True)

    # 1. 必須ディレクトリ構造作成
    (ws / "work" / "settings").mkdir(parents=True, exist_ok=True)
    (ws / "work" / "focus_cache").mkdir(parents=True, exist_ok=True)
    (ws / "extensions").mkdir(parents=True, exist_ok=True)

    # 2. 初期設定ファイル
    enabled_json = ws / "work" / "settings" / "extensions.enabled.json"
    if not enabled_json.exists():
        enabled_json.write_text(
            json.dumps({"schema_version": 1, "enabled_extensions": [], "disabled_extensions": []}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )

    # 3. 初期LANDMINES.md
    landmines_md = ws / "work" / "focus_cache" / "LANDMINES.md"
    if not landmines_md.exists():
        landmines_md.write_text("# Focus Cache: 地雷一覧\n\n", encoding="utf-8")

    # 4. developer.key.json (開発用デフォルトキー)
    dev_key = ws / "developer.key.json"
    if not dev_key.exists():
        key_data = {
            "key_id": "local-dev-default",
            "mode": "development",
            "allowed_scopes": ["COMMON", "IDTASK", "TUSK_SZ", "TUSK_DTP"],
            "created_at": "2026-08-16"
        }
        dev_key.write_text(json.dumps(key_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 5. Coreの配置 (指定があればコピー)
    core_installed = False
    if core_source and core_source.is_dir() and core_source != (ws / "Tusk_core"):
        dest_core = ws / "Tusk_core"
        if not dest_core.exists():
            shutil.copytree(core_source, dest_core, ignore=shutil.ignore_patterns("__pycache__", ".git", "*.tmp"))
            core_installed = True

    return {
        "status": "success",
        "action": "init",
        "workspace": str(ws),
        "created_files": [
            str(enabled_json.relative_to(ws)),
            str(landmines_md.relative_to(ws)),
            str(dev_key.relative_to(ws))
        ],
        "core_installed": core_installed
    }


# ---------------------------------------------------------
# 2. 拡張機能管理 (Extension Management)
# ---------------------------------------------------------
def list_extensions(workspace: Path) -> Dict[str, Any]:
    ws = workspace.resolve()
    ext_dir = ws / "extensions"
    enabled_json = ws / "work" / "settings" / "extensions.enabled.json"

    available: List[str] = []
    if ext_dir.is_dir():
        available = sorted(p.name for p in ext_dir.iterdir() if p.is_dir() and NAME_RE.fullmatch(p.name))

    enabled_ids: List[str] = []
    disabled_ids: List[str] = []
    if enabled_json.exists():
        try:
            data = json.loads(enabled_json.read_text(encoding="utf-8"))
            enabled_ids = [row["id"] for row in data.get("enabled_extensions", [])]
            disabled_ids = data.get("disabled_extensions", [])
        except Exception:
            pass

    return {
        "workspace": str(ws),
        "available_extensions": available,
        "enabled_extensions": enabled_ids,
        "disabled_extensions": disabled_ids
    }


def validate_extension_manifest(ext_path: Path) -> Dict[str, Any]:
    name = ext_path.name
    if not NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid extension folder name: {name}")
    manifest_path = ext_path / "EXTENSION-MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("root") != name or manifest.get("algorithm") != "sha256":
        raise ValueError("Invalid extension manifest root or algorithm")

    for item in manifest.get("managed_files", []):
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"Unsafe path in manifest: {item['path']}")
        target = ext_path / rel
        if not target.is_file():
            raise FileNotFoundError(f"Managed file missing: {target}")
        if calculate_sha256(target) != item["sha256"]:
            raise ValueError(f"SHA mismatch: {item['path']}")

    return manifest


def install_extension(workspace: Path, source_path: Path, enable: bool = True) -> Dict[str, Any]:
    ws = workspace.resolve()
    src = source_path.resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"Source directory not found: {src}")

    name = src.name
    if not NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid extension name: {name}")

    dest = ws / "extensions" / name
    if dest.exists():
        shutil.rmtree(dest)

    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", ".git", "*.tmp"))

    # マニフェスト検証
    validate_extension_manifest(dest)

    if enable:
        set_extension_enabled(workspace, name, True)

    return {
        "status": "success",
        "action": "install",
        "extension": name,
        "path": str(dest),
        "enabled": enable
    }


def set_extension_enabled(workspace: Path, name: str, enabled: bool) -> Dict[str, Any]:
    ws = workspace.resolve()
    ext_dir = ws / "extensions"
    enabled_json = ws / "work" / "settings" / "extensions.enabled.json"

    data = {"schema_version": 1, "enabled_extensions": [], "disabled_extensions": []}
    if enabled_json.exists():
        try:
            data = json.loads(enabled_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    rows = {row["id"]: row for row in data.get("enabled_extensions", [])}
    disabled = set(data.get("disabled_extensions", []))
    ext_key = name.lower()

    if enabled:
        ext_path = ext_dir / name
        if not ext_path.is_dir():
            raise FileNotFoundError(f"Extension not found: {name}")
        validate_extension_manifest(ext_path)
        manifest_rel = f"../../extensions/{name}/EXTENSION-MANIFEST.json"
        rows[ext_key] = {"id": ext_key, "manifest": manifest_rel}
        disabled.discard(ext_key)
    else:
        rows.pop(ext_key, None)
        disabled.add(ext_key)

    data["schema_version"] = 1
    data["enabled_extensions"] = [rows[k] for k in sorted(rows)]
    data["disabled_extensions"] = sorted(disabled)

    enabled_json.parent.mkdir(parents=True, exist_ok=True)
    temp = enabled_json.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, enabled_json)

    return {
        "status": "success",
        "action": "enable" if enabled else "disable",
        "extension": name,
        "enabled": enabled
    }


def remove_extension(workspace: Path, name: str) -> Dict[str, Any]:
    ws = workspace.resolve()
    dest = ws / "extensions" / name

    # 1. 先に無効化
    try:
        set_extension_enabled(workspace, name, False)
    except Exception:
        pass

    # 2. フォルダ削除
    if dest.exists():
        shutil.rmtree(dest)

    return {
        "status": "success",
        "action": "remove",
        "extension": name
    }


# ---------------------------------------------------------
# 3. アプデ確認・検証 (Update / Check)
# ---------------------------------------------------------
def check_updates(workspace: Path) -> Dict[str, Any]:
    ws = workspace.resolve()
    results: Dict[str, Any] = {"workspace": str(ws), "components": {}}

    # 1. Core検証
    core_dir = ws / "Tusk_core"
    core_manifest = core_dir / "DISTRIBUTION-MANIFEST.json"
    if core_manifest.is_file():
        try:
            m_data = json.loads(core_manifest.read_text(encoding="utf-8"))
            mismatches = []
            for item in m_data.get("managed_files", []):
                p = core_dir / item["path"]
                if not p.is_file() or calculate_sha256(p) != item["sha256"]:
                    mismatches.append(item["path"])
            results["components"]["Tusk_core"] = {
                "version": m_data.get("version", "unknown"),
                "status": "up_to_date" if not mismatches else "modified",
                "modified_files": mismatches
            }
        except Exception as e:
            results["components"]["Tusk_core"] = {"status": "error", "error": str(e)}

    # 2. 有効化拡張検証
    ext_list = list_extensions(ws)
    for ext_name in ext_list["available_extensions"]:
        ext_dir = ws / "extensions" / ext_name
        manifest_path = ext_dir / "EXTENSION-MANIFEST.json"
        if manifest_path.is_file():
            try:
                m_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                mismatches = []
                for item in m_data.get("managed_files", []):
                    p = ext_dir / item["path"]
                    if not p.is_file() or calculate_sha256(p) != item["sha256"]:
                        mismatches.append(item["path"])
                results["components"][ext_name] = {
                    "status": "up_to_date" if not mismatches else "modified",
                    "modified_files": mismatches
                }
            except Exception as e:
                results["components"][ext_name] = {"status": "error", "error": str(e)}

    return results


# ---------------------------------------------------------
# 4. アンインストーラ (Uninstall / Clean)
# ---------------------------------------------------------
def uninstall_workspace(workspace: Path, purge: bool = False) -> Dict[str, Any]:
    ws = workspace.resolve()
    removed = []

    if purge:
        # 完全削除 (ワークスペースごと)
        if ws.exists():
            shutil.rmtree(ws)
            removed.append(str(ws))
    else:
        # 設定・一時ファイル・キャッシュのクリーン削除
        for target_dir in [ws / "work", ws / "tmp"]:
            if target_dir.exists():
                shutil.rmtree(target_dir)
                removed.append(str(target_dir))
        for target_file in [ws / "developer.key.json"]:
            if target_file.exists():
                target_file.unlink()
                removed.append(str(target_file))

    return {
        "status": "success",
        "action": "uninstall",
        "purge": purge,
        "removed_paths": removed
    }


# ---------------------------------------------------------
# CLI エントリーポイント
# ---------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tusk Workspace & Extension Manager")
    parser.add_argument("--workspace", type=Path, default=get_default_workspace(), help="Target workspace path")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. init
    init_parser = subparsers.add_parser("init", help="Initialize workspace with Core baseline")
    init_parser.add_argument("--core-source", type=Path, help="Path to Tusk_core source to copy")

    # 2. ext
    ext_parser = subparsers.add_parser("ext", help="Manage extensions")
    ext_sub = ext_parser.add_subparsers(dest="ext_command", required=True)
    ext_sub.add_parser("list", help="List extensions")

    inst_p = ext_sub.add_parser("install", help="Install extension from directory")
    inst_p.add_argument("source", type=Path, help="Extension source folder")
    inst_p.add_argument("--no-enable", action="store_true", help="Do not enable after install")

    en_p = ext_sub.add_parser("enable", help="Enable an extension")
    en_p.add_argument("name", help="Extension folder name")

    dis_p = ext_sub.add_parser("disable", help="Disable an extension")
    dis_p.add_argument("name", help="Extension folder name")

    rem_p = ext_sub.add_parser("remove", help="Remove an extension")
    rem_p.add_argument("name", help="Extension folder name")

    # 3. update
    up_parser = subparsers.add_parser("update", help="Check and apply updates")
    up_parser.add_argument("--check", action="store_true", help="Only check for updates without applying")

    # 4. uninstall
    un_parser = subparsers.add_parser("uninstall", help="Uninstall workspace / Clean temporary files")
    un_parser.add_argument("--purge", action="store_true", help="Purge entire workspace directory")
    un_parser.add_argument("--force", action="store_true", help="Force without confirmation")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    ws: Path = args.workspace

    try:
        if args.command == "init":
            res = init_workspace(ws, args.core_source)
        elif args.command == "ext":
            if args.ext_command == "list":
                res = list_extensions(ws)
            elif args.ext_command == "install":
                res = install_extension(ws, args.source, enable=not args.no_enable)
            elif args.ext_command == "enable":
                res = set_extension_enabled(ws, args.name, True)
            elif args.ext_command == "disable":
                res = set_extension_enabled(ws, args.name, False)
            elif args.ext_command == "remove":
                res = remove_extension(ws, args.name)
            else:
                parser.error("Unknown ext subcommand")
        elif args.command == "update":
            res = check_updates(ws)
        elif args.command == "uninstall":
            if not args.force and not args.json:
                confirm = input(f"Are you sure you want to uninstall {'(PURGE ENTIRE WORKSPACE)' if args.purge else ''} at {ws}? [y/N]: ")
                if confirm.lower() != "y":
                    print("Cancelled.")
                    return 1
            res = uninstall_workspace(ws, purge=args.purge)
        else:
            parser.error("Unknown command")

        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"[{res.get('status', 'OK').upper()}] {args.command} completed.")
            print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "error": str(e)}, indent=2, ensure_ascii=False))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
