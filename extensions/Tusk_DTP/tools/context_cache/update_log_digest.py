import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest().upper()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--act", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    log_roots = [workspace / "統合ソース" / "logs", workspace / "logs"]
    logs = []
    for root in log_roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.stat().st_size <= 8 * 1024 * 1024:
                logs.append(path)
    logs.sort(key=lambda path: (path.stat().st_mtime_ns, str(path).casefold()))
    target = workspace / "work" / "context_cache" / "common" / "log_index.jsonl"
    print(json.dumps({"act": args.act, "logs": len(logs), "target": str(target), "dry_run": args.dry_run}, ensure_ascii=False))
    if args.dry_run:
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for path in logs:
        lines.append(json.dumps({
            "scope": args.act,
            "path": path.relative_to(workspace).as_posix(),
            "size": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns,
            "sha256": digest(path),
            "indexed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }, ensure_ascii=False))
    temporary = target.with_suffix(".jsonl.tmp")
    temporary.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    os.replace(temporary, target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
