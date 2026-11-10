"""Opportunistic fail-closed dispatcher for absent research T−12/T−2 runs.

The watchdog is a separate unattended fallback. Its workflow_dispatch events
MUST NOT be counted as schedule-triggered runs or as first-seen proof. It
never writes a forecast and never changes a model/cutoff.
"""
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
import json
import os

JST=timezone(timedelta(hours=9))
REPO="ikst2512-eng/boat-edge-clean"
TARGETS={
    "t12":"entry-course-t12-baseline.yml",
    "t2":"entry-course-late-capture.yml",
}
COOLDOWN=timedelta(minutes=5)
ACTIVE_PROTECTION=timedelta(minutes=30)
PREVIEW_WORKFLOW="research-live-preview-evidence.yml"


def _timestamp(value):
    if type(value) is not str:
        raise ValueError("entry_watchdog_run_timestamp_missing")
    stamp=datetime.fromisoformat(value.replace("Z","+00:00"))
    if stamp.utcoffset() is None:
        raise ValueError("entry_watchdog_run_timestamp_naive")
    return stamp


def dispatch_decision(now, runs, *, kind="t2"):
    """No API or timer side effects; a failed attempt has a bounded cooldown."""
    if not isinstance(now,datetime) or now.utcoffset() is None:
        raise ValueError("entry_watchdog_clock_invalid")
    if not isinstance(runs,list):
        raise ValueError("entry_watchdog_runs_invalid")
    if kind not in TARGETS:
        raise ValueError("entry_watchdog_target_invalid")
    local=now.astimezone(JST)
    first_hour=8 if kind=="t12" else 9
    if not first_hour<=local.hour<=22:
        return "outside_research_hours"
    eligible=[]
    for run in runs:
        if not isinstance(run,dict):
            raise ValueError("entry_watchdog_run_invalid")
        if run.get("event") not in ("schedule","workflow_dispatch"):
            continue
        if run.get("head_branch")!="main":
            continue
        # An unknown run state cannot prove that no capture is active.
        # Reject malformed API records instead of dispatching on ambiguity.
        if run.get("status") not in ("queued", "in_progress", "waiting",
                                     "pending", "requested", "completed"):
            raise ValueError("entry_watchdog_run_status_invalid")
        at=_timestamp(run.get("created_at"))
        age=now-at
        if age<timedelta(minutes=-1):
            raise ValueError("entry_watchdog_future_run_timestamp")
        if age<timedelta(0):
            age=timedelta(0)
        eligible.append((age,run))
    # Active jobs can exceed a short successful-run cooldown. Never overlap.
    if any(run.get("status") in ("queued","in_progress","waiting","pending",
                                "requested") and age<ACTIVE_PROTECTION
           for age,run in eligible):
        return "research_job_already_active"
    if any(age<COOLDOWN for age,_ in eligible):
        return "research_run_recently_started"
    return "dispatch_missing_research_job"


def _call(route, token, *, method="GET", fields=None):
    url=f"https://api.github.com/repos/{REPO}/{route}"
    body=None if fields is None else json.dumps(fields).encode()
    request=Request(url,data=body,method=method,headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"BOAT-EDGE-CLEAN-entry-course-watchdog/1.0",
        **({"Content-Type":"application/json"} if body is not None else {})
    })
    with urlopen(request,timeout=25) as response:
        if method=="POST" and response.status!=204:
            raise ValueError("entry_watchdog_dispatch_not_204")
        if method=="GET" and response.status!=200:
            raise ValueError("entry_watchdog_list_not_200")
        data=response.read(500_001)
    return json.loads(data) if method=="GET" else None


def run_once(*, now, fetch_runs, dispatch):
    report={"schema":"entry-course-unattended-fallback-v1",
            "observed_at":now.isoformat(),"research_only":True,
            "formal":False,"forecast_record":False,
            "unattended_scheduled_capture_verified":False,
            "independent_first_seen_verified":False,
            "targets":{}}
    for kind,file in TARGETS.items():
        # Each event type is queried separately so heavy unrelated runs
        # cannot displace either the cron or fallback records.
        runs=[]
        for event in ("schedule","workflow_dispatch"):
            items=fetch_runs(file,event)
            if not isinstance(items,list):
                raise ValueError("entry_watchdog_api_runs_invalid")
            runs.extend(items)
        decision=dispatch_decision(now,runs,kind=kind)
        record={"decision":decision,
                "observed_schedule_runs":sum(r.get("event")=="schedule" for r in runs),
                "observed_dispatch_runs":sum(r.get("event")=="workflow_dispatch" for r in runs),
                "trigger_is_schedule":False}
        record["dispatch_requested"]=False
        report["targets"][kind]=record
    # Preflight every target before any side effect: a bad T2 API receipt
    # must never cause a partial T12 dispatch without an audit report.
    for kind,file in TARGETS.items():
        record=report["targets"][kind]
        if record["decision"]=="dispatch_missing_research_job":
            dispatch(file)
            record["dispatch_requested"]=True
    return report


def preview_fallback(now, fetch_runs, dispatch):
    """Best-effort independent source capture fallback after critical T12/T2 rescue.

    No new cron; uses the existing watchdog event cadence. A failure in this
    *extra* lookup never prevents the T12/T2 dispatch preflight from running.
    Workflow dispatch is not a scheduled observation or a saved forecast.
    """
    if not isinstance(now,datetime) or now.utcoffset() is None:
        raise ValueError("entry_preview_watchdog_clock_invalid")
    local=now.astimezone(JST)
    record={"workflow":PREVIEW_WORKFLOW,"decision":"outside_preview_hours",
            "observed_schedule_runs":0,"observed_dispatch_runs":0,
            "dispatch_requested":False,"trigger_is_schedule":False,
            "saved_forecast_verified":False}
    if not 9<=local.hour<22:
        return record
    runs=[]
    for event in ("schedule","workflow_dispatch"):
        observed=fetch_runs(PREVIEW_WORKFLOW,event)
        if not isinstance(observed,list):
            raise ValueError("entry_preview_watchdog_api_runs_invalid")
        runs.extend(observed)
    decision=dispatch_decision(now,runs,kind="t2")
    record.update(decision=decision,
                  observed_schedule_runs=sum(r.get("event")=="schedule" for r in runs),
                  observed_dispatch_runs=sum(r.get("event")=="workflow_dispatch" for r in runs))
    if decision=="dispatch_missing_research_job":
        dispatch(PREVIEW_WORKFLOW)
        record["dispatch_requested"]=True
    return record


def main():
    repo=os.environ.get("GITHUB_REPOSITORY")
    if repo!=REPO:
        raise ValueError("entry_watchdog_wrong_repository")
    token=os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError("entry_watchdog_missing_token")
    now=datetime.now(timezone.utc)
    def fetch_runs(file,event):
        from urllib.parse import urlencode
        query=urlencode({"event":event,"per_page":30})
        result=_call(f"actions/workflows/{quote(file)}/runs?{query}",token)
        if not isinstance(result,dict) or not isinstance(result.get("workflow_runs"),list):
            raise ValueError("entry_watchdog_api_schema_invalid")
        return result["workflow_runs"]
    def dispatch(file):
        _call(f"actions/workflows/{quote(file)}/dispatches",token,
              method="POST",fields={"ref":"main"})
    report=run_once(now=now,fetch_runs=fetch_runs,dispatch=dispatch)
    # A preview service outage must not cancel T12/T2 rescue actions already
    # taken. Save an honest independent diagnostic before returning failure.
    preview_error=None
    try:
        report["independent_preview"]=preview_fallback(now,fetch_runs,dispatch)
    except Exception as exc:
        preview_error=exc
        report["independent_preview"]={"workflow":PREVIEW_WORKFLOW,
                "decision":"unverified_preview_fallback_failure",
                "error_type":type(exc).__name__,"dispatch_requested":False,
                "trigger_is_schedule":False,"saved_forecast_verified":False}
    path=Path("entry-course-evidence/activation-watchdog.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,sort_keys=True,ensure_ascii=False)+"\n",
                    encoding="utf-8")
    print("ENTRY_COURSE_ACTIVATION_WATCHDOG="+json.dumps(report,sort_keys=True))
    if preview_error is not None:
        raise preview_error


if __name__=="__main__":
    main()
