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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from hole_capture_artifact_inventory import api
from hole_shadow_stage_verdict import classify
from hole_future_shadow_audit import audit, POLICIES, TOPS
from hole_future_locked_eval import verify_locked_selection
from hole_future_result_coverage import reconcile

def aggregate(root,artifacts,window_start=None,window_end_exclusive=None):
    """Score only the stated race-day window; run start date is not race date."""
    root=Path(root);artifacts=Path(artifacts)
    verify_locked_selection()
    if (window_start is None)!=(window_end_exclusive is None):
        raise ValueError("incomplete_race_day_window")
    if window_start is not None:
        first=date.fromisoformat(window_start)
        last=date.fromisoformat(window_end_exclusive)
        if first>=last:
            raise ValueError("invalid_race_day_window")
    else:
        first=last=None
    def in_window(code):
        if not isinstance(code,str) or not re.fullmatch(r"20[0-9]{10}",code):
            return False
        try:
            day=date.fromisoformat(code[:4]+"-"+code[4:6]+"-"+code[6:8])
        except ValueError:
            return False
        return (day>=date(2026,11,4) and
                (first is None or first<=day<last))
    if artifacts.is_symlink() or not artifacts.is_dir():
        return {"status":"no_artifact_directory","formal":False,"comparable":0}
    files=sorted(p for p in artifacts.rglob("hole-shadow.json") if p.is_file() and not p.is_symlink())
    examined=0;all_rows={};duplicates=set();excluded=Counter();nonusable=Counter();shadow_statuses=Counter()
    outside_window=set()
    source_snapshots={}
    identical_repeated_codes=set()
    replay_verified_codes=set()
    declared_failed_replay_codes=set()
    for path in files:
        examined+=1
        file_codes=set()
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
            records=data.get("records") if isinstance(data,dict) else None
            if not isinstance(records,list):
                nonusable["invalid_record_set"]+=1;continue
            shadow_statuses[str(data.get("status","missing_status"))]+=1
            # Record duplicate codes regardless of whether a result is currently settled.
            for record in records:
                code=record.get("race_code") if isinstance(record,dict) else None
                if in_window(code):
                    file_codes.add(code)
                    # Byte-equivalent source records from repeated Actions runs
                    # are one frozen prediction, not two independent races.
                    # Any different snapshot for the same race is ambiguous.
                    snapshot=json.dumps(record,sort_keys=True,separators=(",",":"))
                    if code in source_snapshots:
                        if source_snapshots[code]!=snapshot:
                            duplicates.add(code)
                        else:
                            identical_repeated_codes.add(code)
                    else:
                        source_snapshots[code]=snapshot
                    all_rows.setdefault(code,None)
                elif first is not None and isinstance(code,str) and re.fullmatch(r"20[0-9]{10}",code):
                    outside_window.add(code)
            scored=audit(root,path)
            # The per-file auditor must never invent a scored race not in
            # the frozen artifact or score it without passing replay.
            eligible=scored.get("eligible_codes",[])
            scored_rows=scored.get("rows",[])
            if not isinstance(eligible,list) or not isinstance(scored_rows,list):
                raise ValueError("invalid_audit_contract")
            eligible_in_window=[code for code in eligible if in_window(code)]
            if (len(eligible_in_window)!=len(set(eligible_in_window)) or
                    not set(eligible_in_window).issubset(file_codes)):
                raise ValueError("unbacked_eligible_code")
            scored_in_window=[row for row in scored_rows
                              if isinstance(row,dict) and in_window(row.get("race_code"))]
            scored_codes=[row["race_code"] for row in scored_in_window]
            if (len(scored_codes)!=len(set(scored_codes)) or
                    not set(scored_codes).issubset(set(eligible_in_window))):
                raise ValueError("unbacked_scored_row")
            for row in scored_in_window:
                flags=row.get("flags")
                if not isinstance(flags,dict) or set(flags)!=set(POLICIES):
                    raise ValueError("invalid_audit_flags")
                for mode in POLICIES:
                    outcome=flags[mode]
                    if (not isinstance(outcome,dict) or
                            set(outcome)!={f"top{k}" for k in TOPS} or
                            any(type(outcome[f"top{k}"]) is not bool for k in TOPS)):
                        raise ValueError("invalid_audit_flags")
                    if (outcome["top3"] and not outcome["top5"] or
                            outcome["top5"] and not outcome["top10"]):
                        raise ValueError("nonmonotonic_hit_flags")
        except (OSError,UnicodeError,ValueError,KeyError,TypeError) as exc:
            # If one artifact is invalid, its race cannot be rescued by a
            # duplicate from another run without proving which is canonical.
            duplicates.update(file_codes)
            nonusable[type(exc).__name__]+=1;continue
        eligible_this_file={code for code in scored.get("eligible_codes",[])
                            if in_window(code)}
        replay_verified_codes.update(eligible_this_file)
        # A good copy cannot rescue a second copy which was never replay
        # validated (bad hash, late timestamp, missing candidate, wrong method).
        declared_failed_replay_codes.update(file_codes-eligible_this_file)
        for name,n in scored.get("excluded_by_reason",{}).items():
            excluded[name]+=n
        for row in scored.get("rows",[]):
            code=row["race_code"]
            if not in_window(code):
                if first is not None and isinstance(code,str):
                    outside_window.add(code)
                continue
            if code in all_rows and all_rows[code] is not None:
                if all_rows[code]!=row:
                    duplicates.add(code)
            else:
                all_rows[code]=row
    # Every declared copy must pass candidate replay. A valid earlier copy
    # cannot make another invalid same-race record appear independently valid.
    duplicates.update(declared_failed_replay_codes)
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
            "identical_snapshot_codes_deduplicated":sorted(identical_repeated_codes-duplicates),
            "codes_quarantined_for_failed_replay":sorted(declared_failed_replay_codes),
            "excluded_outside_race_day_window":len(outside_window),
            "outside_race_day_codes":sorted(outside_window),
            "comparable":len(rows),"race_codes":[r["race_code"] for r in rows],
            "per_race_flags":{r["race_code"]:r["flags"] for r in rows},
            "observed_future_codes":sorted(replay_verified_codes-duplicates),
            "declared_future_codes":sorted(set(all_rows)|duplicates),
            "declared_but_not_replay_verified_codes":sorted((set(all_rows)|duplicates)-replay_verified_codes),
            "excluded_by_reason":dict(excluded),"invalid_artifacts":dict(nonusable),
            "shadow_status_counts":dict(shadow_statuses),
            "hits":hits,"delta":delta,
            "warning":"These are result-blind same-job locally frozen snapshots, NOT independently verified first receipts. Empty or incomplete capture window cannot establish accuracy."}

JST=timezone(timedelta(hours=9))
PAGE_SIZE=100
MAX_PAGES=4
MAX_DOWNLOADS=180

def discover_full_days(repo,token,days=2,as_of_jst=None,capture_lookback_days=0):
    """Page GitHub runs by CREATED date, not a small latest-N limit.

    Include only completed JST days; partially collected current-day runs must
    not masquerade as a complete daily accuracy cohort.
    """
    if type(days) is not int or not 1<=days<=3:
        raise ValueError("invalid_day_window")
    if type(capture_lookback_days) is not int or not 0<=capture_lookback_days<=1:
        raise ValueError("invalid_capture_lookback")
    now=as_of_jst or datetime.now(JST)
    if now.utcoffset()!=timedelta(hours=9):
        raise ValueError("as_of_must_be_jst")
    end_day=now.date()  # exclusive: today is incomplete
    first_day=end_day-timedelta(days=days)
    capture_first_day=first_day-timedelta(days=capture_lookback_days)
    base="https://api.github.com/repos/"+repo
    runs=[];seen=set();listing_complete=False
    pages=0
    for page in range(1,MAX_PAGES+1):
        url=(base+"/actions/workflows/four-mode-prospective-capture.yml/runs"
             +"?per_page="+str(PAGE_SIZE)+"&page="+str(page))
        response=json.loads(api(url,token))
        page_runs=response.get("workflow_runs",[])
        if not isinstance(page_runs,list):
            raise ValueError("invalid_workflow_listing")
        pages=page
        oldest_day=None
        for item in page_runs:
            created=item.get("created_at")
            if not isinstance(created,str):
                continue
            timestamp=datetime.fromisoformat(created.replace("Z","+00:00"))
            if timestamp.utcoffset() is None:continue
            local_day=timestamp.astimezone(JST).date()
            if oldest_day is None or local_day<oldest_day:oldest_day=local_day
            if capture_first_day<=local_day<end_day and item.get("event") in ("schedule","workflow_dispatch"):
                run_id=item["id"]
                if run_id in seen:raise ValueError("duplicate_run_in_listing")
                seen.add(run_id);runs.append(item)
        # Older-than-window entry proves traversal reached the window boundary.
        if len(page_runs)<PAGE_SIZE or (oldest_day is not None and oldest_day<capture_first_day):
            listing_complete=True
            break
    return {"candidates":runs,"listing_complete":listing_complete,
            "pages_fetched":pages,"window_start_jst":first_day.isoformat(),
            "capture_window_start_jst":capture_first_day.isoformat(),
            "capture_lookback_days":capture_lookback_days,
            "window_end_exclusive_jst":end_day.isoformat(),"days":days}


def read_evidence_json(folder,name):
    """Bounded, non-symlink evidence read; absent and malformed remain distinct."""
    path=folder/name
    if path.is_symlink() or not path.is_file():
        return None
    if path.stat().st_size>2000000:
        return None
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value,dict) else None
    except (OSError,UnicodeError,ValueError):
        return None


def summarize_downloaded_runs(root,run_ids):
    """Evidence status for every successful download, even without hole-shadow."""
    root=Path(root)
    rows=[]
    for run_id in run_ids:
        run_dir=root/str(run_id)
        if run_dir.is_symlink() or not run_dir.is_dir():
            rows.append({"run_id":run_id,"stage":"download_directory_missing",
                         "has_hole_shadow":False})
            continue
        # GitHub CLI may nest artifacts by artifact name; discover exact one.
        publication_paths=[p for p in run_dir.rglob("publication.json")
                           if p.is_file() and not p.is_symlink()]
        stage_paths=[p for p in run_dir.rglob("stages.json")
                     if p.is_file() and not p.is_symlink()]
        shadow_paths=[p for p in run_dir.rglob("hole-shadow.json")
                      if p.is_file() and not p.is_symlink()]
        if any(len(x)>1 for x in (publication_paths,stage_paths,shadow_paths)):
            rows.append({"run_id":run_id,"stage":"ambiguous_multiple_evidence_files",
                         "has_hole_shadow":False})
            continue
        publication=(read_evidence_json(publication_paths[0].parent,"publication.json")
                     if publication_paths else None)
        stages=(read_evidence_json(stage_paths[0].parent,"stages.json")
                if stage_paths else None)
        shadow=(read_evidence_json(shadow_paths[0].parent,"hole-shadow.json")
                if shadow_paths else None)
        rows.append({"run_id":run_id,
                     "stage":classify(stages,publication,shadow),
                     "publication_outcome":publication.get("outcome") if publication else None,
                     "has_hole_shadow":bool(shadow_paths),
                     "shadow_records":len(shadow["records"]) if shadow and
                           isinstance(shadow.get("records"),list) else None})
    return rows

def late_window_as_of(now_jst, lag_days, days=1):
    """A check N days later must include the race day now-N, not the day before.

    discover_full_days uses an exclusive end date. For N=7 and days=1,
    today's 2026-11-11 run must inspect 2026-11-04, not 2026-11-03.
    """
    if now_jst.tzinfo is None or now_jst.utcoffset()!=timedelta(hours=9):
        raise ValueError("now_must_be_jst")
    if type(lag_days) is not int or not 0<=lag_days<=28:
        raise ValueError("invalid_lag_days")
    if type(days) is not int or not 1<=days<=3:
        raise ValueError("invalid_day_window")
    # Shift the exclusive end to the day after the target race day.
    return now_jst-timedelta(days=max(lag_days-1,0))


def collect_recent(root,repo,token,days=2,as_of_jst=None):
    if not repo or not token:raise ValueError("credentials_required")
    discovery=discover_full_days(repo,token,days,as_of_jst,capture_lookback_days=1)
    candidates=discovery["candidates"]
    failures=[];downloaded=[]
    with tempfile.TemporaryDirectory() as directory:
        dest=Path(directory)
        for entry in candidates[:MAX_DOWNLOADS]:
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
        result=aggregate(root,dest,discovery["window_start_jst"],
                         discovery["window_end_exclusive_jst"])
        run_evidence=summarize_downloaded_runs(dest,downloaded)
    result["downloaded_run_evidence"]=run_evidence
    result["downloaded_stage_counts"]=dict(Counter(
        item["stage"] for item in run_evidence))
    result["runs_in_window"]=len(candidates)
    result["runs_inspected"]=min(len(candidates),MAX_DOWNLOADS)
    result["runs_downloaded"]=len(downloaded)
    result["downloaded_runs_without_shadow"]=max(0,len(downloaded)-result["artifact_files"])
    result["run_download_failures"]=failures
    result["window_start_jst"]=discovery["window_start_jst"]
    result["capture_window_start_jst"]=discovery["capture_window_start_jst"]
    result["capture_lookback_days"]=discovery["capture_lookback_days"]
    result["window_end_exclusive_jst"]=discovery["window_end_exclusive_jst"]
    result["repository_result_coverage"]=reconcile(root,
        discovery["window_start_jst"],discovery["window_end_exclusive_jst"],
        result["observed_future_codes"],result["race_codes"])
    result["pages_fetched"]=discovery["pages_fetched"]
    result["run_listing_complete"]=discovery["listing_complete"]
    result["download_limit_reached"]=len(candidates)>MAX_DOWNLOADS
    result["capture_window_complete"]=(
        discovery["listing_complete"] and len(candidates)>0 and not failures
        and len(candidates)<=MAX_DOWNLOADS
        and len(downloaded)==len(candidates)
        and result["downloaded_runs_without_shadow"]==0)
    result["repository_result_coverage"]["checked_out_file_coverage_complete"]=(
        result["capture_window_complete"] and result["repository_result_coverage"]["confirmed"]>0
        and result["repository_result_coverage"]["confirmed_without_shadow"]==0
        and result["repository_result_coverage"]["confirmed_shadow_but_unscored"]==0)
    result["warning"]+=" Run discovery includes the preceding JST day for advance-published predictions; only requested race dates are scored. Complete capture window describes artifact retrieval ONLY, not race/result completeness or independent first receipt."
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=".")
    p.add_argument("--artifacts",default=None)
    p.add_argument("--days",type=int,default=2)
    p.add_argument("--lag-days",type=int,default=0,
                   help="Revisit a completed historical JST window; does not change frozen tickets")
    opts=p.parse_args()
    if opts.artifacts:
        x=aggregate(opts.root,opts.artifacts)
    else:
        if type(opts.lag_days) is not int or opts.lag_days<0 or opts.lag_days>28:
            raise ValueError("invalid_lag_days")
        observation_time=late_window_as_of(datetime.now(JST),opts.lag_days,opts.days)
        x=collect_recent(opts.root,os.environ["GITHUB_REPOSITORY"],
                         os.environ["GH_TOKEN"],opts.days,observation_time)
        x["recheck_lag_days"]=opts.lag_days
    print(json.dumps(x,ensure_ascii=False,sort_keys=True))
