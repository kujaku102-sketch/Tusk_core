from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


EXTENSION_RE = re.compile(r"^Tusk_[A-Za-z0-9._-]+$")
MIGRATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    "archive",
    "build",
    "dist",
    "node_modules",
    "tmp",
    "venv",
    "work",
}
EXCLUDED_FILES = {
    ".env",
    "credentials.json",
    "developer.key.json",
    "token.json",
    "EXTENSION-MANIFEST.json",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


class MigrationError(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Candidate:
    name: str
    source: Path
    files: tuple[Path, ...]
    excluded: tuple[str, ...]
    status: str


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_linklike(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(os.path, "isjunction", None)
    return bool(is_junction and is_junction(path))


def resolve_directory(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise MigrationError("TUSK_MIGRATION_INVALID_ROOT", f"{label}: {path}") from exc
    if not resolved.is_dir() or is_linklike(resolved):
        raise MigrationError("TUSK_MIGRATION_INVALID_ROOT", f"{label}: {resolved}")
    return resolved


def validate_roots(legacy_root: Path, workspace: Path) -> tuple[Path, Path]:
    legacy = resolve_directory(legacy_root, "legacy_root")
    current = resolve_directory(workspace, "workspace")
    if legacy == current:
        raise MigrationError("TUSK_MIGRATION_INVALID_ROOT", "legacy_root equals workspace")
    if not (current / "Tusk_core" / "AGENTS.md").is_file() or not (current / "extensions").is_dir():
        raise MigrationError("TUSK_MIGRATION_INVALID_ROOT", "workspace is not a Tusk workspace")
    return legacy, current


def should_exclude(relative: Path) -> bool:
    if any(part in EXCLUDED_DIRECTORIES for part in relative.parts[:-1]):
        return True
    name = relative.name
    return name in EXCLUDED_FILES or name.startswith(".env.") or relative.suffix.lower() in EXCLUDED_SUFFIXES


def collect_static_files(source: Path) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    files: list[Path] = []
    excluded: list[str] = []
    for root_text, directories, names in os.walk(source, topdown=True, followlinks=False):
        root = Path(root_text)
        kept_directories: list[str] = []
        for name in sorted(directories):
            child = root / name
            relative = child.relative_to(source)
            if name in EXCLUDED_DIRECTORIES or is_linklike(child):
                excluded.append(relative.as_posix() + "/")
            else:
                kept_directories.append(name)
        directories[:] = kept_directories
        for name in sorted(names):
            child = root / name
            relative = child.relative_to(source)
            if should_exclude(relative) or is_linklike(child):
                excluded.append(relative.as_posix())
                continue
            if child.is_file():
                files.append(relative)
    return tuple(sorted(files, key=lambda value: value.as_posix())), tuple(sorted(set(excluded)))


def discover_candidates(legacy_root: Path) -> tuple[Candidate, ...]:
    extension_root = legacy_root / "extensions"
    if not extension_root.is_dir() or is_linklike(extension_root):
        return ()
    candidates: list[Candidate] = []
    for source in sorted(extension_root.iterdir(), key=lambda value: value.name):
        if not source.is_dir() or is_linklike(source) or not EXTENSION_RE.fullmatch(source.name):
            continue
        files, excluded = collect_static_files(source)
        status = "ready" if Path("AGENTS.md") in files else "needs_review"
        candidates.append(Candidate(source.name, source, files, excluded, status))
    return tuple(candidates)


def select_candidates(candidates: tuple[Candidate, ...], selected: list[str] | None) -> tuple[Candidate, ...]:
    by_name = {candidate.name: candidate for candidate in candidates}
    names = selected or sorted(by_name)
    if len(names) != len(set(names)):
        raise MigrationError("TUSK_MIGRATION_INVALID_EXTENSION", "duplicate extension selection")
    missing = [name for name in names if name not in by_name]
    if missing or any(not EXTENSION_RE.fullmatch(name) for name in names):
        raise MigrationError("TUSK_MIGRATION_INVALID_EXTENSION", ",".join(missing or names))
    chosen = tuple(by_name[name] for name in names)
    blocked = [candidate.name for candidate in chosen if candidate.status != "ready"]
    if blocked:
        raise MigrationError("TUSK_MIGRATION_INVALID_EXTENSION", ",".join(blocked))
    return chosen


def run_count(legacy_root: Path) -> int:
    runs = legacy_root / "work" / "runs"
    if not runs.is_dir() or is_linklike(runs):
        return 0
    return sum(1 for child in runs.iterdir() if child.is_dir() and not is_linklike(child))


def candidate_record(candidate: Candidate) -> dict:
    return {
        "name": candidate.name,
        "source": str(candidate.source),
        "status": candidate.status,
        "file_count": len(candidate.files),
        "total_bytes": sum((candidate.source / relative).stat().st_size for relative in candidate.files),
        "excluded": list(candidate.excluded),
    }


def build_plan(legacy_root: Path, workspace: Path, selected: list[str] | None = None) -> dict:
    legacy, current = validate_roots(legacy_root, workspace)
    candidates = discover_candidates(legacy)
    chosen = select_candidates(candidates, selected)
    return {
        "schema_version": 1,
        "state": "ready",
        "legacy_root": str(legacy),
        "workspace": str(current),
        "selected_extensions": [candidate_record(candidate) for candidate in chosen],
        "all_candidates": [candidate_record(candidate) for candidate in candidates],
        "legacy_run_count": run_count(legacy),
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def generated_manifest(candidate: Candidate, destination: Path) -> dict:
    managed = [
        {"path": relative.as_posix(), "sha256": digest(destination / relative)}
        for relative in candidate.files
    ]
    return {
        "schema_version": 1,
        "root": candidate.name,
        "entry": "AGENTS.md",
        "algorithm": "sha256",
        "runtime_scope": {
            "workspace_required": True,
            "derived_from": [
                "activation",
                "current_task",
                "current_spec",
                "git_diff",
                "validated_context_cache",
            ],
            "owned_paths": [f"extensions/{candidate.name}"],
            "excluded_paths": [
                "Tusk_core",
                "Tusk_sharpener",
                "runtime_adapters",
                "work/migrations",
            ],
        },
        "managed_files": managed,
    }


def stage_candidate(candidate: Candidate, staged_root: Path) -> dict:
    destination = staged_root / candidate.name
    if destination.exists():
        raise MigrationError("TUSK_MIGRATION_DESTINATION_EXISTS", str(destination))
    staged_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{candidate.name}-", dir=staged_root))
    try:
        for relative in candidate.files:
            source = candidate.source / relative
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        write_json(temporary / "EXTENSION-MANIFEST.json", generated_manifest(candidate, temporary))
        os.replace(temporary, destination)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return {
        "name": candidate.name,
        "destination": str(destination),
        "file_count": len(candidate.files),
        "manifest": str(destination / "EXTENSION-MANIFEST.json"),
    }


def stage(
    legacy_root: Path,
    workspace: Path,
    migration_id: str,
    selected: list[str] | None,
    apply: bool,
) -> dict:
    if not apply:
        raise MigrationError("TUSK_MIGRATION_WRITE_REQUIRES_APPLY", "stage requires --apply")
    if not MIGRATION_ID_RE.fullmatch(migration_id):
        raise MigrationError("TUSK_MIGRATION_INVALID_ID", migration_id)
    plan = build_plan(legacy_root, workspace, selected)
    current = Path(plan["workspace"])
    migration_root = current / "work" / "migrations" / migration_id
    if migration_root.exists():
        raise MigrationError("TUSK_MIGRATION_DESTINATION_EXISTS", str(migration_root))
    staged_root = migration_root / "staged_extensions"
    chosen = select_candidates(discover_candidates(Path(plan["legacy_root"])), selected)
    staged = [stage_candidate(candidate, staged_root) for candidate in chosen]
    result = {
        **plan,
        "state": "staged",
        "migration_id": migration_id,
        "migration_root": str(migration_root),
        "staged_extensions": staged,
        "activation_changed": False,
        "legacy_changed": False,
    }
    write_json(migration_root / "migration-result.json", result)
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="tusk-workspace-migrator")
    value.add_argument("action", choices=("inspect", "stage"))
    value.add_argument("--legacy-root", type=Path, required=True)
    value.add_argument("--workspace", type=Path, required=True)
    value.add_argument("--extension", action="append")
    value.add_argument("--migration-id")
    value.add_argument("--apply", action="store_true")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.action == "inspect":
            result = build_plan(args.legacy_root, args.workspace, args.extension)
        else:
            result = stage(
                args.legacy_root,
                args.workspace,
                args.migration_id or "",
                args.extension,
                args.apply,
            )
    except MigrationError as exc:
        print(
            json.dumps(
                {"schema_version": 1, "state": "needs_review", "error_code": exc.code, "detail": exc.detail},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
