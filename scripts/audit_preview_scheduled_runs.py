"""Read-only GitHub Actions schedule audit. No saved race evidence is inferred from a CI success."""
import json
import os
from datetime import date, datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API="https://api.github.com"
REPO="ikst2512-eng/boat-edge-clean"
WORKFLOW="late-preview-capture.yml"

def collect_schedule_history(fetch_page, target_day, max_pages=20):
    """Read enough actual scheduled runs to cover a full JST day.

    Inspect the preceding JST day as a buffer for a delayed started_at.
    An incomplete/truncated listing never certifies schedule health.
    Fetch errors (including HTTP 403 and 404) propagate as failures.
    """
    if not isinstance(target_day, date) or isinstance(target_day, datetime):
        raise ValueError("invalid_target_day")
    if type(max_pages) is not int or max_pages<1:
        raise ValueError("invalid_page_limit")
    earlier_than=target_day-timedelta(days=1)
    seen=set()
    runs=[]
    expected_total=None
    previous=None
    for page in range(1,max_pages+1):
        data=fetch_page(page)
        if (not isinstance(data,dict)
                or type(data.get("total_count")) is not int
                or data["total_count"]<0
                or not isinstance(data.get("workflow_runs"),list)
                or len(data["workflow_runs"])>100):
            raise ValueError("invalid_schedule_history_page")
        if expected_total is None:
            expected_total=data["total_count"]
        if expected_total!=data["total_count"]:
            raise ValueError("schedule_listing_changed_during_pagination")
        boundary=False
        for run in data["workflow_runs"]:
            if (not isinstance(run,dict) or run.get("event")!="schedule"
                    or type(run.get("id")) is not int or run["id"]<=0
                    or run["id"] in seen):
                raise ValueError("invalid_or_duplicate_schedule_run")
            try:
                created=datetime.fromisoformat(run["created_at"].replace("Z","+00:00"))
            except (KeyError,AttributeError,ValueError,TypeError) as exc:
                raise ValueError("invalid_schedule_creation_clock") from exc
            if created.utcoffset() is None or (previous is not None and created>previous):
                raise ValueError("nonmonotonic_schedule_history")
            previous=created
            seen.add(run["id"])
            runs.append(run)
            if created.astimezone(timezone(timedelta(hours=9))).date()<earlier_than:
                boundary=True
        if len(runs)>expected_total:
            raise ValueError("schedule_history_count_overflow")
        if boundary or len(runs)==expected_total:
            return {
                "workflow_runs":runs,
                "total_count":expected_total,
                "history_pages_read":page,
                "history_rows_inspected":len(runs),
                "full_day_metadata_coverage":True,
            }
        if len(data["workflow_runs"])!=100:
            raise ValueError("truncated_schedule_history_page")
    raise ValueError("schedule_history_pagination_limit")


def audit_target_day(now, scheduled_audit):
    """Choose the JST date of the latest nominal 23:17 nightly audit slot.

    Delayed scheduled runners after JST midnight must audit the *previous*
    completed capture day. GitHub does not expose the exact originating cron
    slot in run timestamps, so this is a conservative nominal-day assignment,
    not proof that the originating slot fired on time.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware audit clock required")
    local=now.astimezone(timezone(timedelta(hours=9)))
    if scheduled_audit and (local.hour,local.minute)<(23,17):
        return local.date()-timedelta(days=1)
    return local.date()


def capture_window_health(runs, today, scheduled_audit):
    """Classify actual schedule-run starts, without certifying race data or T-12."""
    jst=timezone(timedelta(hours=9))
    in_window, outside, unknown=[], [], []
    in_window_success, in_window_failed, in_window_pending=[], [], []

    def aware(value):
        if not isinstance(value, str):
            return None
        try:
            stamp=datetime.fromisoformat(value.replace("Z", "+00:00"))
            return stamp if stamp.utcoffset() is not None else None
        except ValueError:
            return None

    for run in runs:
        if run.get("event")!="schedule":
            continue
        run_id=run.get("id")
        if type(run_id) is not int or run_id<=0:
            continue
        started=aware(run.get("run_started_at"))
        created=aware(run.get("created_at"))
        cohort=started or created
        if cohort is None or cohort.astimezone(jst).date()!=today:
            continue
        if started is None or created is None or started<created:
            unknown.append(run_id)
            continue
        local=started.astimezone(jst)
        if (8, 3)<=(local.hour, local.minute)<=(21, 58):
            in_window.append(run_id)
            if run.get("status")=="completed" and run.get("conclusion")=="success":
                in_window_success.append(run_id)
            elif run.get("status")=="completed" and run.get("conclusion") not in (None,"success"):
                in_window_failed.append(run_id)
            else:
                in_window_pending.append(run_id)
        else:
            outside.append(run_id)

    return {
        "nominal_capture_window_jst": "08:03-21:58",
        "today_in_nominal_window_run_ids": sorted(in_window),
        "today_outside_nominal_window_run_ids": sorted(outside),
        "today_unknown_start_run_ids": sorted(unknown),
        "today_in_window_successful_run_ids": sorted(in_window_success),
        "today_in_window_failed_run_ids": sorted(in_window_failed),
        "today_in_window_pending_or_unknown_run_ids": sorted(in_window_pending),
        "no_in_window_capture_start_today": bool(scheduled_audit and not in_window),
        "no_successful_in_window_capture_today": bool(scheduled_audit and in_window and not in_window_success),
        "window_check_is_t12_evidence": False,
    }

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

def main():
    token=os.environ.get("GITHUB_TOKEN")
    if not token:raise SystemExit("GITHUB_TOKEN required")
    scheduled_audit=os.environ.get("GITHUB_EVENT_NAME")=="schedule"
    target_day=audit_target_day(datetime.now(timezone.utc),scheduled_audit)
    def fetch_page(page):
        url=(f"{API}/repos/{REPO}/actions/workflows/{WORKFLOW}/runs"
             f"?event=schedule&per_page=100&page={page}")
        req=Request(url,headers={"Accept":"application/vnd.github+json",
                                 "Authorization":"Bearer "+token,
                                 "User-Agent":"BOAT-EDGE-CLEAN-AUDIT"})
        with urlopen(req,timeout=15) as resp:
            return json.load(resp)
    data=collect_schedule_history(fetch_page,target_day)
    report=summarize(data["workflow_runs"])
    report["history_pages_read"]=data["history_pages_read"]
    report["history_rows_inspected"]=data["history_rows_inspected"]
    report["full_day_metadata_coverage"]=data["full_day_metadata_coverage"]
    with urlopen(Request(f"{API}/repos/{REPO}/actions/workflows/{WORKFLOW}",headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+token,"User-Agent":"BOAT-EDGE-CLEAN-AUDIT"}),timeout=15) as response:
        workflow=json.load(response)
    report["workflow_state"]=workflow.get("state")
    report["workflow_path"]=workflow.get("path")
    report["total_scheduled_runs_reported"]=data.get("total_count")
    # Scheduled nightly audit must not succeed silently when no capture schedule
    # actually ran today. Manual/PR audits remain diagnostic-only.
    report["audited_day_jst"]=target_day.isoformat()
    report["audited_day_is_nominal_slot_inference"]=scheduled_audit
    report.update(daily_capture_health(data["workflow_runs"],target_day,scheduled_audit))
    report.update(capture_window_health(data["workflow_runs"],target_day,scheduled_audit))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    path=os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path,"a") as file:
            file.write("## Scheduled capture run audit\n")
            file.write(f"Scheduled runs reported: {report['total_scheduled_runs_reported']}; inspected {report['history_rows_inspected']} across {report['history_pages_read']} page(s), full-day covered: {report['full_day_metadata_coverage']}; success: {report['success']}; failed: {report['failed']}; pending: {report['pending']}\n")
            file.write(f"Last 24h scheduled runs: {report['scheduled_last_24h']} ({report['schedule_health']}).\n")
            file.write(f"Audited JST day: {report['audited_day_jst']} (nominal-slot inference: {report['audited_day_is_nominal_slot_inference']}); scheduled runs: {report['today_scheduled_runs']}; missing: {report['schedule_missing_today']}; all failed: {report['all_today_captures_failed']}; workflow: {report['workflow_state']}.\n")
            file.write(f"Nominal JST window: {report['nominal_capture_window_jst']}; in-window IDs: {report['today_in_nominal_window_run_ids']}; in-window successful: {report['today_in_window_successful_run_ids']}; in-window failed: {report['today_in_window_failed_run_ids']}; in-window pending/unknown: {report['today_in_window_pending_or_unknown_run_ids']}; outside-window IDs: {report['today_outside_nominal_window_run_ids']}; unknown-start IDs: {report['today_unknown_start_run_ids']}. Run metadata only; not T-12 evidence.\n")
            file.write("**Saved six-lane race pairs cannot be derived from run status.** Inspect evidence artifacts separately.\n")
    if report["schedule_missing_today"]:
        raise SystemExit("NO_SCHEDULED_PREVIEW_CAPTURE_TODAY: nightly audit fails closed")
    if report["no_in_window_capture_start_today"]:
        raise SystemExit("NO_IN_WINDOW_SCHEDULED_PREVIEW_CAPTURE_TODAY")
    if report["no_successful_in_window_capture_today"]:
        raise SystemExit("NO_SUCCESSFUL_IN_WINDOW_SCHEDULED_PREVIEW_CAPTURE_TODAY")
    if report["all_today_captures_failed"]:
        raise SystemExit("ALL_TODAY_SCHEDULED_PREVIEW_CAPTURES_FAILED")

if __name__=="__main__":
    main()
