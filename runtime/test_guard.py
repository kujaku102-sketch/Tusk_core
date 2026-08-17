from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    from .process_control import run as run_process
except ImportError:
    from process_control import run as run_process


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def event(kind: str, code: str | None, message: str) -> dict:
    return {"event": kind, "code": code, "message": message, "timestamp_utc": now()}


def tail(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value[-2000:]


def run_guard(command: list[str], timeout: int) -> dict:
    started = event("PROGRESS", None, "test started")
    try:
        completed = run_process(command, timeout)
    except subprocess.TimeoutExpired as exc:
        return {"status": "failed", "events": [started, event("FAIL", "F004", f"timeout after {timeout}s")], "stdout_tail": tail(exc.stdout), "stderr_tail": tail(exc.stderr)}
    if completed.returncode != 0:
        return {"status": "failed", "events": [started, event("FAIL", "F004", f"exit {completed.returncode}")], "returncode": completed.returncode, "stdout_tail": tail(completed.stdout), "stderr_tail": tail(completed.stderr)}
    return {"status": "success", "events": [started, event("DONE", None, "test passed")], "returncode": 0, "stdout_tail": tail(completed.stdout), "stderr_tail": tail(completed.stderr)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-json", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        command = json.loads(args.command_json)
        if not isinstance(command, list) or not command or not all(isinstance(value, str) and value for value in command):
            raise ValueError("command must be a JSON string array")
        report = run_guard(command, args.timeout)
    except (json.JSONDecodeError, ValueError) as exc:
        report = {"status": "failed", "events": [event("FAIL", "F002", str(exc))]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "success" else 4


if __name__ == "__main__":
    raise SystemExit(main())
