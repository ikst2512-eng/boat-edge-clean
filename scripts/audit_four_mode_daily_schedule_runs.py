"""Day-wide GitHub Actions scheduled-capture metadata audit (read-only).

The detailed artifact inspector deliberately checks only a recent subset.
This independent inventory uses one 100-run API page to detect earlier
scheduled job failures. It does NOT establish forecast publication, early
receipt, or the contents of any skipped artifacts.
"""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

JST = timezone(timedelta(hours=9))
WORKFLOW = "four-mode-prospective-capture.yml"
PAGE_LIMIT = 100


def audit_day(repo, day, token, fetch=None):
    if (not isinstance(repo, str) or len(repo.split("/")) != 2
            or not all(repo.split("/")) or not token
            or not isinstance(day, str) or len(day) != 8 or not day.isdigit()):
        raise ValueError("invalid_audit_arguments")
    datetime.strptime(day, "%Y%m%d")
    url = (f"https://api.github.com/repos/{repo}/actions/workflows/"
           f"{quote(WORKFLOW)}/runs?event=schedule&per_page={PAGE_LIMIT}")
    if fetch is None:
        def fetch(location):
            request = Request(location, headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "User-Agent": "boat-edge-scheduled-full-day-audit"})
            with urlopen(request, timeout=20) as response:
                return json.load(response)
    result = fetch(url)
    if (not isinstance(result, dict)
            or not isinstance(result.get("workflow_runs"), list)
            or type(result.get("total_count")) is not int
            or result["total_count"] < len(result["workflow_runs"])
            or len(result["workflow_runs"]) > PAGE_LIMIT):
        raise ValueError("invalid_workflow_run_listing")
    seen = set()
    rows = []
    previous = None
    for entry in result["workflow_runs"]:
        if (not isinstance(entry, dict) or entry.get("event") != "schedule"
                or type(entry.get("id")) is not int or entry["id"] <= 0
                or entry["id"] in seen):
            raise ValueError("invalid_schedule_run")
        seen.add(entry["id"])
        try:
            created = datetime.fromisoformat(
                entry["created_at"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, TypeError, ValueError) as exc:
            raise ValueError("invalid_schedule_run_timestamp") from exc
        if created.utcoffset() is None or (previous is not None and created > previous):
            raise ValueError("unsorted_or_naive_schedule_run_timestamp")
        previous = created
        rows.append({
            "run_id": entry["id"], "day_jst": created.astimezone(JST).strftime("%Y%m%d"),
            "status": entry.get("status"), "conclusion": entry.get("conclusion")})
    matching = [row for row in rows if row["day_jst"] == day]
    # When a full page is all from this day, older scheduled runs may have
    # been truncated. A previous-day boundary (or short unpaginated listing)
    # is needed to certify full same-day metadata coverage.
    complete = (result["total_count"] == len(rows)
                or any(row["day_jst"] < day for row in rows))
    failed = sorted(row["run_id"] for row in matching
                    if row["status"] == "completed"
                    and row["conclusion"] not in ("success", None))
    pending = sorted(row["run_id"] for row in matching
                     if row["status"] != "completed"
                     or row["conclusion"] is None)
    return {"schema": "FOUR_MODE_DAILY_SCHEDULE_RUN_METADATA_V1",
            "day_jst": day, "total_history_runs_available": result["total_count"],
            "history_rows_inspected": len(rows), "full_day_metadata_coverage": complete,
            "same_day_scheduled_run_count": len(matching),
            "failed_run_ids": failed, "pending_or_unknown_run_ids": pending,
            "forecast_publication_verified": False,
            "per_run_artifact_coverage_verified": False,
            "note": "Workflow execution status only; no claim about artifact completeness."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--day-jst")
    args = parser.parse_args()
    day = args.day_jst or datetime.now(JST).strftime("%Y%m%d")
    result = audit_day(args.repo, day, os.environ.get("GITHUB_TOKEN", ""))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
    print("FOUR_MODE_DAILY_SCHEDULE_METADATA=" + json.dumps(result, sort_keys=True))
    if (os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"):
        if not result["full_day_metadata_coverage"]:
            print("::error::Full JST day scheduled run metadata not covered by API page")
            raise SystemExit(2)
        if result["same_day_scheduled_run_count"] == 0:
            print("::error::No scheduled V2 capture execution recorded for target JST day")
            raise SystemExit(2)
        if result["failed_run_ids"]:
            print("::error::Scheduled V2 captures failed earlier today, outside bounded artifact audit")
            raise SystemExit(2)
        if result["pending_or_unknown_run_ids"]:
            print("::error::Scheduled V2 captures are pending or have no confirmed outcome; day cannot be certified")
            raise SystemExit(2)


if __name__ == "__main__":
    main()
