import argparse
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--act", required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--include-content", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    manifest = workspace / "work" / "context_cache" / args.act / "context_manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"manifest missing: {manifest}")
    payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
    query = args.query.casefold().strip()
    selected = []
    for record in payload.get("files", []):
        relative = str(record.get("path", ""))
        if query and query not in relative.casefold():
            continue
        item = dict(record)
        if args.include_content:
            path = (workspace / relative).resolve()
            try:
                item["content_prefix"] = path.read_text(encoding="utf-8")[:4096]
            except (OSError, UnicodeDecodeError):
                item["content_prefix"] = None
        selected.append(item)
        if len(selected) >= max(1, args.limit):
            break
    print(json.dumps({"act": args.act, "count": len(selected), "items": selected}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
