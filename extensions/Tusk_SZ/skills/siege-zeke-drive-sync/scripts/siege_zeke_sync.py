#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path

ROOT_ID="1yLQKxHxHjktl7frBAVZ-Vh7Sjm18G-T3"
CORE=Path(__file__).resolve().parents[5]
SZ=CORE/"extensions/Tusk_SZ"
GLOBAL_CONFIG=SZ/"GLOBAL.json"
def digest(path: Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def contained(child:Path,parent:Path)->bool:
    child,parent=child.resolve(strict=False),parent.resolve(strict=False)
    return child!=parent and parent in child.parents
def decision(local:str,remote:str,baseline:str)->str:
    lc,rc=local!=baseline,remote!=baseline
    if lc and rc and local!=remote:return "SYNC-409"
    if lc:return "push"
    if rc:return "pull"
    return "equal" if local==remote else "SYNC-409"
def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("operation",choices=("inventory","compare","apply-local"))
    p.add_argument("--workspace",required=True); p.add_argument("--map",required=True); p.add_argument("--stage",required=True)
    p.add_argument("--project",required=True); p.add_argument("--child",required=True)
    p.add_argument("--apply",action="store_true"); a=p.parse_args(); w=Path(a.workspace).resolve(); s=Path(a.stage).resolve()
    if not contained(s,CORE/"work"/"runs") and not contained(s,w):
        raise SystemExit("F225: stage must be contained by workspace or Tusk run root")
    g=json.loads(GLOBAL_CONFIG.read_text(encoding="utf-8-sig")); project_path=Path(a.project).resolve(strict=False); pr=json.loads((project_path/'PROJECT.json').read_text(encoding="utf-8-sig")); child_path=Path(a.child).resolve(strict=False); ch=json.loads(child_path.read_text(encoding="utf-8-sig"))
    registered={x.get('project_id'):(CORE/'extensions/Tusk_SZ'/x.get('path','')).resolve(strict=False) for x in g.get('projects',[])}
    if registered.get(pr.get('project_id'))!=project_path/'PROJECT.json' or ch.get('parent_project_id')!=pr.get('project_id'): raise SystemExit('F224: authority chain unresolved')
    index=json.loads((project_path/'CHILDREN.json').read_text(encoding='utf-8-sig')); indexed={x.get('work_id'):(project_path/x.get('path','')).resolve(strict=False) for x in index.get('children',[])}
    if indexed.get(ch.get('work_id'))!=child_path:raise SystemExit('F224: child is not registered')
    expected_map=(project_path/pr.get('canonical_map','')).resolve(strict=False)
    if Path(a.map).resolve(strict=False)!=expected_map:raise SystemExit('F224: canonical map is not registered')
    if a.operation=='apply-local' and (not a.apply or ch.get('state')!='running'): raise SystemExit('F224: apply requires running child')
    allowed=[(w/x).resolve(strict=False) for x in ch.get('allowed_paths',[])]; forbidden=[(w/x).resolve(strict=False) for x in ch.get('forbidden_paths',[]) if not Path(x).is_absolute()]; m=json.loads(expected_map.read_text(encoding="utf-8-sig")); rows=[]; blocked=False
    for x in m.get("artifacts",[]):
        lp=(w/x["local_path"]).resolve(); rp=(s/x["stage_path"]).resolve()
        if not contained(lp,w) or not contained(rp,s): raise SystemExit("F226: mapped path escape")
        permitted=any(lp==v or v in lp.parents for v in allowed)
        if a.operation=='apply-local' and not permitted: raise SystemExit('F224: path not allowed by child')
        if a.operation=='apply-local' and any(lp==v or v in lp.parents for v in forbidden):raise SystemExit('F224: path forbidden by child')
        if a.operation=='apply-local' and ('pull' not in x.get('permitted_operations',[]) or x.get('authority') not in ('drive','three_way') or x.get('classification') in ('asset','archive','secret')):raise SystemExit('F224: artifact policy forbids local apply')
        lh=digest(lp) if lp.is_file() else "missing"; rh=digest(rp) if rp.is_file() else "missing"
        d=decision(lh,rh,x.get("accepted_sha256","missing")); blocked|=d=="SYNC-409"
        rows.append({"id":x["id"],"drive_file_id":x.get("drive_file_id"),"local_sha256":lh,"remote_sha256":rh,"decision":d})
        if a.operation=="apply-local" and a.apply and d=="pull":
            lp.parent.mkdir(parents=True,exist_ok=True); tmp=lp.with_name(lp.name+".tusk-tmp"); tmp.write_bytes(rp.read_bytes()); os.replace(tmp,lp)
    print(json.dumps({"schema_version":1,"program_id":"TUSK_SZ_SYNC","root_id":ROOT_ID,"operation":a.operation,"rows":rows,"ok":not blocked},ensure_ascii=False,indent=2))
    return 1 if blocked else 0
if __name__=="__main__":raise SystemExit(main())
