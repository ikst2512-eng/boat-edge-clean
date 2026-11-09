"""Read-only evidence of scheduled captures, fallback dispatches, and watchdog runs."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

CAPTURE = "four-mode-prospective-capture.yml"
WATCHDOG = "four-mode-capture-watchdog.yml"


def api_json(url, token):
    req = Request(url, headers={"Authorization": "Bearer " + token,
                                 "Accept": "application/vnd.github+json",
                                 "X-GitHub-Api-Version": "2022-11-28",
                                 "User-Agent": "boat-edge-clean-watchdog-evidence"})
    with urlopen(req, timeout=20) as res:
        return json.load(res)


def check_runs(payload, event):
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise ValueError("invalid workflow run response")
    items = payload["workflow_runs"]
    total = payload.get("total_count")
    if (len(items) > 100 or (total is not None and (
            type(total) is not int or total < len(items)))):
        raise ValueError("invalid workflow run history coverage")
    rows = []
    seen = set()
    for r in items:
        if (not isinstance(r, dict) or r.get("event") != event
                or type(r.get("id")) is not int or r["id"] <= 0
                or r["id"] in seen):
            raise ValueError("unexpected or duplicate workflow run")
        seen.add(r["id"])
        try:
            moment = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, ValueError, TypeError) as exc:
            raise ValueError("invalid run time") from exc
        if moment.utcoffset() is None:
            raise ValueError("timezone required")
        # GitHub cannot certify a run concluded successfully before it
        # completed. Treat contradictory status/conclusion as corrupt
        # evidence, not a positive capture.
        if r.get("status") != "completed" and r.get("conclusion") is not None:
            raise ValueError("noncompleted_run_has_conclusion")
        rows.append({"id": r["id"], "event": event, "created_at": moment.isoformat(),
                     "status": r.get("status"), "conclusion": r.get("conclusion"),
                     "html_url": r.get("html_url")})
    return rows


def inventory(repo, token, fetch=api_json, now=None):
    if not repo or repo.count("/") != 1 or not token:
        raise ValueError("invalid arguments")
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise ValueError("timezone required")
    all_rows = []
    coverage = {}
    global_seen_ids = set()
    for workflow, events in ((CAPTURE, ("schedule", "workflow_dispatch")),
                             (WATCHDOG, ("schedule", "push"))):
        for event in events:
            url = (f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}"
                   f"/runs?event={event}&per_page=100")
            payload = fetch(url, token)
            rows = check_runs(payload, event)
            total = payload.get("total_count")
            coverage[workflow + ":" + event] = {
                "returned": len(rows), "first_page_only": True,
                "total_count_reported": total,
                "may_be_truncated": (
                    len(rows) == 100 or
                    (type(total) is int and total > len(rows)))}
            for r in rows:
                if r["id"] in global_seen_ids:
                    raise ValueError("same_run_id_in_multiple_event_listings")
                global_seen_ids.add(r["id"])
                r["workflow"] = workflow
            all_rows.extend(rows)
    all_rows.sort(key=lambda r: r["created_at"], reverse=True)
    captures = [r for r in all_rows if r["workflow"] == CAPTURE]
    watchdogs = [r for r in all_rows if r["workflow"] == WATCHDOG]
    latest_capture = captures[0] if captures else None
    gap = None
    if latest_capture is not None:
        stamp = datetime.fromisoformat(latest_capture["created_at"])
        gap = max(0, round((now - stamp).total_seconds() / 60, 1))
    def count(rows, event):
        selected = [r for r in rows if r["event"] == event]
        return {"returned": len(selected),
                "success": sum(
                    r["status"] == "completed" and r["conclusion"] == "success"
                    for r in selected),
                "failed": sum(
                    r["status"] == "completed" and r["conclusion"] == "failure"
                    for r in selected),
                "pending": sum(r["status"] != "completed" for r in selected),
                "completed_unknown_outcome": sum(
                    r["status"] == "completed" and r["conclusion"] is None
                    for r in selected),
                "completed_other_non_success": sum(
                    r["status"] == "completed"
                    and r["conclusion"] not in ("success", "failure", None)
                    for r in selected)}
    return {"schema": "FOUR_MODE_WATCHDOG_DISPATCH_COVERAGE_V1",
            "as_of_utc": now.isoformat(),
            "capture_schedule": count(captures, "schedule"),
            "capture_workflow_dispatch": count(captures, "workflow_dispatch"),
            "watchdog_schedule": count(watchdogs, "schedule"),
            "watchdog_push": count(watchdogs, "push"),
            "latest_capture": latest_capture, "minutes_since_latest_capture": gap,
            "latest_watchdog": watchdogs[0] if watchdogs else None,
            "source_coverage": coverage,
            "dispatch_accepted_proven": False,
            "forecast_saved_proven": False,
            "note": ("Run listings are bounded first-page metadata only. "
                     "Pending, completed with no conclusion, and other "
                     "non-success outcomes are separate. A successful job "
                     "does not prove dispatch cause, main publication, or "
                     "individual Cron slot delivery."),
            "recent_capture_runs": captures,
            "recent_watchdog_runs": watchdogs[:40]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    data = inventory(args.repo, os.environ.get("GITHUB_TOKEN"))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("FOUR_MODE_WATCHDOG_DISPATCH_COVERAGE=" + json.dumps({
        "as_of_utc": data["as_of_utc"],
        "capture_schedule": data["capture_schedule"],
        "capture_workflow_dispatch": data["capture_workflow_dispatch"],
        "watchdog_schedule": data["watchdog_schedule"],
        "watchdog_push": data["watchdog_push"],
        "latest_capture": data["latest_capture"],
        "recent_capture_runs": data["recent_capture_runs"][:10],
        "minutes_since_latest_capture": data["minutes_since_latest_capture"]}, sort_keys=True))


if __name__ == "__main__":
    main()
