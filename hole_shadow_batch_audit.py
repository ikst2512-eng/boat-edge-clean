"""Aggregate immutable hole shadow capture artifacts; read-only, not formal."""
import argparse
import json
import re
from pathlib import Path
from hole_shadow_bundle_audit import audit

TOPS=(3,5,10)
FIELDS=("baseline","shadow","shadow_bundle2")

def batch(root,folder):
    folder=Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        return {"status":"no_capture_artifacts","formal":False,"compared":0}
    paths=sorted(p for p in folder.rglob("hole-shadow.json") if p.is_file() and not p.is_symlink())
    if not paths:
        return {"status":"no_capture_artifacts","formal":False,"compared":0}
    seen=set();counts={x:{f"top{k}":0 for k in TOPS} for x in FIELDS}
    exclusions={};used=[]; rejected=[]
    for path in paths:
        result=audit(root,path)
        for row in result.get("rows",[]):
            code=row["race_code"]
            if code in seen:
                raise ValueError("duplicate_race_across_capture_artifacts:"+code)
            seen.add(code)
            used.append(code)
            for key in FIELDS:
                for k in TOPS:
                    counts[key][f"top{k}"]+=int(row["flags"][key][f"top{k}"])
        for row in result.get("excluded",[]):
            key=row.get("reason","unspecified")
            exclusions[key]=exclusions.get(key,0)+1
        rejected.extend({"file":str(path),"status":result["status"]} for _ in [0]
                        if result["status"] not in ("retrospective_shadow_comparison","no_comparable_shadow"))
    n=len(used)
    delta={key:{f"top{k}":{"baseline":counts["baseline"][f"top{k}"],
                             "candidate":counts[key][f"top{k}"],
                             "net":counts[key][f"top{k}"]-counts["baseline"][f"top{k}"]}
                for k in TOPS} for key in ("shadow","shadow_bundle2")}
    return {"schema":"HOLE_SHADOW_BATCH_V1",
            "status":"retrospective_batch_only" if n else "no_comparable_results",
            "formal":False,"independent_first_receipt_verified":False,
            "prospective_validation":False,"production_forecast_changed":False,
            "capture_artifacts":len(paths),"compared":n,"excluded_by_reason":exclusions,
            "invalid_artifacts":rejected,"race_codes":used,"hits":counts,"delta":delta,
            "warning":"Same-job captures do not prove independently received predeadline. This is NOT formal accuracy."}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=".")
    p.add_argument("--artifacts",required=True)
    args=p.parse_args()
    print(json.dumps(batch(args.root,args.artifacts),ensure_ascii=False,sort_keys=True))
