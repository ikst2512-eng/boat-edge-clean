"""Read-only GitHub Actions schedule audit. No saved race evidence is inferred from a CI success."""
import json
import os
from datetime import datetime, timedelta, timezone
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
    return {"scheduled_last_24h":len(recent),
            "schedule_health":"recent_scheduled_run_observed" if recent else "no_scheduled_run_in_last_24h","scheduled_runs":len(scheduled),
            "success":sum(r.get("conclusion")=="success" for r in scheduled),
            "failed":sum(r.get("conclusion")=="failure" for r in scheduled),
            "pending":sum(r.get("status")!="completed" for r in scheduled),
            "latest_scheduled":scheduled[0].get("created_at") if scheduled else None,
            "saved_six_lane_pairs":"not_computable_from_run_status",
            "note":"Successful workflow means job passed, not that any race was saved."}

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
    jst=timezone(timedelta(hours=9))
    today=datetime.now(jst).date()
    today_runs=[run for run in data["workflow_runs"]
                if run.get("event")=="schedule" and run.get("created_at")
                and datetime.fromisoformat(run["created_at"].replace("Z","+00:00")).astimezone(jst).date()==today]
    report["today_scheduled_runs"]=len(today_runs)
    report["schedule_missing_today"]=(os.environ.get("GITHUB_EVENT_NAME")=="schedule" and not today_runs)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    path=os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path,"a") as file:
            file.write("## Scheduled capture run audit\n")
            file.write(f"Scheduled runs reported: {report['total_scheduled_runs_reported']}; last 100: {report['scheduled_runs']}; success: {report['success']}; failed: {report['failed']}; pending: {report['pending']}\n")
            file.write(f"Last 24h scheduled runs: {report['scheduled_last_24h']} ({report['schedule_health']}).\n")
            file.write("**Saved six-lane race pairs cannot be derived from run status.** Inspect evidence artifacts separately.\n")
    if report["schedule_missing_today"]:
        raise SystemExit("NO_SCHEDULED_PREVIEW_CAPTURE_TODAY: nightly audit fails closed")

if __name__=="__main__":
    main()
