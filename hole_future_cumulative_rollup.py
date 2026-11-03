"""Conservative cumulative hole-mode research summary from previous daily CI artifacts.

Daily overlapping windows may repeat one race. Only identical, checked flags
are deduplicated. Conflicts are quarantined, never silently picked. This is
NOT a formal first-receipt validation or a complete sample census.
"""
import argparse
import json
import os
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from hole_future_shadow_audit import POLICIES, TOPS

def rollup(reports):
    rows={}; conflicts=set(); invalid=Counter(); days=set()
    report_count=0; covered=set(); partial=0; all_reports=[]
    for item in reports:
        report_count+=1
        if not isinstance(item,dict) or item.get("formal") is not False or (
                item.get("independent_first_receipt_verified") is not False):
            invalid["untrusted_report"]+=1;continue
        if item.get("schema")!="HOLE_FUTURE_ARTIFACT_BATCH_V1":
            invalid["schema_mismatch"]+=1;continue
        start=item.get("window_start_jst");end=item.get("window_end_exclusive_jst")
        if not isinstance(start,str) or not isinstance(end,str) or start>=end:
            invalid["invalid_window"]+=1;continue
        all_reports.append({"start":start,"end":end,
                            "capture_complete":item.get("capture_window_complete") is True})
        days.add((start,end))
        if item.get("capture_window_complete") is not True:
            partial+=1
        flags=item.get("per_race_flags")
        if not isinstance(flags,dict) or set(flags)!=set(item.get("race_codes",[])) or (
                item.get("comparable")!=len(flags)):
            invalid["missing_or_inconsistent_race_flags"]+=1;continue
        for code,values in flags.items():
            if not isinstance(code,str) or len(code)!=12 or not code.isdigit() or code[:8]<"20261104":
                invalid["invalid_race_code"]+=1;continue
            if code in conflicts:continue
            if not isinstance(values,dict) or set(values)!=set(POLICIES):
                invalid["invalid_modes"]+=1;continue
            if any(set(values[mode])!={f"top{k}" for k in TOPS} or
                   any(type(values[mode][f"top{k}"]) is not bool for k in TOPS)
                   for mode in POLICIES):
                invalid["invalid_hit_flags"]+=1;continue
            if any(values[m]["top3"]!=values["baseline"]["top3"] or
                   values[m]["top5"]!=values["baseline"]["top5"] for m in POLICIES):
                invalid["top5_shift"]+=1;continue
            # The same date can recur in rolling daily windows.
            if code in rows and rows[code]!=values:
                rows.pop(code);conflicts.add(code)
            else:
                rows[code]=values
    counts={m:{f"top{k}":0 for k in TOPS} for m in POLICIES}
    for row in rows.values():
        for m in POLICIES:
            for k in TOPS:counts[m][f"top{k}"]+=int(row[m][f"top{k}"])
    delta={}
    for m in POLICIES[1:]:
        delta[m]={}
        for k in TOPS:
            key=f"top{k}"
            gain=sum(int(row[m][key] and not row["baseline"][key]) for row in rows.values())
            loss=sum(int(row["baseline"][key] and not row[m][key]) for row in rows.values())
            if gain-loss!=counts[m][key]-counts["baseline"][key]:
                raise ValueError("attribution_mismatch")
            delta[m][key]={"gained":gain,"lost":loss,"net":gain-loss}
    return {"schema":"HOLE_CUMULATIVE_EVIDENCE_V1",
            "status":"incomplete_cumulative_research",
            "reports_read":report_count,"window_records":len(days),
            "incomplete_window_reports":partial,
            "invalid_report_counts":dict(invalid),
            "conflicted_codes_quarantined":sorted(conflicts),
            "comparable":len(rows),"race_codes":sorted(rows),
            "hits":counts,"delta":delta,
            "historical_reporting_coverage_proven":False,
            "formal":False,"prospective_validation":False,
            "independent_first_receipt_verified":False,"production_forecast_changed":False,
            "warning":"Artifact report rollup only. Missing or expired daily artifacts, late results beyond rolling window, unconfirmed race census, or first receipt proof can invalidate the denominator."}

def fetch_previous(repo,limit=40):
    if not repo or type(limit) is not int or not 1<=limit<=70:
        raise ValueError("invalid_request")
    env={**os.environ}
    command=["gh","run","list","--repo",repo,"--workflow",
             "hole-future-shadow-batch.yml","--limit",str(limit),
             "--json","databaseId,event,conclusion"]
    listing=subprocess.run(command,capture_output=True,text=True,env=env,timeout=30,check=True)
    ids=[item["databaseId"] for item in json.loads(listing.stdout)
         if item.get("event") in ("schedule","workflow_dispatch")
         and item.get("conclusion")=="success"]
    reports=[];failed=[]
    with tempfile.TemporaryDirectory() as directory:
        for run_id in ids:
            target=Path(directory)/str(run_id);target.mkdir()
            result=subprocess.run(["gh","run","download",str(run_id),"--repo",repo,
                                  "--pattern","hole-future-shadow-batch",
                                  "--dir",str(target)],
                                  capture_output=True,text=True,env=env,timeout=45)
            if result.returncode!=0:
                failed.append(run_id);continue
            files=[p for p in target.rglob("hole_future_batch.json")
                   if p.is_file() and not p.is_symlink()]
            if len(files)!=1 or files[0].stat().st_size>3000000:
                failed.append(run_id);continue
            try:reports.append(json.loads(files[0].read_text(encoding="utf-8")))
            except (ValueError,UnicodeError,OSError):failed.append(run_id)
    result=rollup(reports)
    result["runs_listed"]=len(ids)
    result["daily_artifacts_read"]=len(reports)
    result["unavailable_daily_run_ids"]=failed
    result["run_list_cap"]=limit
    result["history_exhaustive"]=False
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--reports",default=None)
    p.add_argument("--limit",type=int,default=40)
    a=p.parse_args()
    if a.reports:
        folder=Path(a.reports)
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError("missing_report_dir")
        reports=[json.loads(x.read_text(encoding="utf-8"))
                 for x in sorted(folder.rglob("hole_future_batch.json"))
                 if x.is_file() and not x.is_symlink()]
        out=rollup(reports)
    else:out=fetch_previous(os.environ["GITHUB_REPOSITORY"],a.limit)
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
