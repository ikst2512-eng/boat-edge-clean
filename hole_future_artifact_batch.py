"""Research-only scoring of uniquely observed future hole snapshots from actual capture artifacts.

Absence, duplicate snapshots, unreadable artifacts, and unverified first receipt are
explicit. No alternative reconstruction from forecasts is counted as a frozen pick.
"""
import argparse
import json
import os
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from hole_capture_artifact_inventory import api
from hole_future_shadow_audit import audit, POLICIES, TOPS
from hole_future_locked_eval import verify_locked_selection

def aggregate(root,artifacts):
    root=Path(root);artifacts=Path(artifacts)
    verify_locked_selection()
    if artifacts.is_symlink() or not artifacts.is_dir():
        return {"status":"no_artifact_directory","formal":False,"comparable":0}
    files=sorted(p for p in artifacts.rglob("hole-shadow.json") if p.is_file() and not p.is_symlink())
    examined=0;all_rows={};duplicates=set();excluded=Counter();nonusable=Counter();shadow_statuses=Counter()
    for path in files:
        examined+=1
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
            records=data.get("records") if isinstance(data,dict) else None
            if not isinstance(records,list):
                nonusable["invalid_record_set"]+=1;continue
            shadow_statuses[str(data.get("status","missing_status"))]+=1
            # Record duplicate codes regardless of whether a result is currently settled.
            for record in records:
                code=record.get("race_code") if isinstance(record,dict) else None
                if isinstance(code,str) and re.fullmatch(r"20\d{10}",code) and code[:8]>="20261104":
                    if code in all_rows:duplicates.add(code)
                    all_rows.setdefault(code,None)
            scored=audit(root,path)
        except (OSError,UnicodeError,ValueError,KeyError,TypeError) as exc:
            nonusable[type(exc).__name__]+=1;continue
        for name,n in scored.get("excluded_by_reason",{}).items():
            excluded[name]+=n
        for row in scored.get("rows",[]):
            code=row["race_code"]
            if not isinstance(code,str) or code[:8]<"20261104":
                raise ValueError("invalid_scored_date")
            if code in all_rows and all_rows[code] is not None:
                duplicates.add(code)
            all_rows[code]=row
    # Quarantine any repeated race entirely. Different artifact runs must not inflate n.
    for code in duplicates:all_rows.pop(code,None)
    rows=[x for x in all_rows.values() if x is not None]
    rows.sort(key=lambda x:x["race_code"])
    hits={name:{f"top{k}":0 for k in TOPS} for name in POLICIES}
    for row in rows:
        for name in POLICIES:
            for k in TOPS:hits[name][f"top{k}"]+=int(row["flags"][name][f"top{k}"])
    delta={}
    for name in POLICIES[1:]:
        delta[name]={}
        for k in TOPS:
            key=f"top{k}";gained=sum(int(r["flags"][name][key] and not r["flags"]["baseline"][key]) for r in rows)
            lost=sum(int(r["flags"]["baseline"][key] and not r["flags"][name][key]) for r in rows)
            if gained-lost!=hits[name][key]-hits["baseline"][key]:
                raise ValueError("inconsistent_delta")
            delta[name][key]={"gained":gained,"lost":lost,"net":gained-lost}
            if k in (3,5) and (gained or lost):
                raise ValueError("top5_changed")
    return {"schema":"HOLE_FUTURE_ARTIFACT_BATCH_V1",
            "status":"shadow_research_comparable" if rows else "no_verified_local_shadows_with_results",
            "formal":False,"independent_first_receipt_verified":False,
            "prospective_validation":False,"production_forecast_changed":False,
            "artifact_files":examined,"distinct_future_codes_seen":len(all_rows)+len(duplicates),
            "duplicate_codes_quarantined":sorted(duplicates),
            "comparable":len(rows),"race_codes":[r["race_code"] for r in rows],
            "excluded_by_reason":dict(excluded),"invalid_artifacts":dict(nonusable),
            "shadow_status_counts":dict(shadow_statuses),
            "hits":hits,"delta":delta,
            "warning":"These are result-blind same-job locally frozen snapshots, NOT independently verified first receipts. Empty or incomplete capture window cannot establish accuracy."}

def collect_recent(root,repo,token,limit=20):
    if not repo or not token:raise ValueError("credentials_required")
    if type(limit) is not int or not 1<=limit<=40:raise ValueError("invalid_run_limit")
    base="https://api.github.com/repos/"+repo
    response=json.loads(api(base+"/actions/workflows/four-mode-prospective-capture.yml/runs?per_page="+str(limit),token))
    candidates=[r for r in response.get("workflow_runs",[])
                if r.get("event") in ("schedule","workflow_dispatch")
                and isinstance(r.get("created_at"),str)
                and r["created_at"][:10]>="2026-11-03"]
    failures=[];downloaded=[]
    with tempfile.TemporaryDirectory() as directory:
        dest=Path(directory)
        for entry in candidates:
            run_id=entry["id"]
            run_dir=dest/str(run_id);run_dir.mkdir()
            env={**os.environ,"GH_TOKEN":token}
            try:
                result=subprocess.run(["gh","run","download",str(run_id),
                                       "--repo",repo,"--pattern","four-mode-capture-*",
                                       "--dir",str(run_dir)],capture_output=True,
                                      text=True,env=env,timeout=90)
                if result.returncode:
                    failures.append({"run_id":run_id,"reason":"download_failed"})
                else:
                    downloaded.append(run_id)
            except (OSError,subprocess.TimeoutExpired):
                failures.append({"run_id":run_id,"reason":"download_error"})
        result=aggregate(root,dest)
    result["runs_inspected"]=len(candidates)
    result["runs_downloaded"]=len(downloaded)
    result["downloaded_runs_without_shadow"]=max(0,len(downloaded)-result["artifact_files"])
    result["run_download_failures"]=failures
    result["run_list_limit"]=limit
    result["capture_window_complete"]=False
    result["warning"]+=" At most recent N workflow runs; capture history is not exhaustive."
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=".")
    p.add_argument("--artifacts",default=None)
    p.add_argument("--runs",type=int,default=20)
    opts=p.parse_args()
    if opts.artifacts:
        x=aggregate(opts.root,opts.artifacts)
    else:
        x=collect_recent(opts.root,os.environ["GITHUB_REPOSITORY"],
                         os.environ["GH_TOKEN"],opts.runs)
    print(json.dumps(x,ensure_ascii=False,sort_keys=True))
