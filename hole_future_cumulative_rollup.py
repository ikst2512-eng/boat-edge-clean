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
from datetime import date
from pathlib import Path

from hole_future_shadow_audit import POLICIES, TOPS

def report_totals_match(flags, claimed_hits, claimed_delta):
    """Cross-check both summary layers against immutable per-race hit booleans."""
    expected_hits={m:{f"top{k}":sum(int(row[m][f"top{k}"]) for row in flags.values())
                      for k in TOPS} for m in POLICIES}
    if claimed_hits!=expected_hits:
        return False
    expected_delta={}
    for m in POLICIES[1:]:
        expected_delta[m]={}
        for k in TOPS:
            key=f"top{k}"
            gain=sum(int(row[m][key] and not row["baseline"][key])
                     for row in flags.values())
            loss=sum(int(row["baseline"][key] and not row[m][key])
                     for row in flags.values())
            expected_delta[m][key]={"gained":gain,"lost":loss,"net":gain-loss}
    return claimed_delta==expected_delta

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
        try:
            start_date=date.fromisoformat(start)
            end_date=date.fromisoformat(end)
            if start_date>=end_date:
                raise ValueError("empty_date_window")
        except (TypeError,ValueError):
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
        # Reject the entire report before accumulating any races if its
        # claimed race dates are not within its own half-open JST window.
        # Also reject malformed codes; a partial report could bias hits.
        try:
            window_codes_valid=all(
                isinstance(code,str) and len(code)==12 and code.isdigit()
                and date(2026,11,4)<=date(int(code[:4]),int(code[4:6]),int(code[6:8]))<end_date
                and date(int(code[:4]),int(code[4:6]),int(code[6:8]))>=start_date
                for code in flags
            )
        except ValueError:
            window_codes_valid=False
        if not window_codes_valid:
            invalid["race_outside_report_window"]+=1;continue
        # Validate every row first, before allowing any report to contribute.
        # A mismatch in one entry must not allow selective hits to leak in.
        if any(not isinstance(values,dict) or set(values)!=set(POLICIES)
               or any(not isinstance(values.get(m),dict) or
                      set(values[m])!={f"top{k}" for k in TOPS} or
                      any(type(values[m][f"top{k}"]) is not bool for k in TOPS)
                      for m in POLICIES) for values in flags.values()):
            invalid["invalid_hit_flags"]+=1;continue
        if not report_totals_match(flags,item.get("hits"),item.get("delta")):
            invalid["summary_totals_mismatch"]+=1;continue
        # Reject the complete report before importing any rows. Otherwise
        # selectively skipping failed races would bias the denominator and
        # allow apparently valid gains to survive a corrupt daily artifact.
        if any(
            (values[m]["top3"] and not values[m]["top5"]) or
            (values[m]["top5"] and not values[m]["top10"])
            for values in flags.values() for m in POLICIES
        ):
            invalid["nonmonotonic_hit_flags"]+=1;continue
        if any(
            values[m]["top3"]!=values["baseline"]["top3"] or
            values[m]["top5"]!=values["baseline"]["top5"]
            for values in flags.values() for m in POLICIES
        ):
            invalid["top5_shift"]+=1;continue
        for code,values in flags.items():
            if code in conflicts:continue
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
    # Filter BEFORE limiting: many PR CI runs can otherwise push all daily
    # scheduled reports beyond the latest N results and hide the cohort.
    ids=[];seen=set();runs_by_event={}
    for event in ("schedule","workflow_dispatch"):
        command=["gh","run","list","--repo",repo,"--workflow",
                 "hole-future-shadow-batch.yml","--event",event,
                 "--limit",str(limit),"--json","databaseId,event,conclusion"]
        listing=subprocess.run(command,capture_output=True,text=True,
                               env=env,timeout=30,check=True)
        listed=json.loads(listing.stdout)
        if not isinstance(listed,list):
            raise ValueError("invalid_event_run_listing")
        runs_by_event[event]=len(listed)
        for item in listed:
            if not isinstance(item,dict) or item.get("event")!=event or (
                    item.get("conclusion")!="success"):
                continue
            run_id=item.get("databaseId")
            if type(run_id) is not int or run_id<=0:
                continue
            if run_id not in seen:
                seen.add(run_id)
                ids.append(run_id)
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
            accepted={"hole_future_batch.json","hole_future_late_7d.json",
                      "hole_future_late_21d.json"}
            files=[p for p in target.rglob("*.json") if p.is_file()
                   and not p.is_symlink() and p.name in accepted]
            names=[p.name for p in files]
            # A run may predate delayed checks. Any duplicate report name
            # or unreadable report invalidates the entire run's contribution.
            if (not files or len(names)!=len(set(names)) or
                    "hole_future_batch.json" not in names or
                    any(p.stat().st_size>3000000 for p in files)):
                failed.append(run_id);continue
            batch=[]
            try:
                for path in files:
                    report=json.loads(path.read_text(encoding="utf-8"))
                    if (not isinstance(report,dict) or
                            report.get("schema")!="HOLE_FUTURE_ARTIFACT_BATCH_V1"):
                        raise ValueError("invalid_daily_report")
                    age=(0 if path.name=="hole_future_batch.json"
                         else 7 if path.name=="hole_future_late_7d.json" else 21)
                    if report.get("recheck_lag_days",0)!=age:
                        raise ValueError("wrong_recheck_lag")
                    batch.append(report)
            except (ValueError,UnicodeError,OSError):
                failed.append(run_id);continue
            reports.extend(batch)
    result=rollup(reports)
    result["runs_listed"]=len(ids)
    result["event_runs_returned"]=runs_by_event
    result["daily_artifacts_read"]=len(reports)
    result["late_recheck_reports_read"]=sum(
        x.get("recheck_lag_days",0) in (7,21) for x in reports)
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
