"""Read-only observed four-mode Actions job/attempt inventory.

Expands a fully paginated UTC-day Actions run-metadata inventory into actual
per-attempt job/step pages. This is NOT a complete expected Cron inventory,
not proof of a remotely first-seen candidate, nor official T-12 admission.
No production writes, new Cron, candidate generation or result access.
"""
import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from four_mode_top1_capture_run_inventory import fetch_day, summarize

REPO = "ikst2512-eng/boat-edge-clean"
STEP_FREEZE = "Freeze all four-mode research candidates from published original"
STEP_LEDGER = "Preserve four-mode candidates on existing write-once Git evidence branch"
STEP_ORIGINAL = "Capture predeadline records"
MAX_JOBS = 1000


def fetch_job_pages(run_id, attempt, *, token=None, reader=None):
    if (type(run_id) is not int or run_id <= 0 or type(attempt) is not int
            or not 1 <= attempt <= 20):
        raise ValueError("invalid_run_or_attempt")
    if reader is None:
        if not token:
            raise ValueError("missing_github_read_token")
        def reader(url):
            req = urllib.request.Request(url, headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "four-mode-observed-job-attempt-readonly",
            })
            with urllib.request.urlopen(req, timeout=25) as response:
                if response.status != 200:
                    raise ValueError("github_job_api_not_200")
                raw = response.read(3_000_001)
                if len(raw) > 3_000_000:
                    raise ValueError("github_job_page_oversized")
                return json.loads(raw)
    pages = []
    total = None
    page = 1
    while True:
        url = (f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}"
               f"/attempts/{attempt}/jobs?" +
               urllib.parse.urlencode({"per_page": 100, "page": page}))
        payload = reader(url)
        if not isinstance(payload, dict):
            raise ValueError("malformed_job_page")
        n, rows = payload.get("total_count"), payload.get("jobs")
        if (type(n) is not int or not 0 <= n <= MAX_JOBS
                or type(rows) is not list):
            raise ValueError("invalid_job_page_total")
        if total is None:
            total = n
        if total != n or len(rows) != min(100, max(0, n - 100*(page-1))):
            raise ValueError("truncated_or_unstable_job_pages")
        pages.append({"run_id": run_id, "attempt": attempt,
                      "page": page, "total_count": n, "jobs": rows})
        if page >= max(1, (n + 99)//100):
            break
        page += 1
    return pages


def review(day, run_report, job_pages):
    """Retain missing-runs uncertainty; never infer actual shadow publication."""
    if (not isinstance(run_report, dict)
            or run_report.get("utc_day") != day
            or run_report.get("schema") !=
               "FOUR_MODE_TOP1_GITHUB_RUN_METADATA_INVENTORY_V1"
            or run_report.get("formal") is not False
            or run_report.get("complete_expected_schedule_inventory_verified") is not False
            or type(run_report.get("capture_runs")) is not list
            or type(job_pages) is not list):
        raise ValueError("untrusted_observed_capture_roster")

    wanted = {}
    for run in run_report["capture_runs"]:
        if (type(run) is not dict or type(run.get("run_id")) is not int
                or type(run.get("attempts_reported")) is not int
                or not 1 <= run["attempts_reported"] <= 20
                or run.get("event") not in ("schedule", "workflow_dispatch")
                or type(run.get("head_sha")) is not str
                or re.fullmatch(r"[0-9a-f]{40}", run["head_sha"]) is None):
            raise ValueError("invalid_capture_run_identity")
        rid = run["run_id"]
        if rid in wanted:
            raise ValueError("duplicate_capture_run_id")
        wanted[rid] = run

    pages = {}
    for p in job_pages:
        if (type(p) is not dict or type(p.get("run_id")) is not int
                or p["run_id"] not in wanted
                or type(p.get("attempt")) is not int
                or not 1 <= p["attempt"] <= wanted[p["run_id"]]["attempts_reported"]
                or type(p.get("page")) is not int
                or p["page"] < 1 or type(p.get("total_count")) is not int
                or not 0 <= p["total_count"] <= MAX_JOBS
                or type(p.get("jobs")) is not list):
            raise ValueError("unexpected_job_attempt_page")
        key = (p["run_id"], p["attempt"])
        pages.setdefault(key, []).append(p)

    records, all_ids = [], set()
    for rid, run in sorted(wanted.items()):
        for attempt in range(1, run["attempts_reported"]+1):
            key = (rid, attempt)
            group = sorted(pages.pop(key, []), key=lambda x:x["page"])
            if not group:
                raise ValueError("missing_observed_job_attempt")
            total = group[0]["total_count"]
            expected = max(1, (total+99)//100)
            if (len(group) != expected or
                    [p["page"] for p in group] != list(range(1, expected+1))):
                raise ValueError("missing_or_duplicate_job_page")
            rows = []
            for page in group:
                needed = min(100, max(0, total - 100*(page["page"]-1)))
                if page["total_count"] != total or len(page["jobs"]) != needed:
                    raise ValueError("unverifiable_job_page_completeness")
                rows.extend(page["jobs"])
            if len(rows) != total:
                raise ValueError("missing_jobs")
            stage_names = []
            job_names = []
            job_outcomes = []
            for job in rows:
                if (type(job) is not dict or type(job.get("id")) is not int
                        or job["id"] <= 0 or job["id"] in all_ids
                        or job.get("run_id") != rid or job.get("run_attempt") != attempt
                        or not isinstance(job.get("name"), str)
                        or job.get("name") not in ("test", "capture")
                        or job.get("status") not in ("queued", "in_progress", "completed")
                        or (job["status"] == "completed" and
                            job.get("conclusion") not in
                            ("success", "failure", "cancelled", "skipped",
                             "timed_out", "action_required", "neutral"))):
                    raise ValueError("invalid_or_duplicate_attempt_job")
                all_ids.add(job["id"])
                job_names.append(job["name"])
                job_outcomes.append(job.get("conclusion"))
                steps = job.get("steps")
                if steps is None:
                    if job["status"] == "completed" and job["conclusion"] != "skipped":
                        raise ValueError("completed_job_missing_step_details")
                    continue
                if type(steps) is not list:
                    raise ValueError("malformed_job_steps")
                for s in steps:
                    if (type(s) is not dict or not isinstance(s.get("name"), str)
                            or s.get("status") not in
                            ("queued", "in_progress", "completed", "pending")):
                        raise ValueError("malformed_step_metadata")
                    if s["name"] in (STEP_ORIGINAL, STEP_FREEZE, STEP_LEDGER):
                        if job["name"] != "capture":
                            raise ValueError("candidate_step_in_non_capture_job")
                        stage_names.append((s["name"], s.get("conclusion")))
            if len(set(job_names)) != len(job_names):
                raise ValueError("duplicate_attempt_job_role")
            for stage in (STEP_ORIGINAL, STEP_FREEZE, STEP_LEDGER):
                if sum(name == stage for name, _ in stage_names) > 1:
                    raise ValueError("duplicate_pipeline_stage")
            has_freeze = any(s == STEP_FREEZE for s,_ in stage_names)
            has_ledger = any(s == STEP_LEDGER for s,_ in stage_names)
            if has_freeze != has_ledger:
                raise ValueError("partial_candidate_stage_execution_inventory")
            executed = (has_freeze and has_ledger and
                        all(conclusion == "success" for name, conclusion
                            in stage_names if name in (STEP_FREEZE, STEP_LEDGER)))
            records.append({
                "run_id": rid, "run_attempt": attempt, "event": run["event"],
                "head_sha": run["head_sha"],
                "job_count": len(rows), "job_names": sorted(job_names),
                "job_conclusions": dict(zip(job_names, job_outcomes)),
                "original_capture_step_present": any(
                    s == STEP_ORIGINAL for s, _ in stage_names),
                "candidate_step_pair_present": has_freeze and has_ledger,
                "candidate_steps_succeeded_not_publication": bool(executed),
                "candidate_bytes_and_remote_initial_receipt_checked": False,
                "formal": False,
            })
    if pages:
        raise ValueError("extra_job_pages_outside_reported_attempts")

    return {
        "schema": "FOUR_MODE_OBSERVED_CAPTURE_JOB_ATTEMPTS_V1",
        "day_utc": day,
        "status": "bounded_reported_github_actions_attempt_job_inventory_only",
        "observed_capture_runs": len(wanted),
        "observed_run_attempts_with_complete_job_metadata": len(records),
        "observed_capture_job_attempts": sum(
            "capture" in r["job_names"] for r in records),
        "attempts_with_candidate_stage_pair": sum(
            r["candidate_step_pair_present"] for r in records),
        "candidate_stages_succeeded_not_publication": sum(
            r["candidate_steps_succeeded_not_publication"] for r in records),
        "attempts": records,
        "complete_observed_job_attempt_pages": True,
        "complete_expected_schedule_inventory_verified": False,
        "candidate_artifact_publication_verified": False,
        "candidate_independent_first_remote_receipt_verified": False,
        "official_three_original_t12_verified": False,
        "formal": False, "admitted_prospective_pairs": 0,
        "model_improvement_proven": False, "model_promotion_allowed": False,
        "warning": "All *reported* job attempts, not all nominal Cron slots. "
                   "A completed job or candidate stage never independently proves "
                   "remote candidate acceptance or official original source use.",
    }


def run_live(day, *, token):
    if not token:
        raise ValueError("github_token_required")
    report = summarize(fetch_day(day, token=token), day)
    pages = []
    for row in report["capture_runs"]:
        for attempt in range(1, row["attempts_reported"]+1):
            pages.extend(fetch_job_pages(row["run_id"], attempt, token=token))
    return review(day, report, pages)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--utc-day", required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    report = run_live(args.utc_day, token=os.environ.get("GH_TOKEN"))
    output = json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2)+"\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print("FOUR_MODE_CAPTURE_ATTEMPT_INVENTORY=" + json.dumps(
        {k:v for k,v in report.items() if k != "attempts"}, sort_keys=True))


if __name__ == "__main__":
    main()
