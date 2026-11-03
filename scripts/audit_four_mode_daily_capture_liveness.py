"""Read-only daily liveness audit of V2 capture workflow run metadata.

A successfully completed capture run does not establish archive publication or
predeadline source provenance. Missing capture execution is a separate failure
from missing forecast files.
"""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
CAPTURE = "four-mode-prospective-capture.yml"
EVENTS = {"schedule", "workflow_dispatch"}


def report(day, inventory):
    if not isinstance(day, str) or len(day) != 8 or not day.isdecimal():
        raise ValueError("invalid JST day")
    try:
        datetime.strptime(day, "%Y%m%d")
    except ValueError as exc:
        raise ValueError("invalid JST day") from exc
    if not isinstance(inventory, dict) or not isinstance(inventory.get("recent_capture_runs"), list):
        raise ValueError("invalid capture inventory")
    selected = []
    for run in inventory["recent_capture_runs"]:
        if not isinstance(run, dict) or run.get("workflow") != CAPTURE or run.get("event") not in EVENTS:
            raise ValueError("unexpected capture run")
        run_id = run.get("id")
        stamp = run.get("created_at")
        if type(run_id) is not int or run_id <= 0 or not isinstance(stamp, str):
            raise ValueError("invalid run metadata")
        try:
            instant = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid capture timestamp") from exc
        if instant.tzinfo is None:
            raise ValueError("capture timestamp has no timezone")
        if instant.astimezone(JST).strftime("%Y%m%d") == day:
            selected.append(run)
    status = (
        "no_capture_runs_observed" if not selected
        else "capture_success_observed" if any(x.get("conclusion") == "success" and x.get("status") == "completed" for x in selected)
        else "capture_pending" if any(x.get("status") != "completed" for x in selected)
        else "all_observed_captures_failed"
    )
    return {
        "schema": "FOUR_MODE_DAILY_CAPTURE_LIVENESS_V1",
        "day_jst": day,
        "status": status,
        "same_day_run_ids": [r["id"] for r in selected],
        "completed_success_count": sum(r.get("status") == "completed" and r.get("conclusion") == "success" for r in selected),
        "completed_failure_count": sum(r.get("status") == "completed" and r.get("conclusion") == "failure" for r in selected),
        "pending_count": sum(r.get("status") != "completed" for r in selected),
        "publication_verified": False,
        "predeadline_source_verified": False,
        "note": "Workflow run presence or success alone does not prove Git archive publication.",
    }


def should_fail(result, event, ref):
    return (event == "schedule" and ref == "refs/heads/main"
            and result.get("status") in ("no_capture_runs_observed", "all_observed_captures_failed",
                                        "capture_inventory_unavailable"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--day-jst", default=None)
    args = parser.parse_args()
    day = args.day_jst or datetime.now(JST).strftime("%Y%m%d")
    try:
        evidence = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
        result = report(day, evidence)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        result = {
            "schema": "FOUR_MODE_DAILY_CAPTURE_LIVENESS_V1",
            "day_jst": day,
            "status": "capture_inventory_unavailable",
            "error_type": type(exc).__name__,
            "same_day_run_ids": [],
            "completed_success_count": 0,
            "completed_failure_count": 0,
            "pending_count": 0,
            "publication_verified": False,
            "predeadline_source_verified": False,
            "note": "Capture run inventory could not be verified; counts are unknown, not zero.",
        }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("FOUR_MODE_DAILY_CAPTURE_LIVENESS=" + json.dumps(result, sort_keys=True))
    if should_fail(result, os.getenv("GITHUB_EVENT_NAME"), os.getenv("GITHUB_REF")):
        print("::error::Daily V2 capture execution is absent or all observed runs failed")
        raise SystemExit(2)
    if result["status"] == "capture_pending":
        print("::warning::Daily V2 capture is pending; publication not yet proven")


if __name__ == "__main__":
    main()
