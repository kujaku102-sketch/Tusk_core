#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, os, re, shutil
from pathlib import Path

CORE = Path(__file__).resolve().parents[5]
SZ = Path(__file__).resolve().parents[3]
PRODUCER = {"producer": "WKZ"}
GLOBAL_CONFIG = SZ / "GLOBAL.json"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inside(child: Path, parent: Path) -> bool:
    child, parent = child.resolve(strict=False), parent.resolve(strict=False)
    return child != parent and parent in child.parents

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))

def redact(value: object) -> str:
    text = " ".join(str(value).replace("\x00", " ").split())
    return re.sub(r"(?i)\b(token|secret|password|authorization)=\S+", r"\1=<redacted>", text)[:240]

def inspect(args: argparse.Namespace) -> dict:
    workspace = Path(args.workspace).resolve(strict=False)
    project = Path(args.project).resolve(strict=False)
    pj = project / "PROJECT.json"; rd = project / "REQUIRED-DATA.json"
    global_cfg=load(GLOBAL_CONFIG); child_path=Path(args.child).resolve(strict=False); child=load(child_path)
    result = {"schema_version": 1, "program_id": "TUSK_SZ_BOOTSTRAP",
              "mode": "apply" if args.apply else "inspect", "producer": PRODUCER,
              "workspace": str(workspace), "project": str(project), "checks": {},
              "required_data": [], "authentication": {}, "ok": False, "status": "blocked"}
    result["checks"] = {"core": (CORE / "AGENTS.md").is_file(),
                        "tusk_sz": (SZ / "AGENTS.md").is_file(),
                        "project": pj.is_file(), "required_data_manifest": rd.is_file(),
                        "workspace": workspace.is_dir()}
    if not all(result["checks"].values()): return result
    config = load(pj); manifest = load(rd)
    registered={x.get("project_id"): (SZ/x.get("path","")).resolve(strict=False) for x in global_cfg.get("projects",[])}
    if config.get("project_id") != args.project_id or registered.get(args.project_id)!=pj.resolve(strict=False): return result
    index=load(project/"CHILDREN.json"); indexed={x.get("work_id"):(project/x.get("path","")).resolve(strict=False) for x in index.get("children",[])}
    if indexed.get(child.get("work_id"))!=child_path:return result
    if child.get("parent_project_id")!=args.project_id or child.get("producer")!="WKZ": return result
    result["authority"]={"work_id":child.get("work_id"),"state":child.get("state"),"resolved":True}
    for item in manifest.get("items", []):
        dest = workspace / item["destination"]
        state = {"id": item["id"], "destination": str(dest), "present": dest.is_file()}
        if dest.is_file():
            state["sha256"] = sha(dest)
            state["hash_matches"] = state["sha256"].lower() == item["sha256"].lower()
        result["required_data"].append(state)
    locator = Path(args.credential_locator).resolve(strict=False)
    result["authentication"] = {"provider": "google", "scope": "drive",
        "credential_locator": str(locator), "present": locator.is_file()}
    result["ok"] = all(x["present"] and x.get("hash_matches",False) for x in result["required_data"]) and locator.is_file()
    result["status"] = "ready" if result["ok"] else "needs_bootstrap"
    return result

def apply_missing(args: argparse.Namespace, result: dict) -> None:
    workspace = Path(args.workspace).resolve(strict=False)
    project = Path(args.project).resolve(strict=False)
    stage = Path(args.stage).resolve(strict=False) if args.stage else None
    if stage is None or not stage.is_dir(): raise SystemExit("F220: --apply requires existing --stage")
    if not result.get("authority",{}).get("resolved"): raise SystemExit("F224: inspect authority failed")
    manifest = load(project / "REQUIRED-DATA.json"); child=load(Path(args.child))
    if child.get("state")!="running": raise SystemExit("F224: child is not running")
    allowed=[(workspace/x).resolve(strict=False) for x in child.get("allowed_paths",[])]
    forbidden=[(workspace/x).resolve(strict=False) for x in child.get("forbidden_paths",[]) if not Path(x).is_absolute()]
    for item in manifest.get("items", []):
        dest = (workspace / item["destination"]).resolve(strict=False)
        if not any(dest==x or x in dest.parents for x in allowed): raise SystemExit("F224: destination not allowed by child")
        if any(dest==x or x in dest.parents for x in forbidden): raise SystemExit("F224: destination forbidden by child")
        if not inside(dest, workspace): raise SystemExit("F221: destination escapes workspace")
        if dest.exists(): continue
        source = (stage / item["stage_path"]).resolve(strict=False)
        if not inside(source, stage) or not source.is_file(): raise SystemExit("F222: staged source missing")
        if sha(source).lower() != item["sha256"].lower(): raise SystemExit("F223: staged source hash mismatch")
        dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, dest)
    result.update(inspect(args)); result["mode"] = "apply"

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--workspace",required=True); p.add_argument("--project",required=True)
    p.add_argument("--child",required=True)
    p.add_argument("--project-id",required=True); p.add_argument("--credential-locator",required=True)
    p.add_argument("--stage"); p.add_argument("--apply",action="store_true"); a=p.parse_args()
    r=inspect(a)
    if a.apply: apply_missing(a,r)
    print(json.dumps(r,ensure_ascii=False,indent=2)); return 0 if r["ok"] else 1
if __name__ == "__main__": raise SystemExit(main())
