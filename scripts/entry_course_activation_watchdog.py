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


def _timestamp(value):
    if type(value) is not str:
        raise ValueError("entry_watchdog_run_timestamp_missing")
    stamp=datetime.fromisoformat(value.replace("Z","+00:00"))
    if stamp.utcoffset() is None:
        raise ValueError("entry_watchdog_run_timestamp_naive")
    return stamp


def dispatch_decision(now, runs):
    """No API or timer side effects; a failed attempt has a bounded cooldown."""
    if not isinstance(now,datetime) or now.utcoffset() is None:
        raise ValueError("entry_watchdog_clock_invalid")
    if not isinstance(runs,list):
        raise ValueError("entry_watchdog_runs_invalid")
    local=now.astimezone(JST)
    if not 9<=local.hour<=22:
        return "outside_research_hours"
    eligible=[]
    for run in runs:
        if not isinstance(run,dict):
            raise ValueError("entry_watchdog_run_invalid")
        if run.get("event") not in ("schedule","workflow_dispatch"):
            continue
        if run.get("head_branch")!="main":
            continue
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
        decision=dispatch_decision(now,runs)
        record={"decision":decision,
                "observed_schedule_runs":sum(r.get("event")=="schedule" for r in runs),
                "observed_dispatch_runs":sum(r.get("event")=="workflow_dispatch" for r in runs),
                "trigger_is_schedule":False}
        if decision=="dispatch_missing_research_job":
            dispatch(file)
            record["dispatch_requested"]=True
        else:
            record["dispatch_requested"]=False
        report["targets"][kind]=record
    return report


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
    path=Path("entry-course-evidence/activation-watchdog.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,sort_keys=True,ensure_ascii=False)+"\n",
                    encoding="utf-8")
    print("ENTRY_COURSE_ACTIVATION_WATCHDOG="+json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
