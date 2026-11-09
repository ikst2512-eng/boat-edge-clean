"""Read-only daily liveness audit of V2 capture workflow run metadata.

A successfully completed capture run does not establish archive publication or
predeadline source provenance. Missing capture execution is a separate failure
from missing forecast files.
"""
import argparse
import json
import os
from datetime import datetime, time, timedelta, timezone
from scripts.audit_four_mode_daily_schedule_runs import (
    NOMINAL_DAILY_CAPTURE_SLOTS, SCHEDULE_OBSERVATION_GRACE,
)
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
    in_window = []
    outside_window_run_ids = {"pre_opening": [], "after_last_slot_grace": []}
    first = datetime.combine(
        datetime.strptime(day, "%Y%m%d").date(), time(7, 7), tzinfo=JST)
    last = (first + timedelta(minutes=15 * (NOMINAL_DAILY_CAPTURE_SLOTS - 1))
            + SCHEDULE_OBSERVATION_GRACE)
    seen_run_ids = set()
    for run in inventory["recent_capture_runs"]:
        if not isinstance(run, dict) or run.get("workflow") != CAPTURE or run.get("event") not in EVENTS:
            raise ValueError("unexpected capture run")
        run_id = run.get("id")
        stamp = run.get("created_at")
        if (type(run_id) is not int or run_id <= 0
                or run_id in seen_run_ids or not isinstance(stamp, str)):
            raise ValueError("invalid or duplicate run metadata")
        seen_run_ids.add(run_id)
        try:
            instant = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid capture timestamp") from exc
        if instant.tzinfo is None:
            raise ValueError("capture timestamp has no timezone")
        local = instant.astimezone(JST)
        if local.strftime("%Y%m%d") == day:
            selected.append(run)
            if local < first:
                outside_window_run_ids["pre_opening"].append(run_id)
            elif local > last:
                outside_window_run_ids["after_last_slot_grace"].append(run_id)
            else:
                in_window.append(run)
    # GitHub can report completed with a null conclusion while the outcome is
    # still unsettled. Count such executions explicitly as unknown, not a
    # confirmed failure or a successful capture.
    completed_unknown = [
        r["id"] for r in selected
        if r.get("status") == "completed" and r.get("conclusion") is None]
    # A full first page is not complete evidence: older same-day runs may
    # be hidden beyond the API page boundary. Do not assert absence/all failure.
    coverage = inventory.get("source_coverage", {})
    if not isinstance(coverage, dict):
        raise ValueError("invalid source coverage")
    for event in EVENTS:
        item = coverage.get(CAPTURE + ":" + event, {})
        if not isinstance(item, dict):
            raise ValueError("invalid capture coverage metadata")
    capture_coverage_incomplete = any(
        coverage.get(CAPTURE + ":" + event, {}).get("may_be_truncated") is True
        for event in EVENTS
    )
    status = (
        "capture_inventory_incomplete"
        if capture_coverage_incomplete and not any(
            x.get("conclusion") == "success" and x.get("status") == "completed"
            for x in selected
        ) else
        "no_capture_runs_observed" if not selected
        else "capture_success_observed" if any(x.get("conclusion") == "success" and x.get("status") == "completed" for x in selected)
        else "capture_pending" if any(x.get("status") != "completed" for x in selected)
        else "capture_outcome_unknown" if completed_unknown
        else "all_observed_captures_failed"
    )
    return {
        "schema": "FOUR_MODE_DAILY_CAPTURE_LIVENESS_V1",
        "day_jst": day,
        "status": status,
        "same_day_run_ids": [r["id"] for r in selected],
        "same_day_in_capture_window_run_ids": [r["id"] for r in in_window],
        "same_day_outside_capture_window_run_ids": outside_window_run_ids,
        "completed_success_in_capture_window_count": sum(
            r.get("status") == "completed" and r.get("conclusion") == "success"
            for r in in_window),
        "capture_window_success_observed": any(
            r.get("status") == "completed" and r.get("conclusion") == "success"
            for r in in_window),
        "per_nominal_slot_capture_delivery_verified": False,
        "capture_coverage_incomplete": capture_coverage_incomplete,
        "completed_success_count": sum(r.get("status") == "completed" and r.get("conclusion") == "success" for r in selected),
        "completed_failure_count": sum(r.get("status") == "completed" and r.get("conclusion") == "failure" for r in selected),
        "pending_count": sum(r.get("status") != "completed" for r in selected),
        "completed_unknown_outcome_count": len(completed_unknown),
        "completed_unknown_outcome_run_ids": completed_unknown,
        "completed_non_success_count": sum(
            r.get("status") == "completed"
            and r.get("conclusion") not in ("success", None) for r in selected),
        "publication_verified": False,
        "predeadline_source_verified": False,
        "note": ("Workflow run presence or success alone does not prove Git "
                 "archive publication. A successful run created outside the "
                 "07:07-20:57 JST capture window is not evidence of in-window "
                 "capture execution or any individual scheduled slot."),
    }


def should_fail(result, event, ref):
    return (event == "schedule" and ref == "refs/heads/main"
            and (result.get("status") in (
                "no_capture_runs_observed", "all_observed_captures_failed",
                "capture_inventory_unavailable", "capture_inventory_incomplete",
                "capture_outcome_unknown")
                or (result.get("status") == "capture_success_observed"
                    and result.get("capture_window_success_observed") is False)))


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
            "same_day_in_capture_window_run_ids": [],
            "same_day_outside_capture_window_run_ids": {
                "pre_opening": [], "after_last_slot_grace": []},
            "completed_success_in_capture_window_count": 0,
            "capture_window_success_observed": False,
            "per_nominal_slot_capture_delivery_verified": False,
            "completed_success_count": 0,
            "completed_failure_count": 0,
            "pending_count": 0,
            "completed_unknown_outcome_count": 0,
            "completed_unknown_outcome_run_ids": [],
            "completed_non_success_count": 0,
            "publication_verified": False,
            "predeadline_source_verified": False,
            "note": "Capture run inventory could not be verified; counts are unknown, not zero.",
        }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("FOUR_MODE_DAILY_CAPTURE_LIVENESS=" + json.dumps(result, sort_keys=True))
    if should_fail(result, os.getenv("GITHUB_EVENT_NAME"), os.getenv("GITHUB_REF")):
        print("::error::Daily V2 capture history is absent, failed, incomplete, "
              "unknown or unavailable; unknown is NOT a confirmed failure")
        raise SystemExit(2)
    if result["status"] == "capture_pending":
        print("::warning::Daily V2 capture is pending; publication not yet proven")


if __name__ == "__main__":
    main()
