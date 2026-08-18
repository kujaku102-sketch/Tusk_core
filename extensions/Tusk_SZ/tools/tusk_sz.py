#!/usr/bin/env python3
"""Tusk SZ: bounded product-specific renderer/UI/E2E orchestration."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Iterable


PROGRAM_ID = "TUSK_SZ"
COMPONENT = "tusk_sz"
EXTENSION_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = EXTENSION_ROOT.parents[1]
DEFAULT_EVIDENCE_ROOT = CORE_ROOT / "work" / "runs"
LAYER_STATES = {"passed", "failed", "blocked", "ready", "not_run", "not_applicable"}
SAFE_CARD_ID = re.compile(r"^[A-Z][A-Z0-9]{0,15}-[0-9]{1,6}$")


class TuskError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def clean_marker_value(value: object) -> str:
    return re.sub(r"\s+", "_", str(value).strip()) or "none"


def sanitize_probe_detail(value: object, limit: int = 240) -> str:
    text = " ".join(str(value).replace("\x00", " ").split())
    text = re.sub(r"(?i)\b(token|password|secret|authorization)=\S+", r"\1=<redacted>", text)
    return text[:limit] or "no_detail"


def marker(kind: str, *, code: str | None = None, run_id: str, step: str, **fields: object) -> dict[str, str]:
    data = {"kind": kind, "run_id": run_id, "component": COMPONENT, "step": step}
    if code:
        data["code"] = code
        data["program_id"] = PROGRAM_ID
    data.update({key: str(value) for key, value in fields.items()})
    ordered = []
    if code:
        ordered.extend((f"code={code}", f"program_id={PROGRAM_ID}"))
    ordered.extend((f"run_id={clean_marker_value(run_id)}", f"component={COMPONENT}", f"step={clean_marker_value(step)}"))
    ordered.extend(f"{key}={clean_marker_value(value)}" for key, value in fields.items())
    print(f"[{kind}] " + " ".join(ordered), flush=True)
    return data


def layer(status: str, detail: str, *, code: str | None = None,
          command: list[str] | None = None, evidence: Iterable[Path | str] = (),
          criteria: Iterable[str] = ()) -> dict[str, Any]:
    if status not in LAYER_STATES:
        raise ValueError(f"invalid layer status: {status}")
    return {
        "status": status,
        "code": code,
        "detail": detail,
        "command": command,
        "evidence": [str(item) for item in evidence],
        "criteria": list(criteria),
    }


def is_strictly_contained(child: Path, parent: Path) -> bool:
    child_resolved = child.resolve(strict=False)
    parent_resolved = parent.resolve(strict=False)
    return child_resolved != parent_resolved and parent_resolved in child_resolved.parents


def validate_evidence_path(evidence_dir: Path, evidence_root: Path) -> Path:
    resolved = evidence_dir.resolve(strict=False)
    if not is_strictly_contained(resolved, evidence_root):
        raise TuskError("F202", f"evidence directory escapes or equals root: {resolved}")
    return resolved


def resolve_runtime(explicit: str | None, env_name: str, names: Iterable[str],
                    fallbacks: Iterable[Path]) -> dict[str, Any]:
    candidates: list[tuple[str, str | Path]] = []
    if explicit:
        candidates.append(("argument", explicit))
    env_value = os.environ.get(env_name)
    if env_value:
        candidates.append((f"environment:{env_name}", env_value))
    for name in names:
        found = shutil.which(name)
        if found:
            candidates.append(("PATH", found))
    candidates.extend(("fallback", path) for path in fallbacks)
    seen: set[str] = set()
    for origin, candidate in candidates:
        raw = str(candidate)
        if raw in seen:
            continue
        seen.add(raw)
        found = shutil.which(raw) if not Path(raw).is_absolute() else raw
        if found and Path(found).is_file() and Path(found).stat().st_size > 0:
            return {"available": True, "path": str(Path(found).resolve()), "origin": origin}
    return {"available": False, "path": None, "origin": None}


def node_fallbacks() -> list[Path]:
    home = Path.home()
    return [
        home / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "nodejs/node.exe",
    ]


def powershell_fallbacks() -> list[Path]:
    system_root = Path(os.environ.get("SystemRoot", "C:/Windows"))
    return [
        system_root / "System32/WindowsPowerShell/v1.0/powershell.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "PowerShell/7/pwsh.exe",
    ]


def browser_fallbacks() -> list[Path]:
    program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    return [
        program_files_x86 / "Microsoft/Edge/Application/msedge.exe",
        program_files / "Microsoft/Edge/Application/msedge.exe",
        local / "Microsoft/Edge/Application/msedge.exe",
    ]


def python_fallbacks() -> list[Path]:
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    return [
        local / "Programs/Python/Python312/python.exe",
        local / "Programs/Python/Python311/python.exe",
    ]


def illustrator_fallbacks() -> list[Path]:
    roots = [
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Adobe",
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Adobe",
    ]
    found: list[Path] = []
    for root in roots:
        if root.is_dir():
            found.extend(sorted(root.glob("Adobe Illustrator */Support Files/Contents/Windows/Illustrator.exe"), reverse=True))
    return found


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def validate_result(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version", "program_id", "run_id", "profile", "mode", "workspace",
        "overall_status", "ok", "identity", "dependencies", "layers", "cleanup",
        "markers", "started_at", "finished_at",
    }
    errors.extend(f"missing:{key}" for key in sorted(required - payload.keys()))
    if payload.get("schema_version") != 1:
        errors.append("schema_version")
    if payload.get("program_id") != PROGRAM_ID:
        errors.append("program_id")
    if payload.get("profile") not in {"web", "illustrator"}:
        errors.append("profile")
    if payload.get("mode") not in {"inspect", "apply"}:
        errors.append("mode")
    layers = payload.get("layers")
    if not isinstance(layers, dict):
        errors.append("layers")
    else:
        for name in ("renderer", "ui", "e2e"):
            item = layers.get(name)
            if not isinstance(item, dict) or item.get("status") not in LAYER_STATES:
                errors.append(f"layers.{name}")
    cleanup = payload.get("cleanup")
    if not isinstance(cleanup, dict) or not all(key in cleanup for key in ("required", "attempted", "confirmed")):
        errors.append("cleanup")
    return errors


def run_command(command: list[str], cwd: Path, timeout: int, stdout_path: Path,
                stderr_path: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command, cwd=str(cwd), env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        return {"exit_code": completed.returncode, "timed_out": False,
                "duration_seconds": round(time.monotonic() - started, 3),
                "stdout": completed.stdout, "stderr": completed.stderr}
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        return {"exit_code": None, "timed_out": True,
                "duration_seconds": round(time.monotonic() - started, 3),
                "stdout": stdout, "stderr": stderr}


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def wait_for_http(url: str, process: subprocess.Popen[Any], timeout: int) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout
    last = "not attempted"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False, f"server exited with {process.returncode}"
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True, "HTTP 200"
                last = f"HTTP {response.status}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = str(exc)
        time.sleep(0.25)
    return False, last


def stop_spawned_process(process: subprocess.Popen[Any], timeout: int = 10) -> tuple[bool, str]:
    if process.poll() is not None:
        return True, f"already exited ({process.returncode})"
    if os.name == "nt":
        killer = subprocess.run(
            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, check=False, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, f"taskkill exit={killer.returncode}; process remained"
        return True, f"taskkill exit={killer.returncode}; process exit={process.returncode}"
    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, "process remained after kill"
    return True, f"process exit={process.returncode}"


def web_identity(workspace: Path) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    package_path = workspace / "package.json"
    package: dict[str, Any] = {}
    try:
        package = read_json(package_path)
    except (OSError, ValueError):
        pass
    scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
    checks["package_name_simple_zeke"] = package.get("name") == "simple-zeke"
    checks["build_script"] = isinstance(scripts, dict) and bool(scripts.get("build"))
    checks["smoke_script"] = isinstance(scripts, dict) and bool(scripts.get("smoke:ui"))
    for relative in ("AGENTS.md", "tools/serve.mjs", "scripts/smoke-ui.mjs"):
        checks[f"file:{relative}"] = (workspace / relative).is_file()
    vite = vite_entry(workspace)
    vite_api = vite_api_entry(workspace)
    checks["vite_entry"] = vite is not None
    checks["vite_api_entry"] = vite_api is not None
    return {"ok": all(checks.values()), "checks": checks, "package_name": package.get("name"),
            "vite_entry": str(vite) if vite else None,
            "vite_api_entry": str(vite_api) if vite_api else None}


def playwright_import(workspace: Path) -> dict[str, Any]:
    script = workspace / "scripts/smoke-ui.mjs"
    if not script.is_file():
        return {"available": False, "path": None, "origin": "workspace-script"}
    text = script.read_text(encoding="utf-8")
    match = re.search(r'from\s+["\'](file:///[^"\']*playwright/index\.mjs)["\']', text)
    if not match:
        return {"available": False, "path": None, "origin": "workspace-script"}
    path = Path(urllib.parse.unquote(urllib.parse.urlparse(match.group(1)).path.lstrip("/")))
    return {"available": path.is_file(), "path": str(path), "origin": "workspace-script"}


def vite_entry(workspace: Path) -> Path | None:
    """Resolve Vite without trusting a possibly stale pnpm junction."""
    direct = workspace / "node_modules/vite/bin/vite.js"
    if direct.is_file():
        return direct.resolve()
    candidates = sorted((workspace / "node_modules/.pnpm").glob("vite@*/node_modules/vite/bin/vite.js"))
    files = [candidate.resolve() for candidate in candidates if candidate.is_file()]
    return files[0] if len(files) == 1 else None


def vite_api_entry(workspace: Path) -> Path | None:
    direct = workspace / "node_modules/vite/dist/node/index.js"
    if direct.is_file():
        return direct.resolve()
    candidates = sorted((workspace / "node_modules/.pnpm").glob("vite@*/node_modules/vite/dist/node/index.js"))
    files = [candidate.resolve() for candidate in candidates if candidate.is_file()]
    return files[0] if len(files) == 1 else None


def probe_node_esm_import(node: str, module_path: str, workspace: Path, timeout: int) -> dict[str, Any]:
    """Actually import one ESM module without writing into the product workspace."""
    started = time.monotonic()
    script = 'import {pathToFileURL} from "node:url"; await import(pathToFileURL(process.argv[1]).href);'
    command = [node, "--input-type=module", "--eval", script, module_path]
    try:
        completed = subprocess.run(
            command, cwd=str(workspace), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        raw_detail = completed.stderr or completed.stdout or ("import_ok" if completed.returncode == 0 else "import_failed")
        return {
            "available": completed.returncode == 0,
            "probed": True,
            "path": str(Path(module_path).resolve(strict=False)),
            "exit_code": completed.returncode,
            "timed_out": False,
            "duration_seconds": round(time.monotonic() - started, 3),
            "detail": sanitize_probe_detail(raw_detail),
        }
    except subprocess.TimeoutExpired as exc:
        raw_detail = exc.stderr or exc.stdout or f"import_timeout_after_{timeout}s"
        if isinstance(raw_detail, bytes):
            raw_detail = raw_detail.decode("utf-8", "replace")
        return {
            "available": False,
            "probed": True,
            "path": str(Path(module_path).resolve(strict=False)),
            "exit_code": None,
            "timed_out": True,
            "duration_seconds": round(time.monotonic() - started, 3),
            "detail": sanitize_probe_detail(raw_detail),
        }
    except OSError as exc:
        return {
            "available": False,
            "probed": True,
            "path": str(Path(module_path).resolve(strict=False)),
            "exit_code": None,
            "timed_out": False,
            "duration_seconds": round(time.monotonic() - started, 3),
            "detail": sanitize_probe_detail(f"process_start_failed:{exc.__class__.__name__}"),
        }


def illustrator_identity(workspace: Path) -> dict[str, Any]:
    checks = {
        "pyproject": (workspace / "pyproject.toml").is_file(),
        "agents": (workspace / "AGENTS.md").is_file(),
        "orchestrator": (workspace / "tools/windows/render_card.ps1").is_file(),
        "render_jsx": (workspace / "illustrator/scripts/render_card.jsx").is_file(),
        "audit_jsx": (workspace / "illustrator/scripts/template_audit.jsx").is_file(),
        "python_package": (workspace / "src/siege_export").is_dir(),
    }
    return {"ok": all(checks.values()), "checks": checks}


def valid_card_id(value: str | None) -> bool:
    return isinstance(value, str) and SAFE_CARD_ID.fullmatch(value) is not None


def validate_png_output(workspace: Path, raw_path: object) -> tuple[Path | None, str]:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, "output_path_missing"
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    candidate = candidate.resolve(strict=False)
    output_root = (workspace / "build/output").resolve(strict=False)
    if not is_strictly_contained(candidate, output_root):
        return None, "output_path_outside_workspace_build_output"
    if candidate.suffix.lower() != ".png":
        return None, "output_suffix_not_png"
    if not candidate.is_file() or candidate.stat().st_size <= 8:
        return None, "output_png_missing_or_empty"
    with candidate.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            return None, "output_png_signature_invalid"
    return candidate, "valid_png"


def base_result(args: argparse.Namespace, workspace: Path, evidence_dir: Path | None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "program_id": PROGRAM_ID,
        "run_id": args.run_id,
        "profile": args.profile,
        "mode": "apply" if args.apply else "inspect",
        "workspace": str(workspace),
        "evidence_dir": str(evidence_dir) if evidence_dir else None,
        "overall_status": "blocked",
        "ok": False,
        "identity": {},
        "dependencies": {},
        "layers": {
            "renderer": layer("not_run", "not evaluated"),
            "ui": layer("not_run", "not evaluated"),
            "e2e": layer("not_run", "not evaluated"),
        },
        "cleanup": {"required": False, "attempted": False, "confirmed": True, "detail": "no child process"},
        "markers": [],
        "started_at": utc_now(),
        "finished_at": "",
    }


def add_marker(result: dict[str, Any], kind: str, step: str, code: str | None = None, **fields: object) -> None:
    result["markers"].append(marker(kind, code=code, run_id=result["run_id"], step=step, **fields))


def block_all(result: dict[str, Any], code: str, detail: str, *, ui_not_applicable: bool = False) -> None:
    result["layers"]["renderer"] = layer("blocked", detail, code=code)
    result["layers"]["ui"] = layer("not_applicable" if ui_not_applicable else "blocked", detail, code=None if ui_not_applicable else code)
    result["layers"]["e2e"] = layer("blocked", detail, code=code)
    result["overall_status"] = "blocked"
    result["ok"] = False
    add_marker(result, "TUSK_FORCE_STOP", "preflight", code=code, reason=detail)


def inspect_web(args: argparse.Namespace, workspace: Path, evidence_dir: Path | None) -> dict[str, Any]:
    result = base_result(args, workspace, evidence_dir)
    identity = web_identity(workspace)
    result["identity"] = identity
    if not identity["ok"]:
        block_all(result, "F200", "web_workspace_identity_invalid")
        return result
    node = resolve_runtime(args.node, "TUSK_SZ_NODE", ("node", "node.exe"), node_fallbacks())
    browser = resolve_runtime(args.browser, "TUSK_SZ_BROWSER", ("msedge", "msedge.exe"), browser_fallbacks())
    playwright_location = playwright_import(workspace)
    result["dependencies"] = {"node": node, "browser": browser, "playwright": playwright_location}
    if not node["available"]:
        block_all(result, "F201", "node_runtime_missing")
        return result
    vite_probe = probe_node_esm_import(node["path"], identity["vite_api_entry"], workspace, args.probe_timeout)
    vite_probe["origin"] = "workspace-vite-api"
    result["dependencies"]["vite"] = vite_probe
    if not vite_probe["available"]:
        block_all(result, "F201", "vite_module_import_failed")
        return result
    result["layers"]["renderer"] = layer("ready", "Vite build prerequisites satisfied")
    if playwright_location["available"]:
        playwright_probe = probe_node_esm_import(
            node["path"], playwright_location["path"], workspace, args.probe_timeout)
        playwright_probe["origin"] = playwright_location["origin"]
    else:
        playwright_probe = {
            "available": False, "probed": False, "path": playwright_location.get("path"),
            "origin": playwright_location.get("origin"), "exit_code": None,
            "timed_out": False, "duration_seconds": 0.0, "detail": "module_path_missing",
        }
    result["dependencies"]["playwright"] = playwright_probe
    browser_ready = browser["available"] and playwright_probe["available"]
    result["layers"]["ui"] = layer("ready" if browser_ready else "blocked",
        "browser scenario prerequisites satisfied" if browser_ready else "browser_or_playwright_import_failed",
        code=None if browser_ready else "F201")
    result["layers"]["e2e"] = layer("ready" if browser_ready else "blocked",
        "interactive scenario prerequisites satisfied" if browser_ready else "browser_or_playwright_import_failed",
        code=None if browser_ready else "F201")
    if not browser_ready:
        result["overall_status"] = "blocked"
        add_marker(result, "TUSK_FORCE_STOP", "preflight", code="F201", reason="browser_or_playwright_import_failed")
    else:
        result["overall_status"] = "ready"
        result["ok"] = True
        add_marker(result, "TUSK_PROGRESS", "inspect_complete", current=1, total=1)
    return result


def apply_web(args: argparse.Namespace, workspace: Path, evidence_dir: Path) -> dict[str, Any]:
    result = inspect_web(args, workspace, evidence_dir)
    result["mode"] = "apply"
    if result["overall_status"] != "ready":
        return result
    evidence_dir.mkdir(parents=True, exist_ok=True)
    node = result["dependencies"]["node"]["path"]
    build_command = [node, result["identity"]["vite_entry"], "build"]
    add_marker(result, "TUSK_PROGRESS", "renderer_build", current=1, total=3)
    build_out, build_err = evidence_dir / "renderer.stdout.log", evidence_dir / "renderer.stderr.log"
    build = run_command(build_command, workspace, args.build_timeout, build_out, build_err)
    result["renderer_process"] = {key: value for key, value in build.items() if key not in {"stdout", "stderr"}}
    if build["timed_out"]:
        result["layers"]["renderer"] = layer("failed", "Vite build timed out", code="F203", command=build_command, evidence=(build_out, build_err))
        result["layers"]["ui"] = layer("blocked", "renderer did not complete", code="F203")
        result["layers"]["e2e"] = layer("blocked", "renderer did not complete", code="F203")
        result["overall_status"] = "failed"
        result["ok"] = False
        add_marker(result, "TUSK_FORCE_STOP", "renderer_build", code="F203", reason="build_timeout")
        return result
    if build["exit_code"] != 0 or not (workspace / "dist/index.html").is_file():
        result["layers"]["renderer"] = layer("failed", "Vite build failed or dist/index.html is absent", code="F206", command=build_command, evidence=(build_out, build_err))
        result["layers"]["ui"] = layer("blocked", "renderer failed", code="F206")
        result["layers"]["e2e"] = layer("blocked", "renderer failed", code="F206")
        result["overall_status"] = "failed"
        result["ok"] = False
        add_marker(result, "TUSK_FORCE_STOP", "renderer_build", code="F206", reason="build_contract_failed")
        return result
    result["layers"]["renderer"] = layer("passed", "Vite build passed and dist/index.html exists", command=build_command, evidence=(build_out, build_err, workspace / "dist/index.html"), criteria=("exit_code=0", "dist/index.html exists"))

    browser_ready = result["dependencies"]["browser"]["available"] and result["dependencies"]["playwright"]["available"]
    if not browser_ready:
        result["layers"]["ui"] = layer("blocked", "browser_or_playwright_missing", code="F201")
        result["layers"]["e2e"] = layer("blocked", "browser_or_playwright_missing", code="F201")
        result["overall_status"] = "blocked"
        result["ok"] = False
        add_marker(result, "TUSK_FORCE_STOP", "browser_preflight", code="F201", reason="browser_or_playwright_missing")
        return result
    if not port_is_free(args.port):
        result["layers"]["ui"] = layer("blocked", f"port {args.port} is already occupied", code="F205")
        result["layers"]["e2e"] = layer("blocked", "dedicated server could not start", code="F205")
        result["overall_status"] = "blocked"
        result["ok"] = False
        add_marker(result, "TUSK_FORCE_STOP", "server_start", code="F205", reason="port_occupied")
        return result

    server_command = [node, str(workspace / "tools/serve.mjs")]
    server_out_path, server_err_path = evidence_dir / "server.stdout.log", evidence_dir / "server.stderr.log"
    server_out = server_out_path.open("w", encoding="utf-8", newline="\n")
    server_err = server_err_path.open("w", encoding="utf-8", newline="\n")
    server: subprocess.Popen[Any] | None = None
    result["cleanup"] = {"required": True, "attempted": False, "confirmed": False, "detail": "server not started"}
    try:
        env = os.environ.copy()
        env["PORT"] = str(args.port)
        env["OPEN_BROWSER"] = "0"
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        server = subprocess.Popen(server_command, cwd=str(workspace), env=env, stdout=server_out, stderr=server_err,
                                  text=True, creationflags=flags, start_new_session=os.name != "nt")
        result["server"] = {"pid": server.pid, "command": server_command, "url": f"http://127.0.0.1:{args.port}/"}
        add_marker(result, "TUSK_PROGRESS", "server_ready", current=2, total=3)
        ready, readiness_detail = wait_for_http(result["server"]["url"], server, args.server_timeout)
        result["server"]["readiness"] = readiness_detail
        if not ready:
            code = "F203" if server.poll() is None else "F205"
            result["layers"]["ui"] = layer("failed", f"server readiness failed: {readiness_detail}", code=code, command=server_command, evidence=(server_out_path, server_err_path))
            result["layers"]["e2e"] = layer("blocked", "server not ready", code=code)
            result["overall_status"] = "failed"
            result["ok"] = False
            add_marker(result, "TUSK_FORCE_STOP", "server_ready", code=code, reason="server_not_ready")
            return result

        scenario_command = [node, str(workspace / "scripts/smoke-ui.mjs"), result["server"]["url"]]
        scenario_out, scenario_err = evidence_dir / "browser.stdout.log", evidence_dir / "browser.stderr.log"
        add_marker(result, "TUSK_PROGRESS", "browser_scenario", current=3, total=3)
        scenario = run_command(scenario_command, workspace, args.scenario_timeout, scenario_out, scenario_err)
        result["browser_process"] = {key: value for key, value in scenario.items() if key not in {"stdout", "stderr"}}
        if scenario["timed_out"]:
            result["layers"]["ui"] = layer("failed", "browser scenario timed out", code="F203", command=scenario_command, evidence=(scenario_out, scenario_err))
            result["layers"]["e2e"] = layer("failed", "interactive scenario timed out", code="F203", command=scenario_command, evidence=(scenario_out, scenario_err))
            result["overall_status"] = "failed"
            result["ok"] = False
            add_marker(result, "TUSK_FORCE_STOP", "browser_scenario", code="F203", reason="scenario_timeout")
            return result
        parsed: dict[str, Any] | None = None
        for line_text in reversed(scenario["stdout"].splitlines()):
            try:
                candidate = json.loads(line_text)
                if isinstance(candidate, dict):
                    parsed = candidate
                    break
            except json.JSONDecodeError:
                continue
        if scenario["exit_code"] != 0:
            result["layers"]["ui"] = layer("failed", "real browser assertions failed", code="F207", command=scenario_command, evidence=(scenario_out, scenario_err))
            result["layers"]["e2e"] = layer("failed", "interactive browser scenario failed", code="F208", command=scenario_command, evidence=(scenario_out, scenario_err))
            result["overall_status"] = "failed"
            result["ok"] = False
            add_marker(result, "TUSK_FORCE_STOP", "browser_scenario", code="F208", reason="scenario_exit_nonzero")
            return result
        expected_tabs = ["チュートリアル", "AI対戦", "サンドボックス"]
        screenshot = workspace / "artifacts/vengeance-tutorial-smoke.png"
        ui_ok = (parsed is not None and parsed.get("ok") is True and parsed.get("tabs") == expected_tabs
                 and screenshot.is_file() and screenshot.stat().st_size > 0)
        e2e_ok = parsed is not None and parsed.get("flow") == "install-layered-relog-effect-activation" and parsed.get("aiDeckSelection") == "neutron-vs-vengeance"
        if not ui_ok or not e2e_ok:
            code = "F209"
            result["layers"]["ui"] = layer("failed", "browser output lacks required UI contract", code=code, command=scenario_command, evidence=(scenario_out, scenario_err))
            result["layers"]["e2e"] = layer("failed", "browser output lacks required E2E contract", code=code, command=scenario_command, evidence=(scenario_out, scenario_err))
            result["overall_status"] = "failed"
            result["ok"] = False
            add_marker(result, "TUSK_FORCE_STOP", "browser_result", code=code, reason="browser_result_invalid")
            return result
        result["layers"]["ui"] = layer("passed", "live browser tab and tutorial UI assertions passed", command=scenario_command,
            evidence=(scenario_out, scenario_err, screenshot), criteria=("three expected tabs", "tutorial UI assertions", "browser exit_code=0", "screenshot size > 0"))
        result["layers"]["e2e"] = layer("passed", "existing interactive install/layered/relog/effect/deck scenario passed", command=scenario_command,
            evidence=(scenario_out, scenario_err, screenshot), criteria=("flow=install-layered-relog-effect-activation", "deck selection persisted"))
        result["overall_status"] = "passed"
        result["ok"] = True
        return result
    except OSError as exc:
        result["layers"]["ui"] = layer("failed", f"server process start failed: {exc}", code="F205", command=server_command, evidence=(server_out_path, server_err_path))
        result["layers"]["e2e"] = layer("blocked", "server process did not start", code="F205")
        result["overall_status"] = "failed"
        result["ok"] = False
        add_marker(result, "TUSK_FORCE_STOP", "server_start", code="F205", reason="process_start_failed")
        return result
    finally:
        server_out.close()
        server_err.close()
        if server is not None:
            result["cleanup"]["attempted"] = True
            confirmed, detail = stop_spawned_process(server)
            result["cleanup"]["confirmed"] = confirmed
            result["cleanup"]["detail"] = detail
            if not confirmed:
                result["overall_status"] = "failed"
                result["ok"] = False
                if result["layers"]["e2e"]["status"] == "passed":
                    result["layers"]["e2e"] = layer("failed", "server cleanup could not be confirmed", code="F210", evidence=(server_out_path, server_err_path))
                add_marker(result, "TUSK_FORCE_STOP", "cleanup", code="F210", reason="server_cleanup_unconfirmed")


def inspect_illustrator(args: argparse.Namespace, workspace: Path, evidence_dir: Path | None) -> dict[str, Any]:
    result = base_result(args, workspace, evidence_dir)
    identity = illustrator_identity(workspace)
    result["identity"] = identity
    result["layers"]["ui"] = layer("not_applicable", "Illustrator profile has no separate UI contract")
    if not identity["ok"]:
        block_all(result, "F200", "illustrator_workspace_identity_invalid", ui_not_applicable=True)
        return result
    powershell = resolve_runtime(args.powershell, "TUSK_SZ_POWERSHELL", ("powershell", "powershell.exe", "pwsh", "pwsh.exe"), powershell_fallbacks())
    python = resolve_runtime(args.python, "TUSK_SZ_PYTHON", ("python", "python.exe", "py"), python_fallbacks())
    illustrator = resolve_runtime(args.illustrator, "TUSK_SZ_ILLUSTRATOR", ("Illustrator", "Illustrator.exe"), illustrator_fallbacks())
    template = workspace / "illustrator/templates/card_v1.ai"
    result["dependencies"] = {
        "powershell": powershell,
        "python": python,
        "illustrator": illustrator,
        "template": {"available": template.is_file(), "path": str(template), "origin": "workspace"},
    }
    if not template.is_file():
        block_all(result, "F204", "illustrator_template_card_v1_ai_missing", ui_not_applicable=True)
        return result
    missing = [name for name in ("powershell", "python", "illustrator") if not result["dependencies"][name]["available"]]
    if missing:
        block_all(result, "F201", "missing_dependencies:" + ",".join(missing), ui_not_applicable=True)
        return result
    result["layers"]["renderer"] = layer("ready", "Illustrator renderer prerequisites satisfied")
    result["layers"]["e2e"] = layer("ready", "complete C-03 orchestrator prerequisites satisfied")
    result["overall_status"] = "ready"
    result["ok"] = True
    add_marker(result, "TUSK_PROGRESS", "inspect_complete", current=1, total=1)
    return result


def apply_illustrator(args: argparse.Namespace, workspace: Path, evidence_dir: Path) -> dict[str, Any]:
    result = inspect_illustrator(args, workspace, evidence_dir)
    result["mode"] = "apply"
    if result["overall_status"] != "ready":
        return result
    if not valid_card_id(args.card_id):
        block_all(result, "F200", "card_id_missing_or_unsafe", ui_not_applicable=True)
        return result
    evidence_dir.mkdir(parents=True, exist_ok=True)
    command = [
        result["dependencies"]["powershell"]["path"], "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(workspace / "tools/windows/render_card.ps1"), "-CardId", args.card_id,
    ]
    if args.allow_cache:
        command.append("-AllowCache")
    if args.audit_only:
        command.append("-AuditOnly")
    if args.force:
        command.append("-Force")
    stdout_path, stderr_path = evidence_dir / "illustrator.stdout.log", evidence_dir / "illustrator.stderr.log"
    add_marker(result, "TUSK_PROGRESS", "illustrator_renderer", current=1, total=1)
    run = run_command(command, workspace, args.renderer_timeout, stdout_path, stderr_path)
    result["renderer_process"] = {key: value for key, value in run.items() if key not in {"stdout", "stderr"}}
    product_result_path = workspace / f"build/logs/render-{args.card_id}.json"
    evidence = [stdout_path, stderr_path]
    if product_result_path.is_file():
        evidence.append(product_result_path)
    if run["timed_out"]:
        result["layers"]["renderer"] = layer("failed", "Illustrator orchestration timed out", code="F203", command=command, evidence=evidence)
        result["layers"]["e2e"] = layer("failed", "complete render chain timed out", code="F203", command=command, evidence=evidence)
        result["overall_status"] = "failed"
        result["ok"] = False
        add_marker(result, "TUSK_FORCE_STOP", "illustrator_renderer", code="F203", reason="renderer_timeout")
        return result
    product_result: dict[str, Any] | None = None
    if product_result_path.is_file():
        try:
            candidate = read_json(product_result_path)
            if isinstance(candidate, dict):
                product_result = candidate
        except (OSError, ValueError):
            pass
    if run["exit_code"] != 0:
        product_status = product_result.get("status") if product_result else "missing_result"
        result["layers"]["renderer"] = layer("failed", f"product renderer failed: {product_status}", code="F206", command=command, evidence=evidence)
        result["layers"]["e2e"] = layer("failed", "complete Illustrator chain failed", code="F208", command=command, evidence=evidence)
        result["overall_status"] = "failed"
        result["ok"] = False
        add_marker(result, "TUSK_FORCE_STOP", "illustrator_renderer", code="F206", reason=product_status)
        return result
    if not product_result or product_result.get("ok") is not True:
        result["layers"]["renderer"] = layer("failed", "product result JSON is missing or invalid", code="F209", command=command, evidence=evidence)
        result["layers"]["e2e"] = layer("failed", "no valid complete-chain result", code="F209", command=command, evidence=evidence)
        result["overall_status"] = "failed"
        result["ok"] = False
        add_marker(result, "TUSK_FORCE_STOP", "illustrator_result", code="F209", reason="product_result_invalid")
        return result
    if args.audit_only:
        result["layers"]["renderer"] = layer("passed", "Illustrator template audit returned a valid success result", command=command, evidence=evidence, criteria=("exit_code=0", "product result ok=true"))
        result["layers"]["e2e"] = layer("not_run", "audit-only mode does not prove PNG E2E", code=None, evidence=evidence)
        result["overall_status"] = "passed"
        result["ok"] = True
        add_marker(result, "TUSK_MINOR_ISSUE", "layer_boundary", code="M202", target="e2e", detail="audit_only")
        return result
    output, output_detail = validate_png_output(workspace, product_result.get("output_path"))
    if output is None:
        result["layers"]["renderer"] = layer("failed", f"PNG artifact contract failed: {output_detail}", code="F206", command=command, evidence=evidence)
        result["layers"]["e2e"] = layer("failed", f"PNG artifact contract failed: {output_detail}", code="F208", command=command, evidence=evidence)
        result["overall_status"] = "failed"
        result["ok"] = False
        add_marker(result, "TUSK_FORCE_STOP", "illustrator_artifact", code="F206", reason=output_detail)
        return result
    evidence.append(output)
    result["layers"]["renderer"] = layer("passed", "Illustrator product result and PNG artifact passed", command=command, evidence=evidence, criteria=("exit_code=0", "product result ok=true", "PNG size > 0"))
    result["layers"]["e2e"] = layer("passed", "complete orchestrator-to-PNG chain passed", command=command, evidence=evidence, criteria=("product result contract", "non-empty PNG"))
    result["overall_status"] = "passed"
    result["ok"] = True
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("web", "illustrator"), required=True)
    parser.add_argument("--workspace", required=True, help="explicit external product workspace")
    parser.add_argument("--evidence-dir")
    parser.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    parser.add_argument("--run-id", default=f"SZ-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--node")
    parser.add_argument("--browser")
    parser.add_argument("--powershell")
    parser.add_argument("--python")
    parser.add_argument("--illustrator")
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--build-timeout", type=int, default=180)
    parser.add_argument("--probe-timeout", type=int, default=10)
    parser.add_argument("--server-timeout", type=int, default=30)
    parser.add_argument("--scenario-timeout", type=int, default=180)
    parser.add_argument("--renderer-timeout", type=int, default=300)
    parser.add_argument("--card-id")
    parser.add_argument("--allow-cache", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser


def execute(args: argparse.Namespace) -> tuple[dict[str, Any], Path | None]:
    workspace = Path(args.workspace).resolve(strict=False)
    evidence_dir: Path | None = None
    if args.evidence_dir:
        evidence_dir = validate_evidence_path(Path(args.evidence_dir), Path(args.evidence_root))
    if args.apply and evidence_dir is None:
        raise TuskError("F202", "--apply requires --evidence-dir")
    if args.profile == "web":
        result = apply_web(args, workspace, evidence_dir) if args.apply else inspect_web(args, workspace, evidence_dir)
    else:
        result = apply_illustrator(args, workspace, evidence_dir) if args.apply else inspect_illustrator(args, workspace, evidence_dir)
    result["finished_at"] = utc_now()
    errors = validate_result(result)
    if errors:
        raise TuskError("F209", "Tusk SZ result validation failed: " + ",".join(errors))
    result_path = evidence_dir / "tusk-sz-result.json" if evidence_dir else None
    if result_path:
        atomic_write_json(result_path, result)
    return result, result_path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if min(args.probe_timeout, args.build_timeout, args.server_timeout, args.scenario_timeout, args.renderer_timeout) < 1:
        parser.error("timeouts must be positive")
    if not (1 <= args.port <= 65535):
        parser.error("port must be 1..65535")
    try:
        result, result_path = execute(args)
    except TuskError as exc:
        marker("TUSK_FORCE_STOP", code=exc.code, run_id=args.run_id, step="cli", reason=str(exc))
        print(json.dumps({"schema_version": 1, "program_id": PROGRAM_ID, "run_id": args.run_id,
                          "profile": args.profile, "mode": "apply" if args.apply else "inspect",
                          "overall_status": "blocked", "ok": False, "code": exc.code,
                          "error": str(exc)}, ensure_ascii=False), flush=True)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if result_path:
        print(f"result_path={result_path}", flush=True)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
