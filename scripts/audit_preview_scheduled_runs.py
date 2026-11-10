"""Read-only GitHub Actions schedule audit. No saved race evidence is inferred from a CI success."""
import json
import os
from datetime import datetime, timedelta, timezone, date
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API="https://api.github.com"
REPO="ikst2512-eng/boat-edge-clean"
WORKFLOW="late-preview-capture.yml"

def summarize(runs, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    scheduled=[r for r in runs if r.get("event")=="schedule"]
    def is_recent(run):
        try:
            instant=datetime.fromisoformat(run["created_at"].replace("Z","+00:00"))
            return cutoff <= instant <= now
        except (KeyError, AttributeError, TypeError, ValueError):
            return False
    recent=[r for r in scheduled if is_recent(r)]
    recent_success=sum(r.get("status")=="completed" and r.get("conclusion")=="success" for r in recent)
    recent_failed=sum(r.get("status")=="completed" and r.get("conclusion")=="failure" for r in recent)
    return {"scheduled_last_24h":len(recent),
            "successful_scheduled_last_24h":recent_success,
            "failed_scheduled_last_24h":recent_failed,
            "schedule_health":"recent_scheduled_run_observed" if recent else "no_scheduled_run_in_last_24h","scheduled_runs":len(scheduled),
            "success":sum(r.get("conclusion")=="success" for r in scheduled),
            "failed":sum(r.get("conclusion")=="failure" for r in scheduled),
            "pending":sum(r.get("status")!="completed" for r in scheduled),
            "latest_scheduled":scheduled[0].get("created_at") if scheduled else None,
            "saved_six_lane_pairs":"not_computable_from_run_status",
            "note":"Successful workflow means job passed, not that any race was saved."}

def daily_capture_health(runs, today, scheduled_audit):
    """Return nightly fail-closed conditions, excluding manual and PR runs."""
    jst=timezone(timedelta(hours=9))
    today_runs=[]
    for run in runs:
        if run.get("event")!="schedule" or not run.get("created_at"):
            continue
        try:
            received=datetime.fromisoformat(run["created_at"].replace("Z","+00:00"))
            if received.tzinfo is not None and received.astimezone(jst).date()==today:
                today_runs.append(run)
        except (TypeError, AttributeError, ValueError):
            continue
    return {"today_scheduled_runs":len(today_runs),
            "schedule_missing_today":bool(scheduled_audit and not today_runs),
            "all_today_captures_failed":bool(scheduled_audit and today_runs and
                all(run.get("status")=="completed" and run.get("conclusion")=="failure" for run in today_runs))}


RESEARCH_WORKFLOW="research-live-preview-evidence.yml"
JST=timezone(timedelta(hours=9))
# The source has one configured tick every five minutes, 09:00--21:55 JST.
RESEARCH_PLANNED_DAILY_SLOTS=13*12


def research_day_health(scheduled, dispatched, *, day, observed_at):
    """Classify the source Cron independently from manual/watchdog dispatches.

    Workflow runs certify neither source receipts nor immutable forecast writes.
    """
    if not isinstance(day,date) or not isinstance(observed_at,datetime) or observed_at.utcoffset() is None:
        raise ValueError("research_capture_health_invalid_clock")
    if not isinstance(scheduled,list) or not isinstance(dispatched,list):
        raise ValueError("research_capture_health_invalid_runs")
    start=datetime.combine(day,datetime.min.time(),tzinfo=JST)
    end=start+timedelta(days=1)
    now=observed_at.astimezone(JST)
    planned=sum(1 for hour in range(9,22) for minute in range(0,60,5)
                if start+timedelta(hours=hour,minutes=minute)<=now)
    seen=set()
    observed={"schedule":0,"workflow_dispatch":0}
    last={"schedule":None,"workflow_dispatch":None}
    for expected,rows in (("schedule",scheduled),("workflow_dispatch",dispatched)):
        for row in rows:
            if not isinstance(row,dict) or row.get("event")!=expected:
                raise ValueError("research_capture_health_invalid_run_type")
            run_id=row.get("id")
            if type(run_id) is not int or run_id<=0 or run_id in seen:
                raise ValueError("research_capture_health_invalid_or_duplicate_id")
            seen.add(run_id)
            raw=row.get("created_at")
            try:
                when=datetime.fromisoformat(raw.replace("Z","+00:00"))
            except (TypeError,ValueError,AttributeError) as exc:
                raise ValueError("research_capture_health_invalid_timestamp") from exc
            if when.utcoffset() is None:
                raise ValueError("research_capture_health_naive_timestamp")
            when=when.astimezone(JST)
            if not start<=when<end or when>now+timedelta(seconds=30):
                raise ValueError("research_capture_health_out_of_day")
            if row.get("head_branch")!="main":
                continue
            observed[expected]+=1
            stamp=when.isoformat()
            if last[expected] is None or stamp>last[expected]:
                last[expected]=stamp
    count=observed["schedule"]
    status=("no_planned_ticks_yet" if planned==0 else
            "no_cron_run_observed" if count==0 else
            "severely_sparse_cron_observation" if count*2<planned else
            "cron_runs_observed_not_source_verified")
    return {"date_jst":day.strftime("%Y%m%d"),
            "source_workflow":RESEARCH_WORKFLOW,
            "expected_five_minute_slots_due":planned,
            "observed_schedule_runs":count,
            "observed_workflow_dispatch_runs":observed["workflow_dispatch"],
            "missing_schedule_runs_vs_configured_slots_lower_bound":max(0,planned-count),
            "last_scheduled_run_jst":last["schedule"],
            "last_dispatch_run_jst":last["workflow_dispatch"],
            "cron_health":status,
            "dispatch_attribution":"manual_or_watchdog_not_distinguishable_from_run_event",
            "saved_races":"unverified_from_run_status",
            "t12_certification":"unverified_from_run_status"}


def _source_run_inventory(token, workflow, event, *, day):
    """Get every one-day event inventory page; never silently truncate at 100."""
    start=datetime.combine(day,datetime.min.time(),tzinfo=JST)
    end=start+timedelta(days=1)-timedelta(seconds=1)
    range_query=start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")+".."+end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows=[]
    for page in range(1,11):
        query=urlencode({"event":event,"created":range_query,"per_page":100,"page":page})
        url=f"{API}/repos/{REPO}/actions/workflows/{workflow}/runs?{query}"
        req=Request(url,headers={"Accept":"application/vnd.github+json",
                    "Authorization":"Bearer "+token,"User-Agent":"BOAT-EDGE-CLEAN-AUDIT"})
        with urlopen(req,timeout=15) as response:
            payload=json.load(response)
        chunk=payload.get("workflow_runs") if isinstance(payload,dict) else None
        if (not isinstance(chunk,list) or len(chunk)>100 or
                type(payload.get("total_count")) is not int):
            raise ValueError("research_capture_health_invalid_inventory")
        rows.extend(chunk)
        if len(chunk)<100:
            if len(rows)!=payload["total_count"]:
                raise ValueError("research_capture_health_inventory_count_mismatch")
            return rows
    raise ValueError("research_capture_health_incomplete_inventory")


def main():
    token=os.environ.get("GITHUB_TOKEN")
    if not token:raise SystemExit("GITHUB_TOKEN required")
    url=f"{API}/repos/{REPO}/actions/workflows/{WORKFLOW}/runs?event=schedule&per_page=100"
    req=Request(url,headers={"Accept":"application/vnd.github+json",
                             "Authorization":"Bearer "+token,
                             "User-Agent":"BOAT-EDGE-CLEAN-AUDIT"})
    with urlopen(req,timeout=15) as resp:
        data=json.load(resp)
    report=summarize(data["workflow_runs"])
    with urlopen(Request(f"{API}/repos/{REPO}/actions/workflows/{WORKFLOW}",headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+token,"User-Agent":"BOAT-EDGE-CLEAN-AUDIT"}),timeout=15) as response:
        workflow=json.load(response)
    report["workflow_state"]=workflow.get("state")
    report["workflow_path"]=workflow.get("path")
    report["total_scheduled_runs_reported"]=data.get("total_count")
    # Scheduled nightly audit must not succeed silently when no capture schedule
    # actually ran today. Manual/PR audits remain diagnostic-only.
    report.update(daily_capture_health(data["workflow_runs"],datetime.now(timezone(timedelta(hours=9))).date(),
                                      os.environ.get("GITHUB_EVENT_NAME")=="schedule"))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    day=datetime.now(JST).date()
    research=research_day_health(
        _source_run_inventory(token,RESEARCH_WORKFLOW,"schedule",day=day),
        _source_run_inventory(token,RESEARCH_WORKFLOW,"workflow_dispatch",day=day),
        day=day,observed_at=datetime.now(timezone.utc))
    print("RESEARCH_SOURCE_CRON_AND_DISPATCH_AUDIT="+json.dumps(research,ensure_ascii=False,sort_keys=True))
    path=os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path,"a") as file:
            file.write("## Scheduled capture run audit\n")
            file.write(f"Scheduled runs reported: {report['total_scheduled_runs_reported']}; last 100: {report['scheduled_runs']}; success: {report['success']}; failed: {report['failed']}; pending: {report['pending']}\n")
            file.write(f"Last 24h scheduled runs: {report['scheduled_last_24h']} ({report['schedule_health']}).\n")
            file.write(f"Today JST scheduled: {report['today_scheduled_runs']}; missing: {report['schedule_missing_today']}; all failed: {report['all_today_captures_failed']}; workflow: {report['workflow_state']}.\n")
            file.write("**Saved six-lane race pairs cannot be derived from run status.** Inspect evidence artifacts separately.\n")
            file.write(f"Research 5-min Cron: {research['observed_schedule_runs']}/{research['expected_five_minute_slots_due']} due slots; workflow_dispatch (manual/watchdog mixed): {research['observed_workflow_dispatch_runs']}; status: {research['cron_health']}.\n")
            file.write("Research Cron attempts, rescue dispatches, source capture and T-12 certified original writes are different metrics.\n")
    if report["schedule_missing_today"]:
        raise SystemExit("NO_SCHEDULED_PREVIEW_CAPTURE_TODAY: nightly audit fails closed")
    if report["all_today_captures_failed"]:
        raise SystemExit("ALL_TODAY_SCHEDULED_PREVIEW_CAPTURES_FAILED")
    # This is an *observation* alarm, not a claim GitHub is obliged to
    # execute each minute-accurate Cron tick; dispatches cannot mask a gap.
    if os.environ.get("GITHUB_EVENT_NAME")=="schedule" and (
            research["expected_five_minute_slots_due"]>=24 and
            research["cron_health"] in ("no_cron_run_observed","severely_sparse_cron_observation")):
        raise SystemExit("RESEARCH_PREVIEW_CRON_SEVERELY_SPARSE")

if __name__=="__main__":
    main()
