from __future__ import annotations

import argparse
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    from .process_control import run as run_process
except ImportError:
    from process_control import run as run_process

REQUIRED_RESULT_KEYS = {"schema_version", "slice_id", "status", "changed_files", "tests", "summary", "issues"}


def command_template(explicit: str | None) -> list[str]:
    raw = explicit or os.environ.get("TUSK_FLASH_AGENT_COMMAND", "")
    if raw:
        value = json.loads(raw)
    else:
        config = json.loads((Path(__file__).with_name("antigravity.json")).read_text(encoding="utf-8"))
        value = config.get("default_command")
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError("agent command must be a JSON string array")
    joined = "\n".join(value)
    if "{slice}" not in joined or "{result}" not in joined:
        raise ValueError("agent command requires {slice} and {result}")
    return value


def validate_plan(plan: dict) -> None:
    if set(plan) != {"schema_version", "route", "reason", "slices"} or plan["schema_version"] != 1:
        raise ValueError("invalid plan grammar")
    if plan["route"] not in {"DIRECT", "SPLIT", "STOP"}:
        raise ValueError("invalid route")
    if len(plan["slices"]) > 3:
        raise ValueError("maximum 3 slices")
    owners: dict[str, str] = {}
    for item in plan["slices"]:
        for path in item.get("writable_paths", []):
            if path in owners:
                raise ValueError(f"F003 overlapping write scope: {path}")
            owners[path] = item["slice_id"]


def validate_result(result: dict, task: dict) -> None:
    if set(result) != REQUIRED_RESULT_KEYS or result.get("schema_version") != 1:
        raise ValueError("F002 invalid result grammar")
    if result.get("slice_id") != task["slice_id"] or result.get("status") not in {"success", "failed", "needs_review"}:
        raise ValueError("F002 invalid result identity or status")
    if not isinstance(result.get("changed_files"), list) or not isinstance(result.get("tests"), list) or not isinstance(result.get("issues"), list):
        raise ValueError("F002 invalid result collections")
    allowed = set(task["writable_paths"])
    if any(path not in allowed for path in result["changed_files"]):
        raise ValueError("F002 result reports an out-of-scope change")


def run_slice(task: dict, template: list[str], task_dir: Path, result_dir: Path, timeout: int, workspace: Path | None = None) -> dict:
    task_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    task_path = task_dir / f'{task["slice_id"]}.json'
    result_path = result_dir / f'{task["slice_id"]}.json'
    result_path.unlink(missing_ok=True)
    task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    command = [token.replace("{slice}", str(task_path)).replace("{result}", str(result_path)) for token in template]
    try:
        completed = run_process(command, timeout, cwd=workspace)
    except subprocess.TimeoutExpired as exc:
        return {"slice_id": task["slice_id"], "status": "failed", "code": "F004", "error": f"timeout after {timeout}s", "stderr_tail": str(exc.stderr or "")[-2000:]}
    if completed.returncode != 0:
        return {"slice_id": task["slice_id"], "status": "failed", "code": "F001", "returncode": completed.returncode, "stderr_tail": completed.stderr[-2000:]}
    if not result_path.is_file():
        try:
            payload = json.loads(completed.stdout)
            if isinstance(payload, dict) and isinstance(payload.get("structured_output"), dict):
                payload = payload["structured_output"]
            result_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except (json.JSONDecodeError, OSError, TypeError):
            return {"slice_id": task["slice_id"], "status": "failed", "code": "F002", "error": "result missing", "stdout_tail": completed.stdout[-2000:], "stderr_tail": completed.stderr[-2000:]}
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
        validate_result(result, task)
        return result
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {"slice_id": task["slice_id"], "status": "failed", "code": "F002", "error": str(exc)}


def run_plan(plan: dict, template: list[str], task_dir: Path, result_dir: Path, timeout: int, workspace: Path | None = None) -> dict:
    validate_plan(plan)
    if plan["route"] == "STOP":
        return {"status": "needs_review", "code": "F005", "results": []}
    task_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(3, max(1, len(plan["slices"])))) as pool:
        futures = [pool.submit(run_slice, task, template, task_dir, result_dir, timeout, workspace) for task in plan["slices"]]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["slice_id"])
    success = all(item.get("status") == "success" for item in results)
    return {"status": "success" if success else "failed", "code": None if success else "F001", "results": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--command-json")
    run.add_argument("--task-dir", type=Path, default=Path("work/tasks/slices"))
    run.add_argument("--result-dir", type=Path, default=Path("work/results"))
    run.add_argument("--timeout", type=int, default=900)
    run.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        report = run_plan(plan, command_template(args.command_json), args.task_dir, args.result_dir, args.timeout, args.workspace.resolve())
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        report = {"status": "needs_review", "code": "F002", "error": str(exc), "results": []}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "success" else 4


if __name__ == "__main__":
    raise SystemExit(main())
