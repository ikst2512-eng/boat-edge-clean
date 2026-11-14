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
PREVIEW_WATCHDOG_MARK="entry-course-activation-watchdog"
OFFICIAL_PROBE_WORKFLOW="verify-real-beforeinfo.yml"


def dispatch_payload(file):
    """Tag only the optional independent preview rescue, never T12/T2."""
    if file==PREVIEW_WORKFLOW:
        return {"ref":"main","inputs":{"rescue_origin":PREVIEW_WATCHDOG_MARK}}
    if file in TARGETS.values() or file==OFFICIAL_PROBE_WORKFLOW:
        return {"ref":"main"}
    raise ValueError("entry_watchdog_dispatch_target_unknown")


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


def _count_jst_day_runs(runs, now, event):
    """Count only observed main-branch events from the current JST day.

    The legacy observed_* count remains the number of historical API rows
    fetched, not the number of runs that actually started today.
    """
    today=now.astimezone(JST).date()
    return sum(row.get("event")==event and
               row.get("head_branch")=="main" and
               _timestamp(row.get("created_at")).astimezone(JST).date()==today
               for row in runs)


def run_once(*, now, fetch_runs, dispatch):
    if not isinstance(now,datetime) or now.utcoffset() is None:
        raise ValueError("entry_watchdog_clock_invalid")
    report={"schema":"entry-course-unattended-fallback-v1",
            "observed_at":now.isoformat(),"research_only":True,
            "formal":False,"forecast_record":False,
            "unattended_scheduled_capture_verified":False,
            "independent_first_seen_verified":False,
            "targets":{}}
    local_hour=now.astimezone(JST).hour
    for kind,file in TARGETS.items():
        first_hour=8 if kind=="t12" else 9
        if not first_hour<=local_hour<=22:
            # Do not allow an inactive T2 API error to block the critical
            # 08 JST T12 fallback. Zero counts here mean not queried.
            report["targets"][kind]={
                "decision":"outside_research_hours",
                "observed_schedule_runs":0,"observed_dispatch_runs":0,
                "observed_schedule_runs_today":0,"observed_dispatch_runs_today":0,
                "lookup_skipped_outside_hours":True,
                "trigger_is_schedule":False,"dispatch_requested":False}
            continue
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
                "lookup_skipped_outside_hours":False,
                "observed_schedule_runs":sum(r.get("event")=="schedule" for r in runs),
                "observed_dispatch_runs":sum(r.get("event")=="workflow_dispatch" for r in runs),
                "observed_schedule_runs_today":_count_jst_day_runs(runs,now,"schedule"),
                "observed_dispatch_runs_today":_count_jst_day_runs(runs,now,"workflow_dispatch"),
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
            "observed_schedule_runs_today":0,"observed_dispatch_runs_today":0,
            "latest_native_schedule_jst":None,
            "latest_native_schedule_age_minutes":None,
            "native_schedule_observation":"outside_preview_hours",
            "native_schedule_observation_window_minutes":20,
            "schedule_coverage":"last_30_api_rows_per_event_not_exhaustive",
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
    # The per-workflow GitHub API returns the last 30 events of each type,
    # including historic days. "observed_schedule_runs" is NOT today's count.
    # A watchdog dispatch must never masquerade as a native schedule event.
    schedule_today=_count_jst_day_runs(runs,now,"schedule")
    dispatch_today=_count_jst_day_runs(runs,now,"workflow_dispatch")
    native_times=[_timestamp(row["created_at"]).astimezone(JST)
                  for row in runs if row.get("event")=="schedule"
                  and row.get("head_branch")=="main"]
    latest=max(native_times) if native_times else None
    age=max(0,(local-latest).total_seconds()/60) if latest else None
    record.update(decision=decision,
                  observed_schedule_runs=sum(r.get("event")=="schedule" for r in runs),
                  observed_dispatch_runs=sum(r.get("event")=="workflow_dispatch" for r in runs),
                  observed_schedule_runs_today=schedule_today,
                  observed_dispatch_runs_today=dispatch_today,
                  latest_native_schedule_jst=latest.isoformat() if latest else None,
                  latest_native_schedule_age_minutes=round(age,1) if age is not None else None,
                  native_schedule_observation=(
                      "no_native_schedule_observed_today" if not schedule_today else
                      "native_schedule_observed_with_over_20min_gap" if age>20 else
                      "native_schedule_observed_within_20min"))
    if decision=="dispatch_missing_research_job":
        dispatch(PREVIEW_WORKFLOW)
        record["dispatch_requested"]=True
    return record


def official_live_probe_fallback(now, fetch_runs, dispatch):
    """One-daytime-window fallback for the existing 19:35 JST official E2E.

    Dispatch is explicitly NOT a schedule event or evidence of any matched
    real-time official measurements, and cannot certify T-12 first receipt.
    Uses the already-running watchdog only; no new cron or collector.
    """
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("official_probe_watchdog_clock_invalid")
    local=now.astimezone(JST)
    report={"workflow":OFFICIAL_PROBE_WORKFLOW,
            "decision":"outside_official_probe_window",
            "observed_schedule_runs":0,"observed_dispatch_runs":0,
            "dispatch_requested":False,"trigger_is_schedule":False,
            "live_24_values_verified":False,"formal_t12_certified":False}
    # The 19:35 primary Cron gets five minutes to start, and later failures
    # never warrant inventing post-deadline evidence.
    if local.hour!=19 or not 40<=local.minute<60:
        return report
    observed=[]
    for event in ("schedule","workflow_dispatch"):
        rows=fetch_runs(OFFICIAL_PROBE_WORKFLOW,event)
        if not isinstance(rows,list):
            raise ValueError("official_probe_watchdog_runs_invalid")
        for row in rows:
            if not isinstance(row,dict):
                raise ValueError("official_probe_watchdog_run_invalid")
            if row.get("event")!=event or row.get("head_branch")!="main":
                continue
            if row.get("status") not in ("queued","in_progress","waiting",
                                          "pending","requested","completed"):
                raise ValueError("official_probe_watchdog_run_status_invalid")
            at=_timestamp(row.get("created_at")).astimezone(JST)
            if at>local+timedelta(minutes=1):
                raise ValueError("official_probe_watchdog_future_run")
            if at.date()==local.date() and (at.hour>19 or (at.hour==19 and at.minute>=15)):
                observed.append((event,at,row["status"],row.get("conclusion")))
    report["observed_schedule_runs"]=sum(row[0]=="schedule" for row in observed)
    report["observed_dispatch_runs"]=sum(row[0]=="workflow_dispatch" for row in observed)
    report["observed_failed_schedule_runs"]=sum(
        event=="schedule" and status=="completed" and conclusion=="failure"
        for event,_,status,conclusion in observed)
    if observed:
        # One bounded retry when the primary 19:35 verification DEFINITIVELY
        # failed. Unknown/active/successful runs and any prior dispatch suppress
        # duplicates. This never counts a workflow launch as live evidence.
        failed_primary_only=(local.minute>=50 and
            report["observed_failed_schedule_runs"]==1 and len(observed)==1)
        if failed_primary_only:
            dispatch(OFFICIAL_PROBE_WORKFLOW)
            report["dispatch_requested"]=True
            report["decision"]="requested_retry_after_failed_official_probe"
        else:
            report["decision"]="official_probe_started_already"
        return report
    dispatch(OFFICIAL_PROBE_WORKFLOW)
    report["dispatch_requested"]=True
    report["decision"]="requested_missing_official_probe"
    return report



def audit_wakeup_origin(event_name, payload):
    """Describe the GitHub wakeup source; never promote it to source proof.

    An upstream schedule event can wake an existing watchdog, but cannot
    prove the 19:35 official cron ran or that any official fields were read.
    This function has no effect on the dispatcher policy.
    """
    record={"event_name":event_name if isinstance(event_name,str) else "unknown",
            "source_status":"not_workflow_run",
            "reported_parent":None,
            "native_official_schedule_verified":False,
            "official_24_values_verified":False,
            "formal_t12_certified":False}
    if event_name!="workflow_run":
        return record
    record["source_status"]="parent_metadata_unavailable"
    parent=payload.get("workflow_run") if isinstance(payload,dict) else None
    if not isinstance(parent,dict):
        return record
    repo=parent.get("head_repository")
    record["reported_parent"]={
        "name":parent.get("name") if isinstance(parent.get("name"),str) else None,
        "run_id":parent.get("id") if type(parent.get("id")) is int else None,
        "event":parent.get("event") if isinstance(parent.get("event"),str) else None,
        "conclusion":parent.get("conclusion") if isinstance(parent.get("conclusion"),str) else None,
        "created_at":parent.get("created_at") if isinstance(parent.get("created_at"),str) else None,
        "head_branch":parent.get("head_branch") if isinstance(parent.get("head_branch"),str) else None,
        "head_repository":repo.get("full_name") if isinstance(repo,dict)
                          and isinstance(repo.get("full_name"),str) else None}
    record["source_status"]="github_webhook_metadata_observed_not_attestation"
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
              method="POST",fields=dispatch_payload(file))
    report=run_once(now=now,fetch_runs=fetch_runs,dispatch=dispatch)
    # Pure diagnostic from GitHub's delivered webhook. Never affects dispatch.
    # A missing or malformed event payload must not cancel the T12/T2 rescue.
    try:
        event_path=os.environ.get("GITHUB_EVENT_PATH")
        event_payload=json.loads(Path(event_path).read_text(encoding="utf-8")) if event_path else None
        report["wakeup_origin"]=audit_wakeup_origin(
            os.environ.get("GITHUB_EVENT_NAME","unavailable"),event_payload)
    except (OSError,UnicodeError,ValueError,TypeError) as exc:
        report["wakeup_origin"]={
            "event_name":os.environ.get("GITHUB_EVENT_NAME","unavailable"),
            "source_status":"event_payload_unavailable",
            "error_type":type(exc).__name__,
            "reported_parent":None,
            "native_official_schedule_verified":False,
            "official_24_values_verified":False,
            "formal_t12_certified":False}
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
    # Independent fallback: never fail or block T12/T2/preview recovery.
    # Its own API outage is reported explicitly, not construed as a live PASS.
    try:
        report["independent_official_live_probe"]=official_live_probe_fallback(
            now,fetch_runs,dispatch)
    except Exception as exc:
        report["independent_official_live_probe"]={
            "workflow":OFFICIAL_PROBE_WORKFLOW,
            "decision":"unverified_official_probe_fallback_error",
            "error_type":type(exc).__name__,
            "dispatch_requested":False,
            "trigger_is_schedule":False,
            "live_24_values_verified":False,"formal_t12_certified":False}
    path=Path("entry-course-evidence/activation-watchdog.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,sort_keys=True,ensure_ascii=False)+"\n",
                    encoding="utf-8")
    print("ENTRY_COURSE_ACTIVATION_WATCHDOG="+json.dumps(report,sort_keys=True))
    if preview_error is not None:
        raise preview_error


if __name__=="__main__":
    main()
