from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


NAME_RE = re.compile(r"^Tusk_[A-Za-z0-9._-]+$")


def default_paths() -> tuple[Path, Path]:
    core = Path(__file__).resolve().parents[1]
    architecture = core.parent
    return architecture / "extensions", architecture / "work" / "settings" / "extensions.enabled.json"


def discover(extension_root: Path) -> list[str]:
    if not extension_root.is_dir():
        return []
    return sorted(p.name for p in extension_root.iterdir() if p.is_dir() and NAME_RE.fullmatch(p.name))


def validate(extension_root: Path, name: str) -> Path:
    if not NAME_RE.fullmatch(name):
        raise ValueError("invalid extension name")
    root = extension_root / name
    manifest_path = root / "EXTENSION-MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("root") != name or manifest.get("algorithm") != "sha256":
        raise ValueError("invalid extension manifest")
    for item in manifest.get("managed_files", []):
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("unsafe managed path")
        target = root / rel
        if not target.is_file():
            raise FileNotFoundError(str(target))
        if hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"sha mismatch: {item['path']}")
    entry = root / manifest["entry"]
    if not entry.is_file():
        raise FileNotFoundError(str(entry))
    return manifest_path


def load_registry(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "enabled_extensions": [], "disabled_extensions": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_registry(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def set_enabled(extension_root: Path, registry_path: Path, name: str, enabled: bool) -> dict:
    data = load_registry(registry_path)
    rows = {row["id"]: row for row in data.get("enabled_extensions", [])}
    disabled = set(data.get("disabled_extensions", []))
    if enabled:
        manifest = validate(extension_root, name)
        rows[name.lower()] = {"id": name.lower(), "manifest": os.path.relpath(manifest, registry_path.parent).replace("\\", "/")}
        disabled.discard(name.lower())
    else:
        rows.pop(name.lower(), None)
        disabled.add(name.lower())
    data["schema_version"] = 1
    data["enabled_extensions"] = [rows[key] for key in sorted(rows)]
    data["disabled_extensions"] = sorted(disabled)
    save_registry(registry_path, data)
    return data


def main() -> int:
    extension_root, registry_path = default_paths()
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("list", "enable", "disable"))
    parser.add_argument("name", nargs="?")
    parser.add_argument("--extension-root", type=Path, default=extension_root)
    parser.add_argument("--registry", type=Path, default=registry_path)
    args = parser.parse_args()
    if args.action == "list":
        enabled = {row["id"] for row in load_registry(args.registry).get("enabled_extensions", [])}
        print(json.dumps({"available": discover(args.extension_root), "enabled": sorted(enabled)}, ensure_ascii=False))
        return 0
    if not args.name:
        parser.error("name is required")
    print(json.dumps(set_enabled(args.extension_root, args.registry, args.name, args.action == "enable"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
