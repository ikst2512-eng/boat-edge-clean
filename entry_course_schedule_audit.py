"""Independent daily operational evidence: GitHub schedule runs vs ledger paths.

Read-only. Counts run events and file paths, NOT verified pre-cutoff originals,
independent first-seen certificates, successful predictions, or hit rates.
Manual/PR/dispatch runs must never be credited as unattended collection.
"""
from collections import Counter
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlencode
import json
import re
import subprocess

from entry_course_archive_integrity_audit import audit_archive_bytes
from entry_course_first_add_audit import audit_first_add

JST=timezone(timedelta(hours=9))
REPO="ikst2512-eng/boat-edge-clean"
BRANCH="entry-course-evidence-ledger"
WORKFLOWS={
    "t12":("entry-course-t12-baseline.yml",("t12_baselines",)),
    "t2":("entry-course-late-capture.yml",("waku10","entry_course")),
}
DAY=re.compile(r"20[0-9]{6}\Z")
CODE=re.compile(r"20[0-9]{10}\.json\Z")


def _api(route):
    proc=subprocess.run(["gh","api","-X","GET",route],
                        capture_output=True,timeout=35)
    if proc.returncode:
        raise ValueError("schedule_audit_github_api_failed")
    try:
        return json.loads(proc.stdout)
    except (UnicodeError,ValueError) as exc:
        raise ValueError("schedule_audit_malformed_github_json") from exc


def _observed(value):
    if not isinstance(value,str):
        return None
    try:
        t=datetime.fromisoformat(value.replace("Z","+00:00"))
        return t if t.utcoffset() is not None else None
    except ValueError:
        return None


def _runs(workflow, day, fetch):
    start=datetime.strptime(day,"%Y%m%d").replace(tzinfo=JST)
    end=start+timedelta(days=1)
    # Query a UTC window, then independently filter by exact Japan day.
    begin=(start-timedelta(hours=1)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    finish=(end+timedelta(hours=1)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    params={"event":"schedule","created":begin+".."+finish,"per_page":100}
    seen=set()
    collected=[]
    for page in range(1,8):
        query=urlencode(dict(params,page=page))
        result=fetch(f"repos/{REPO}/actions/workflows/{workflow}/runs?{query}")
        if not isinstance(result,dict) or type(result.get("workflow_runs")) is not list:
            raise ValueError("schedule_audit_workflow_result_invalid")
        rows=result["workflow_runs"]
        for item in rows:
            if not isinstance(item,dict):
                raise ValueError("schedule_audit_run_invalid")
            if item.get("event")!="schedule":
                continue
            at=_observed(item.get("created_at"))
            if at is None:
                raise ValueError("schedule_audit_missing_run_created_at")
            if not start<=at.astimezone(JST)<end:
                continue
            run_id=item.get("id")
            if type(run_id) is not int:
                raise ValueError("schedule_audit_missing_run_id")
            if run_id in seen:
                continue
            seen.add(run_id)
            collected.append({"id":run_id,"created_at":at.isoformat(),
                              "status":item.get("status"),
                              "conclusion":item.get("conclusion"),
                              "head_sha":item.get("head_sha")})
        if len(rows)<100:
            break
    else:
        raise ValueError("schedule_audit_run_pagination_incomplete")
    return collected


def _tree_entries(fetch):
    data=fetch(f"repos/{REPO}/git/trees/{BRANCH}?recursive=1")
    if not isinstance(data,dict) or data.get("truncated") is True:
        raise ValueError("schedule_audit_ledger_tree_truncated")
    rows=data.get("tree")
    if type(rows) is not list:
        raise ValueError("schedule_audit_ledger_tree_invalid")
    return rows


def _tree_paths(fetch):
    return [r["path"] for r in _tree_entries(fetch) if isinstance(r,dict)
            and r.get("type")=="blob" and isinstance(r.get("path"),str)]


def operational_audit(day, *, fetch=_api, today=None):
    if type(day) is not str or not DAY.fullmatch(day):
        raise ValueError("schedule_audit_bad_day")
    try:
        target=datetime.strptime(day,"%Y%m%d").date()
    except ValueError as exc:
        raise ValueError("schedule_audit_bad_day") from exc
    if today is None:
        today=datetime.now(JST).date()
    if target>=today:
        raise ValueError("schedule_audit_requires_completed_jst_day")
    tree=_tree_entries(fetch)
    paths=[r["path"] for r in tree if isinstance(r,dict)
           and r.get("type")=="blob" and isinstance(r.get("path"),str)]
    result={}
    for kind,(workflow,prefixes) in WORKFLOWS.items():
        executions=_runs(workflow,day,fetch)
        decisions=Counter()
        for r in executions:
            if r["status"]=="completed" and r["conclusion"]=="success":
                decisions["success"]+=1
            elif r["status"]=="completed":
                decisions["failed_or_cancelled"]+=1
            else:
                decisions["incomplete"]+=1
        files=sorted(path for path in paths if
            any(path.startswith(f"{prefix}/{day}/") for prefix in prefixes) and
            CODE.fullmatch(path.rsplit("/",1)[-1]) and
            path.rsplit("/",1)[-1][:8]==day)
        result[kind]={
            "workflow":workflow,
            "scheduled_run_count":len(executions),
            "completed_success_run_count":decisions["success"],
            "completed_failure_run_count":decisions["failed_or_cancelled"],
            "incomplete_run_count":decisions["incomplete"],
            "archived_candidate_path_count":len(files),
            "archived_candidate_paths":files,
            "scheduled_run_ids":[r["id"] for r in executions],
            "status":(
                "missing_scheduled_runs" if not executions else
                "no_candidate_archive_paths" if not files else
                "schedule_runs_and_paths_observed_unverified"
            ),
        }
    integrity=audit_archive_bytes(day,tree,fetch,repository=REPO)
    first_add=audit_first_add(integrity["internally_validated_paths"],
                              fetch=fetch,repository=REPO)
    path_count=sum(r["archived_candidate_path_count"] for r in result.values())
    return {"schema":"entry-course-scheduled-ledger-path-audit-v2",
            "date_jst":day,"scope":"completed_jst_day",
            "t12":result["t12"],"t2":result["t2"],
            "no_scheduled_run_assumed_success":True,
            "archive_integrity":integrity,
            "first_add_commit_audit":first_add,
            "archive_paths_not_byte_verified":(
                integrity["blob_sha_and_internal_payload_valid_count"]!=path_count),
            "independent_first_add_commit_verified":False,
            "pre_cutoff_provenance_verified":False,
            "research_only":True,"formal":False,
            "prediction_hit_rate_verified":False}


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--day",default=(datetime.now(JST).date()-timedelta(days=1)).strftime("%Y%m%d"))
    p.add_argument("--output",default="entry-course-evidence/operational-audit.json")
    args=p.parse_args()
    try:
        result=operational_audit(args.day)
    except Exception as exc:
        result={"schema":"entry-course-scheduled-ledger-path-audit-v2",
                "date_jst":args.day,"status":"audit_failed",
                "error_type":type(exc).__name__,
                "research_only":True,"formal":False}
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("ENTRY_COURSE_SCHEDULE_AUDIT="+json.dumps(result,ensure_ascii=False,sort_keys=True))
    if result.get("status")=="audit_failed":
        raise SystemExit(2)


if __name__=="__main__":
    main()
