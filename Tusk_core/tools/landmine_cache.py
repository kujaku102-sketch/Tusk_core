from __future__ import annotations

import argparse
import os
import re
import tempfile
from datetime import date
from pathlib import Path


KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
FIELDS = ("発生回数", "地雷", "原因", "正解パターン", "対象", "最終確認")


def cache_path(workspace: Path) -> Path:
    root = workspace.resolve(strict=True)
    target = root / "work" / "focus_cache" / "LANDMINES.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.parent.resolve().is_relative_to(root):
        raise ValueError("cache path escapes workspace")
    return target


def parse(text: str) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            if not KEY_RE.fullmatch(current) or current in records:
                raise ValueError("invalid or duplicate error_key")
            records[current] = {}
        elif current and line.startswith("- ") and ": " in line:
            name, value = line[2:].split(": ", 1)
            if name in FIELDS:
                records[current][name] = value.strip()
    for key, values in records.items():
        if set(values) != set(FIELDS):
            raise ValueError(f"incomplete record: {key}")
        if not values["発生回数"].isdigit() or int(values["発生回数"]) < 1:
            raise ValueError(f"invalid count: {key}")
    return records


def render(records: dict[str, dict[str, str]]) -> str:
    ordered = sorted(records.items(), key=lambda item: (-int(item[1]["発生回数"]), item[0]))
    lines = ["# Focus Cache: 地雷一覧", ""]
    for key, values in ordered:
        lines.extend([f"## {key}", ""])
        for field in FIELDS:
            lines.append(f"- {field}: {values[field]}")
        lines.append("")
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    previous = path.with_name("LANDMINES.previous.md")
    if path.exists():
        old = path.read_bytes()
        fd, temporary = tempfile.mkstemp(prefix=".landmines-backup-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(old)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, previous)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    fd, temporary = tempfile.mkstemp(prefix=".landmines-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def record(args: argparse.Namespace) -> None:
    if not KEY_RE.fullmatch(args.error_key):
        raise ValueError("invalid error_key")
    path = cache_path(args.workspace)
    records = parse(path.read_text(encoding="utf-8")) if path.exists() else {}
    existing = records.get(args.error_key)
    if existing:
        existing["発生回数"] = str(int(existing["発生回数"]) + 1)
        existing["地雷"] = args.landmine
        if args.cause != "調査中":
            existing["原因"] = args.cause
        if args.correct_pattern != "調査中":
            existing["正解パターン"] = args.correct_pattern
        existing["対象"] = args.target
        existing["最終確認"] = args.confirmed_on
    else:
        records[args.error_key] = {
            "発生回数": "1",
            "地雷": args.landmine,
            "原因": args.cause,
            "正解パターン": args.correct_pattern,
            "対象": args.target,
            "最終確認": args.confirmed_on,
        }
    atomic_write(path, render(records))
    print(f"{args.error_key} count={records[args.error_key]['発生回数']}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="landmine-cache")
    parser.add_argument("--workspace", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("record")
    add.add_argument("--error-key", required=True)
    add.add_argument("--landmine", required=True)
    add.add_argument("--cause", default="調査中")
    add.add_argument("--correct-pattern", default="調査中")
    add.add_argument("--target", required=True)
    add.add_argument("--confirmed-on", default=date.today().isoformat())
    args = parser.parse_args()
    if args.command == "record":
        record(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
