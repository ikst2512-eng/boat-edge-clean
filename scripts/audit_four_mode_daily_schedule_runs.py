"""Day-wide GitHub Actions scheduled-capture metadata audit (read-only).

The detailed artifact inspector deliberately checks only a recent subset.
This independent inventory uses one 100-run API page to detect earlier
scheduled job failures. It does NOT establish forecast publication, early
receipt, or the contents of any skipped artifacts.
"""
import argparse
import json
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

JST = timezone(timedelta(hours=9))
WORKFLOW = "four-mode-prospective-capture.yml"
PAGE_LIMIT = 100


# The main capture workflow currently declares four slots per hour, 07:07
# through 20:52 JST. GitHub Actions created_at may be delayed, and its run
# listing does not identify which cron occurrence created an individual run.
NOMINAL_DAILY_CAPTURE_SLOTS = 56
SCHEDULE_OBSERVATION_GRACE = timedelta(minutes=5)


def nominal_schedule_slots_due(day, as_of):
    """Count scheduled slots nominally due, not certified delivered or missed."""
    date = datetime.strptime(day, "%Y%m%d").date()
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("aware audit as_of required")
    local = as_of.astimezone(JST)
    first = datetime.combine(date, time(7, 7), tzinfo=JST)
    return sum(
        first + i * timedelta(minutes=15) + SCHEDULE_OBSERVATION_GRACE <= local
        for i in range(NOMINAL_DAILY_CAPTURE_SLOTS)
    )


def audit_day(repo, day, token, fetch=None, *, as_of=None):
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
    # Default to a post-fetch observation time: a genuine GitHub run can start
    # while the HTTP request is in flight. Do not mark that run future-dated
    # merely because the query began before it appeared in the response.
    as_of = as_of if as_of is not None else datetime.now(timezone.utc)
    due_slots = nominal_schedule_slots_due(day, as_of)
    audit_as_of_jst = as_of.astimezone(JST)
    # API-page completeness is about observed metadata at the audit instant,
    # not proof that a still-running calendar day has finished.
    calendar_day_elapsed = audit_as_of_jst.strftime("%Y%m%d") > day
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
        # A schedule run from the future is not an observed run. Refuse the
        # entire inconsistent API page rather than counting it toward liveness
        # or silently clipping its timestamp.
        if created > as_of:
            raise ValueError("future_schedule_run_timestamp")
        previous = created
        rows.append({
            "run_id": entry["id"], "day_jst": created.astimezone(JST).strftime("%Y%m%d"),
            "created_at_jst": created.astimezone(JST),
            "status": entry.get("status"), "conclusion": entry.get("conclusion")})
    matching = [row for row in rows if row["day_jst"] == day]
    # A run created before the day's first 07:07 JST trigger cannot be
    # attributed to one of today's scheduled capture slots. GitHub can deliver
    # the previous evening's Cron after midnight; retain the raw count but
    # never use these early runs to satisfy the day's execution presence gate.
    first_nominal_jst = datetime.combine(
        datetime.strptime(day, "%Y%m%d").date(), time(7, 7), tzinfo=JST)
    pre_first_nominal_run_ids = sorted(
        row["run_id"] for row in matching
        if row["created_at_jst"] < first_nominal_jst)
    after_first_nominal_count = len(matching) - len(pre_first_nominal_run_ids)
    # A run created long after the final 20:52 JST slot is still a real
    # GitHub execution, but cannot demonstrate that the day's capture window
    # was served. Keep it visible instead of silently granting liveness.
    last_nominal_with_grace_jst = (
        first_nominal_jst
        + (NOMINAL_DAILY_CAPTURE_SLOTS - 1) * timedelta(minutes=15)
        + SCHEDULE_OBSERVATION_GRACE
    )
    after_final_window_run_ids = sorted(
        row["run_id"] for row in matching
        if row["created_at_jst"] > last_nominal_with_grace_jst)
    within_window_count = (
        after_first_nominal_count - len(after_final_window_run_ids))
    # Staleness is a read-only observation diagnostic, not missed-Cron proof.
    # Clamp the observation endpoint to the last nominal slot plus grace:
    # tomorrow's report must not accumulate overnight silence after captures
    # are no longer scheduled. An empty in-window history is unknown, never
    # represented as zero minutes.
    in_window_rows = [
        row for row in matching
        if first_nominal_jst <= row["created_at_jst"] <= last_nominal_with_grace_jst]
    latest_in_window = max(
        (row["created_at_jst"] for row in in_window_rows), default=None)
    observation_end = min(audit_as_of_jst, last_nominal_with_grace_jst)
    observation_silence_minutes = (
        round((observation_end - latest_in_window).total_seconds() / 60, 2)
        if latest_in_window is not None else None)
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
    in_window_success_run_ids = sorted(
        row["run_id"] for row in in_window_rows
        if row["status"] == "completed" and row["conclusion"] == "success")
    # This is an *observation-count* ratio, NOT a percentage of proven Cron
    # deliveries: the Actions API does not identify the nominal cron slot.
    # A repeated/delayed run can inflate the numerator, so do not cap at 100.
    observed_ratio = (
        round(100 * within_window_count / due_slots, 2)
        if due_slots > 0 else None)
    if due_slots == 0:
        observation_state = "no_nominal_slots_due"
    elif not complete:
        observation_state = "api_coverage_unverified"
    elif within_window_count == 0:
        observation_state = "no_in_window_schedule_observation"
    elif due_slots >= 12 and within_window_count * 4 < due_slots:
        # Read-only 25% triage marker after at least ~3 hours nominally due;
        # never assert which individual Cron slots failed delivery.
        observation_state = "severely_below_nominal_observation"
    elif within_window_count < due_slots:
        observation_state = "below_nominal_observation"
    else:
        observation_state = "nominal_count_met_not_slot_proof"
    return {"schema": "FOUR_MODE_DAILY_SCHEDULE_RUN_METADATA_V1",
            "day_jst": day, "total_history_runs_available": result["total_count"],
            "history_rows_inspected": len(rows), "full_day_metadata_coverage": complete,
            "audit_as_of_jst": audit_as_of_jst.isoformat(),
            "jst_calendar_day_elapsed_at_audit": calendar_day_elapsed,
            "all_nominal_daily_slots_due_at_audit": due_slots == NOMINAL_DAILY_CAPTURE_SLOTS,
            "full_calendar_day_schedule_delivery_verified": False,
            "same_day_scheduled_run_count": len(matching),
            "same_day_pre_first_nominal_run_ids": pre_first_nominal_run_ids,
            "same_day_at_or_after_first_nominal_run_count": after_first_nominal_count,
            "same_day_after_final_nominal_grace_run_ids": after_final_window_run_ids,
            "same_day_within_nominal_window_run_count": within_window_count,
            "in_window_completed_success_run_ids": in_window_success_run_ids,
            "in_window_completed_success_count": len(in_window_success_run_ids),
            "observed_in_window_pct_of_nominal_due": observed_ratio,
            "schedule_observation_state": observation_state,
            "latest_in_window_run_created_at_jst": (
                latest_in_window.isoformat() if latest_in_window is not None
                else None),
            "minutes_since_latest_in_window_observation": observation_silence_minutes,
            "in_window_silence_observation_end_jst": observation_end.isoformat(),
            "observed_within_window_below_nominal_due_by": max(
                0, due_slots - within_window_count),
            "observed_after_first_runs_below_nominal_due_by": max(
                0, due_slots - after_first_nominal_count),
            "nominal_schedule_slots_per_jst_day": NOMINAL_DAILY_CAPTURE_SLOTS,
            "nominal_schedule_slots_due_as_of_audit": due_slots,
            "observed_runs_below_nominal_due_by": max(0, due_slots - len(matching)),
            "per_slot_schedule_delivery_verified": False,
            "failed_run_ids": failed, "pending_or_unknown_run_ids": pending,
            "forecast_publication_verified": False,
            "per_run_artifact_coverage_verified": False,
            "note": ("full_day_metadata_coverage refers to the bounded GitHub API "
                     "history page through audit_as_of_jst, NOT completion of the "
                     "calendar day. Created-at counts may include delayed prior "
                     "cron triggers; any pre-07:07 JST observations are "
                     "excluded from the execution-presence gate while retained "
                     "in the raw same-day count. Runs after the final 20:52 "
                     "JST slot plus five minutes remain raw observations but "
                     "do not satisfy the daily window-presence gate. Future-"
                     "dated API entries fail closed. Observation ratio and "
                     "25-percent triage state compare run-start counts to "
                     "nominal due only, not attributable Cron deliveries or "
                     "independently first-seen publication. Last-run silence is "
                     "bounded by the day's final nominal grace and is not "
                     "proof of specific missing Cron slots, deadline-qualified "
                     "collection, or forecast publication.")}


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
    if (result["schedule_observation_state"] == "severely_below_nominal_observation"
            and os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"):
        print("::warning::SEVERE observed scheduled-run scarcity: "
              f"{result['same_day_within_nominal_window_run_count']} "
              f"starts across {result['nominal_schedule_slots_due_as_of_audit']} "
              f"nominal due slots "
              f"({result['observed_in_window_pct_of_nominal_due']}%). "
              "This is a risk marker, NOT certified missing Cron deliveries.")
    if (result["observed_within_window_below_nominal_due_by"] > 0
            and os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"):
        shortfall = result["observed_within_window_below_nominal_due_by"]
        print(f"::warning::In-window schedule observations below nominal due by "
              f"{shortfall}; numerical shortfall ONLY, individual missing "
              "Cron slots are NOT proven by created_at metadata")
    if (os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"):
        if not result["full_day_metadata_coverage"]:
            print("::error::Full JST day scheduled run metadata not covered by API page")
            raise SystemExit(2)
        if (result["nominal_schedule_slots_due_as_of_audit"] > 0
                and result["same_day_within_nominal_window_run_count"] == 0):
            print("::error::No scheduled V2 capture in nominal JST window; "
                  "pre-opening delayed runs cannot certify today's execution, "
                  "nor can post-window late runs")
            raise SystemExit(2)
        if result["failed_run_ids"]:
            print("::error::Scheduled V2 captures failed earlier today, outside bounded artifact audit")
            raise SystemExit(2)
        if result["pending_or_unknown_run_ids"]:
            print("::error::Scheduled V2 captures are pending or have no confirmed outcome; day cannot be certified")
            raise SystemExit(2)


if __name__ == "__main__":
    main()
