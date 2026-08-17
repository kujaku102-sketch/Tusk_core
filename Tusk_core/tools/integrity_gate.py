from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def default_store() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise ValueError("LOCALAPPDATA is unavailable")
    return Path(base) / "Tusk" / "trusted_developer_keys.json"


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".tusk-trust-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_key(key: dict) -> None:
    if set(key) != {"schema_version", "authority_id", "workspace_id", "allowed_scopes"}:
        raise ValueError("invalid developer key fields")
    if key["schema_version"] != 1 or not isinstance(key["authority_id"], str) or not key["authority_id"]:
        raise ValueError("invalid developer key")
    scopes = key["allowed_scopes"]
    if not isinstance(scopes, list) or not scopes or len(scopes) != len(set(scopes)):
        raise ValueError("invalid allowed_scopes")
    for scope in scopes:
        path = Path(scope)
        if not isinstance(scope, str) or path.is_absolute() or ".." in path.parts or "\\" in scope:
            raise ValueError("invalid scope")


def trust(workspace: Path, key_path: Path, store_path: Path) -> dict:
    root = workspace.resolve(strict=True)
    key_file = key_path.resolve(strict=True)
    if key_file.parent != root:
        raise ValueError("developer key must be directly below workspace")
    key = load_json(key_file)
    validate_key(key)
    store = load_json(store_path) if store_path.exists() else {"schema_version": 1, "authorities": {}}
    if store.get("schema_version") != 1 or not isinstance(store.get("authorities"), dict):
        raise ValueError("invalid trust store")
    store["authorities"][key["authority_id"]] = {
        "key_sha256": digest(key_file),
        "workspace_root": root.as_posix(),
    }
    atomic_json(store_path, store)
    return key


def authorized(workspace: Path, key_path: Path, store_path: Path, scope: str, mode: str) -> bool:
    if mode != "development" or not store_path.is_file():
        return False
    root = workspace.resolve(strict=True)
    key_file = key_path.resolve(strict=True)
    if key_file.parent != root:
        return False
    key = load_json(key_file)
    validate_key(key)
    stored = load_json(store_path).get("authorities", {}).get(key["authority_id"])
    return bool(
        stored
        and stored.get("key_sha256") == digest(key_file)
        and stored.get("workspace_root") == root.as_posix()
        and scope in key["allowed_scopes"]
    )


def verify_manifest(package_root: Path, manifest_path: Path) -> list[str]:
    root = package_root.resolve(strict=True)
    manifest = load_json(manifest_path.resolve(strict=True))
    if manifest.get("algorithm") != "sha256" or not isinstance(manifest.get("managed_files"), list):
        raise ValueError("invalid manifest")
    mismatches: list[str] = []
    for item in manifest["managed_files"]:
        relative = item.get("path")
        expected = item.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError("invalid manifest row")
        target = root / relative
        try:
            resolved = target.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError):
            mismatches.append(relative)
            continue
        if not resolved.is_file() or digest(resolved) != expected.lower():
            mismatches.append(relative)
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser(prog="tusk-integrity")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--key", type=Path)
    parser.add_argument("--trust-store", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("trust")
    check = sub.add_parser("check")
    check.add_argument("--scope", required=True)
    check.add_argument("--mode", choices=("development", "release"), required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--scope", required=True)
    verify.add_argument("--mode", choices=("development", "release"), required=True)
    verify.add_argument("--package-root", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    key_path = args.key or workspace / "developer.key.json"
    store_path = args.trust_store or default_store()
    if args.command == "trust":
        key = trust(workspace, key_path, store_path)
        print(f"trusted={key['authority_id']}")
        return 0
    allowed = authorized(workspace, key_path, store_path, args.scope, args.mode)
    if args.command == "check":
        print(f"authorized={str(allowed).lower()}")
        return 0 if allowed else 3
    mismatches = verify_manifest(args.package_root, args.manifest)
    if not mismatches:
        print("integrity=ok")
        return 0
    for value in mismatches:
        print(f"mismatch={value}")
    if allowed:
        print("integrity=development-warning")
        return 0
    print("integrity=failed")
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
