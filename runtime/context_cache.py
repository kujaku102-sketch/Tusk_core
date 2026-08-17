from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXCLUDED_DIRS = {".git", ".idea", ".vscode", "__pycache__", ".pytest_cache", "archive", "tmp", "work"}
IMPORTANT_NAMES = {"AGENTS.md", "README.md", "LICENSE", "NOTICE", "pyproject.toml", "requirements.txt", "package.json", "Cargo.toml", "go.mod"}
PROTECTED_NAMES = {"LICENSE", "NOTICE", ".env", "credentials.json", "secrets.json"}


def relative_files(root: Path) -> list[str]:
    found: list[str] = []
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name not in EXCLUDED_DIRS and not (Path(current) / name).is_symlink())
        base = Path(current)
        for name in sorted(files):
            path = base / name
            if path.is_symlink():
                continue
            found.append(path.relative_to(root).as_posix())
    return found


def git_head(root: Path) -> str | None:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else None


def python_imports(root: Path, rel: str) -> list[str]:
    try:
        tree = ast.parse((root / rel).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError):
        return []
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return sorted(names)


def build_cache(root: Path) -> dict:
    root = root.resolve()
    files = relative_files(root)
    python_files = [value for value in files if value.endswith(".py")]
    important = [value for value in files if Path(value).name in IMPORTANT_NAMES or value.startswith("policy/")]
    entry_points: list[str] = []
    for value in python_files:
        try:
            if "if __name__" in (root / value).read_text(encoding="utf-8"):
                entry_points.append(value)
        except (OSError, UnicodeError):
            pass
    test_files = [value for value in python_files if Path(value).name.startswith("test_")]
    test_commands = [f'python -m unittest "{value}"' for value in test_files]
    protected = [value for value in files if Path(value).name in PROTECTED_NAMES or value.startswith(".github/")]
    recent_failures: list[str] = []
    log_root = root / "work" / "logs"
    if log_root.is_dir():
        for log in sorted(log_root.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]:
            try:
                recent_failures.extend(line.strip()[:500] for line in log.read_text(encoding="utf-8", errors="replace").splitlines() if "FAIL" in line.upper())
            except OSError:
                pass
    return {
        "schema_version": 1,
        "project_id": root.name,
        "root": str(root),
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "git_head": git_head(root),
        "important_files": sorted(set(important)),
        "entry_points": sorted(set(entry_points)),
        "test_commands": sorted(set(test_commands)),
        "dependency_edges": [{"source": value, "imports": python_imports(root, value)} for value in python_files],
        "protected_paths": sorted(set(protected)),
        "recent_failures": recent_failures[-10:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_cache(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "files": len(relative_files(args.root.resolve())), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
