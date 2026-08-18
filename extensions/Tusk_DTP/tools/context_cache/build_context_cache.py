import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


EXCLUDED = {"archive", "runtime", "release", "work", "__pycache__", ".git"}
ACT_ROOTS = {
    "act1": "統合ソース/Act1Runtime",
    "act1dev": "統合ソース",
    "act2": "統合ソース",
    "act3": "統合ソース/AppSourceRuntime",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def iter_files(root):
    for directory, names, files in os.walk(root):
        names[:] = [name for name in names if name.casefold() not in EXCLUDED]
        base = Path(directory)
        for name in files:
            path = base / name
            if path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024:
                continue
            yield path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--act", required=True, choices=sorted(ACT_ROOTS))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    source = workspace / ACT_ROOTS[args.act]
    if not source.is_dir():
        raise SystemExit(f"scope root missing: {source}")
    paths = list(iter_files(source))
    target = workspace / "work" / "context_cache" / args.act / "context_manifest.json"
    if args.dry_run:
        print(json.dumps({"act": args.act, "source": str(source), "files": len(paths), "target": str(target), "dry_run": True}, ensure_ascii=False))
        return 0
    records = []
    for path in paths:
        relative = path.relative_to(workspace).as_posix()
        records.append({
            "path": relative,
            "size": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns,
            "sha256": sha256(path),
        })
    records.sort(key=lambda item: item["path"].casefold())
    print(json.dumps({"act": args.act, "source": str(source), "files": len(records), "target": str(target), "dry_run": args.dry_run}, ensure_ascii=False))
    payload = {
        "schema_version": 1,
        "scope_key": args.act,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_root": str(source),
        "files": records,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
