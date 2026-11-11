"""Read-only GitHub Actions capture-run enumeration, NOT formal first receipt.

Enumerates both schedule and workflow_dispatch for one UTC day. Captured run
metadata can establish which *reported* runs were listed. It cannot establish
missed schedules, complete job attempts, freeze provenance or first receipt.
No workflow modifications, writes to main, or result reads.
"""
import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = "ikst2512-eng/boat-edge-clean"
WORKFLOW = ".github/workflows/four-mode-prospective-capture.yml"
NAME = "Four-mode prospective capture (research only)"
EVENTS = ("schedule", "workflow_dispatch")
UTC = timezone.utc


def at_utc(value):
    if not isinstance(value, str):
        raise ValueError("invalid_utc_clock")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid_utc_clock") from exc
    if stamp.utcoffset() != timedelta(0):
        raise ValueError("non_utc_clock")
    return stamp


def fetch_day(day, *, token=None, reader=None):
    """Read all GitHub API pages, refuse truncation and unstable total_count."""
    if not isinstance(day, str) or not re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", day):
        raise ValueError("invalid_utc_day")
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("invalid_utc_day") from exc
    if reader is None:
        def reader(url):
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "boat-edge-top1-run-inventory-readonly",
            }
            if token:
                headers["Authorization"] = "Bearer " + token
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=25) as response:
                if response.status != 200:
                    raise ValueError("github_api_not_200")
                return json.loads(response.read(3_000_000))
    snapshots = []
    for event in EVENTS:
        page = 1
        expected_total = None
        while True:
            query = urllib.parse.urlencode({
                "event": event, "created": day, "per_page": 100,
                "page": page,
            })
            url = f"https://api.github.com/repos/{REPO}/actions/runs?{query}"
            payload = reader(url)
            if not isinstance(payload, dict):
                raise ValueError("invalid_github_api_page")
            count = payload.get("total_count")
            rows = payload.get("workflow_runs")
            if type(count) is not int or count < 0 or type(rows) is not list:
                raise ValueError("invalid_github_api_page")
            if count > 1000:
                raise ValueError("bounded_github_api_inventory_limit")
            if expected_total is None:
                expected_total = count
            if count != expected_total:
                raise ValueError("unstable_github_api_pagination")
            expected_pages = max(1, (count + 99) // 100)
            required = min(100, max(0, count - (page - 1) * 100))
            if page > expected_pages or len(rows) != required:
                raise ValueError("incomplete_github_api_page")
            snapshots.append({
                "utc_day": day, "event": event, "page": page,
                "total_count": count, "workflow_runs": rows,
            })
            if page >= expected_pages:
                break
            page += 1
    return snapshots


def summarize(snapshots, day):
    """Enumerate reported runs only; NEVER claim a fully attested roster."""
    if not isinstance(day, str) or not re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", day):
        raise ValueError("invalid_utc_day")
    try:
        start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError("invalid_utc_day") from exc
    end = start + timedelta(days=1)
    if not isinstance(snapshots, list):
        raise ValueError("invalid_snapshots")
    all_runs = []
    totals = {}
    for event in EVENTS:
        pages = [x for x in snapshots if isinstance(x, dict) and x.get("event") == event]
        if len(pages) == 0:
            raise ValueError("missing_github_api_event_pages")
        total = pages[0].get("total_count")
        if type(total) is not int or total < 0 or total > 1000:
            raise ValueError("unverifiable_api_total")
        required_pages = max(1, (total + 99) // 100)
        if len(pages) != required_pages:
            raise ValueError("missing_github_api_page")
        pages.sort(key=lambda x:x.get("page", -1))
        if [p.get("page") for p in pages] != list(range(1, required_pages+1)):
            raise ValueError("missing_or_duplicate_api_page")
        count = 0
        for page in pages:
            if page.get("utc_day") != day or page.get("total_count") != total:
                raise ValueError("wrong_api_filter_or_unstable_total")
            rows = page.get("workflow_runs")
            expected = min(100, max(0, total - (page["page"] - 1) * 100))
            if type(rows) is not list or len(rows) != expected:
                raise ValueError("truncated_or_duplicated_api_page")
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError("invalid_run_metadata")
                if row.get("event") != event:
                    raise ValueError("wrong_event_metadata")
                created = at_utc(row.get("created_at"))
                if not start <= created < end:
                    raise ValueError("wrong_utc_day_metadata")
                all_runs.append(row)
            count += len(rows)
        if count != total:
            raise ValueError("api_total_not_fully_enumerated")
        totals[event] = total
    if len(snapshots) != sum(max(1, (totals[x] + 99)//100) for x in EVENTS):
        raise ValueError("unrecognized_extra_api_page")
    ids = [r.get("id") for r in all_runs]
    if any(type(x) is not int or x <= 0 for x in ids) or len(set(ids)) != len(ids):
        raise ValueError("duplicate_or_invalid_github_run_id")
    # Match by either immutable workflow path OR current display name.
    # A renamed capture workflow must be surfaced as an identity conflict,
    # never silently dropped from the reported run population.
    selected = [r for r in all_runs
                if r.get("name") == NAME or r.get("path") == WORKFLOW]
    report = []
    for r in sorted(selected, key=lambda x:(x["created_at"], x["id"])):
        if (r.get("name") != NAME or r.get("path") != WORKFLOW
                or r.get("head_branch") != "main"
                or r.get("event") not in EVENTS):
            raise ValueError("wrong_capture_workflow_identity")
        attempt = r.get("run_attempt")
        if type(attempt) is not int or attempt < 1:
            raise ValueError("missing_run_attempt")
        report.append({
            "run_id": r["id"], "attempts_reported": attempt,
            "event": r["event"], "created_at_utc": r["created_at"],
            "status": r.get("status"), "conclusion": r.get("conclusion"),
            "head_sha": r.get("head_sha"),
            "needs_all_attempts_audit": attempt > 1,
            "job_steps_independently_verified": False,
        })
    return {
        "schema": "FOUR_MODE_TOP1_GITHUB_RUN_METADATA_INVENTORY_V1",
        "utc_day": day,
        "status": "bounded_github_api_metadata_enumeration_reference_only",
        "all_workflow_runs_listed_by_event": totals,
        "observed_capture_runs": len(report),
        "capture_runs": report,
        "complete_expected_schedule_inventory_verified": False,
        "complete_job_attempts_verified": False,
        "candidate_first_remote_receipt_verified": False,
        "actual_top1_shadow_published_verified": False,
        "official_t_minus_12_verified": False,
        "formal": False,
        "model_promotion_allowed": False,
        "warning": "GitHub paginated run metadata does not prove skipped/missing "
                   "scheduled invocations or complete jobs/attempts; no independent "
                   "candidate first receipt, no official pre-race feed validation.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--utc-day", required=True)
    parser.add_argument("--fetch", action="store_true",
                        help="Read-only GitHub Actions API enumeration")
    parser.add_argument("--snapshot", action="append", type=Path, default=[])
    args = parser.parse_args()
    if bool(args.fetch) == bool(args.snapshot):
        raise SystemExit("provide --fetch OR one or more --snapshot files")
    payload = (fetch_day(args.utc_day, token=os.environ.get("GH_TOKEN"))
               if args.fetch else
               [json.loads(x.read_bytes()) for x in args.snapshot])
    print(json.dumps(summarize(payload, args.utc_day), ensure_ascii=False,
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
