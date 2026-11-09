"""Read-only job-level cross-check for #1698 original-capture Actions visibility.

Uses an independently saved, time-windowed scheduled+manual run inventory
as input. It then looks up each matching run's actual GitHub Actions jobs.
It NEVER assigns runs to cron slots, dispatches anything, reads results,
changes a forecast, or treats a green capture job as a remote publication.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import urllib.error
import urllib.request
import os

from position_sensitive_schedule_run_inventory import (
    ROOT_URL, WORKFLOW, SCHEMA as SOURCE_SCHEMA, _at_utc,
)

SCHEMA = "POSITION_SENSITIVE_SCHEDULE_CAPTURE_JOBS_RECONCILE_V1"
MAX_RUNS = 250
MAX_JOBS = 1000
PER_PAGE = 100
JOB_NAMES = ("test", "capture")
SUCCESS = "success"
CONCLUSIONS = (
    None, "success", "failure", "cancelled", "skipped", "timed_out",
    "action_required", "neutral", "stale",
)
STATES = ("queued", "in_progress", "completed")


def jobs_url(run_id, page):
    if type(run_id) is not int or run_id <= 0 or type(page) is not int or not 1 <= page <= 10:
        raise ValueError("invalid_run_or_page")
    return ROOT_URL + f"/actions/runs/{run_id}/jobs?per_page=100&page={page}"


def _job_pages(fetch, run_id):
    if not callable(fetch):
        raise ValueError("invalid_job_fetcher")
    seen = []
    for page in range(1, 11):
        data = fetch(jobs_url(run_id, page))
        seen.append(data)
        if (type(data) is dict and type(data.get("total_count")) is int
                and type(data.get("jobs")) is list
                and len(seen) >= max(1, (data["total_count"]+PER_PAGE-1)//PER_PAGE)):
            break
    total = None
    all_jobs = []
    for result in seen:
        if (type(result) is not dict
                or type(result.get("total_count")) is not int
                or not 0 <= result["total_count"] <= MAX_JOBS
                or type(result.get("jobs")) is not list
                or len(result["jobs"]) > PER_PAGE):
            raise ValueError("invalid_jobs_response")
        if total is None:
            total = result["total_count"]
        elif total != result["total_count"]:
            raise ValueError("jobs_page_count_changed")
        all_jobs.extend(result["jobs"])
    if len(seen) != max(1, (total+PER_PAGE-1)//PER_PAGE) or len(all_jobs) != total:
        raise ValueError("jobs_pagination_incomplete")
    return all_jobs


def reconcile_jobs(inventory, fetch):
    """Fail-close exact job inventory; preserve separate schedule and manual."""
    if (type(inventory) is not dict or inventory.get("schema") != SOURCE_SCHEMA
            or inventory.get("status") !=
            "read_only_schedule_vs_observed_created_runs_NOT_slot_attribution"
            or inventory.get("api_result_pagination_complete_for_supplied_window") is not True
            or inventory.get("manual_dispatch_api_checked") is not True
            or inventory.get("source_workflow_path") != WORKFLOW
            or inventory.get("three_source_cron_expressions_checked_against_snapshot") is not True
            or inventory.get("expected_slots_for_full_day") != 56
            or inventory.get("run_to_exact_cron_slot_attribution_verified") is not False
            or inventory.get("formal") is not False
            or inventory.get("promotion_allowed") is not False
            or not callable(fetch)):
        raise ValueError("untrusted_source_schedule_inventory")
    scheduled = inventory.get("matching_scheduled_runs")
    manual = inventory.get("matching_manual_dispatch_runs")
    if type(scheduled) is not list or type(manual) is not list:
        raise ValueError("source_run_lists_missing")
    if (len(scheduled) != inventory.get("observed_matching_four_mode_scheduled_runs")
            or len(manual) != inventory.get("observed_matching_four_mode_manual_dispatch_runs")
            or len(scheduled) + len(manual) > MAX_RUNS):
        raise ValueError("source_run_count_inconsistent")
    seen_run = set()
    rows = []
    for event, recs in (("schedule",scheduled), ("workflow_dispatch",manual)):
        for record in recs:
            if (type(record) is not dict or type(record.get("run_id")) is not int
                    or record["run_id"] <= 0
                    or record["run_id"] in seen_run
                    or record.get("status") not in STATES
                    or record.get("conclusion") not in CONCLUSIONS):
                raise ValueError("source_run_identity_or_status_invalid")
            seen_run.add(record["run_id"])
            _at_utc(record.get("created_at_utc"))
            if event == "workflow_dispatch":
                if (type(record.get("main_capture_branch")) is not bool
                        or type(record.get("branch")) is not str
                        or record["main_capture_branch"] != (record["branch"] == "main")):
                    raise ValueError("wrong_manual_branch_claim")
            jobs = _job_pages(fetch, record["run_id"])
            chosen = {}
            ids = set()
            for job in jobs:
                if (type(job) is not dict or type(job.get("id")) is not int
                        or job["id"] <= 0 or job["id"] in ids
                        or job.get("run_id") != record["run_id"]
                        or type(job.get("name")) is not str
                        or job.get("status") not in STATES
                        or job.get("conclusion") not in CONCLUSIONS):
                    raise ValueError("invalid_duplicate_or_foreign_job")
                ids.add(job["id"])
                if job["name"] in JOB_NAMES:
                    if job["name"] in chosen:
                        raise ValueError("duplicate_named_capture_job")
                    chosen[job["name"]] = job
            if set(chosen) != set(JOB_NAMES):
                raise ValueError("test_or_capture_job_missing")
            capture = chosen["capture"]
            test = chosen["test"]
            main_run = event == "schedule" or record.get("main_capture_branch") is True
            classification = (
                "main_capture_job_completed_success_no_publication_proof"
                if main_run and capture["status"] == "completed"
                and capture["conclusion"] == SUCCESS
                else "main_capture_job_not_completed_success"
                if main_run
                else "nonmain_dispatch_not_a_production_capture"
            )
            rows.append({
                "run_id": record["run_id"], "event": event,
                "run_created_utc": record["created_at_utc"],
                "run_conclusion": record["conclusion"],
                "main_capture_run": main_run,
                "test_job_id": test["id"],
                "test_job_conclusion": test["conclusion"],
                "capture_job_id": capture["id"],
                "capture_job_conclusion": capture["conclusion"],
                "capture_job_status": capture["status"],
                "classification": classification,
                "capture_job_success_proves_original_forecast_publication": False,
                "capture_job_success_proves_position_candidate_publication": False,
                "candidate_first_remote_receipt_verified": False,
            })
    scheduled_rows = [x for x in rows if x["event"] == "schedule"]
    manual_rows = [x for x in rows if x["event"] == "workflow_dispatch"]
    scheduled_success = sum(
        x["classification"] == "main_capture_job_completed_success_no_publication_proof"
        for x in scheduled_rows
    )
    manually_succeeded = sum(
        x["classification"] == "main_capture_job_completed_success_no_publication_proof"
        for x in manual_rows
    )
    return {
        "schema": SCHEMA,
        "status": "actions_jobs_read_only_confirmed_nonformal",
        "day_jst": inventory.get("day_jst"),
        "as_of_utc": inventory.get("as_of_utc"),
        "expected_schedule_slots_for_day": 56,
        "scheduled_slots_elapsed": inventory.get("scheduled_slots_elapsed"),
        "matching_schedule_runs": len(scheduled_rows),
        "matching_schedule_capture_jobs_success": scheduled_success,
        "matching_manual_dispatch_runs": len(manual_rows),
        "matching_manual_main_capture_jobs_success": manually_succeeded,
        "individual_run_jobs_verified": len(rows),
        "jobs": rows,
        "run_to_cron_slot_mapping_verified": False,
        "missing_scheduled_run_failures_proven": 0,
        "original_publication_verified_from_job_status": False,
        "position_candidate_publication_verified_from_job_status": False,
        "complete_scheduled_and_rescue_run_inventory_verified": False,
        "candidate_first_remote_receipts_independently_verified": 0,
        "official_T12_six_120_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "A GitHub Actions capture job's success proves a job completion "
            "as observed through an API result, NOT an original or candidate "
            "publish. Workflows may complete after no eligible files are staged. "
            "Cron intended-times cannot be mapped to created run IDs without "
            "separate reliable evidence. Manual rescue is NOT a cron slot."
        ),
    }


def get_jobs_json(url):
    if not re.fullmatch(
            re.escape(ROOT_URL)+r"/actions/runs/[1-9][0-9]*/jobs\?per_page=100&page=(?:10|[1-9])",
            url):
        raise ValueError("unapproved_actions_jobs_endpoint")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
        "User-Agent": "boat-edge-position-shadow-jobs-readonly",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            if res.status != 200 or res.headers.get("Age") is not None:
                raise ValueError("untrusted_github_jobs_http_or_cache")
            raw = res.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("actions_jobs_api_oversize")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise ValueError("github_jobs_http_"+str(exc.code)) from exc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--live", action="store_true",
                        help="Opt-in read-only GitHub Actions jobs queries")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.live:
        report = {
            "schema": SCHEMA,
            "status": "read_only_job_reconciliation_unstarted",
            "complete_scheduled_and_rescue_run_inventory_verified": False,
            "candidate_first_remote_receipts_independently_verified": 0,
            "formal": False, "promotion_allowed": False, "production_changed": False,
        }
    else:
        if (args.inventory is None or args.inventory.is_symlink()
                or not args.inventory.is_file()
                or args.inventory.stat().st_size > 300000):
            raise ValueError("missing_valid_schedule_inventory_file")
        data = json.loads(args.inventory.read_bytes())
        report = reconcile_jobs(data, get_jobs_json)
    raw = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)+"\n"
    if args.output:
        if args.output.is_symlink() or args.output.exists():
            raise ValueError("output_not_new_or_symlink")
        args.output.write_text(raw, encoding="utf-8")
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
