"""Read-only original four-mode scheduled-run visibility audit for #1698.

An elapsed cron slot and an Actions run creation are different facts.
Never attribute a run to an exact cron slot by timestamp, infer that a
missing run was skipped, or mark outcome/candidate first-receipt eligibility.

No publishing, dispatch, results, production workflow modification or
research branch writes. Live GitHub API GET is opt-in and read-only.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

REPO = "ikst2512-eng/boat-edge-clean"
ROOT_URL = "https://api.github.com/repos/" + REPO
WORKFLOW = ".github/workflows/four-mode-prospective-capture.yml"
SOURCE_REF = "refs/remotes/origin/main"
SCHEMA = "POSITION_SENSITIVE_SCHEDULED_RUN_VISIBILITY_V1"
JST = timezone(timedelta(hours=9))
UTC = timezone.utc
CRONS = (
    "7,22,37,52 22 * * *",
    "7,22,37,52 23 * * *",
    "7,22,37,52 0-11 * * *",
)
HOURS_JST = range(7, 21)
MINUTES = (7, 22, 37, 52)
MAX_RUNS = 2000
PER_PAGE = 100
DAY_RE = re.compile(r"20[0-9]{6}\Z")
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")


def _at_utc(value):
    if type(value) is not str:
        raise ValueError("missing_utc_time")
    try:
        v = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid_utc_time") from exc
    if v.utcoffset() != timedelta(0):
        raise ValueError("expected_utc_time")
    return v


def _check_day(day):
    if type(day) is not str or DAY_RE.fullmatch(day) is None:
        raise ValueError("invalid_research_day")
    try:
        parsed = datetime.strptime(day, "%Y%m%d").date()
    except ValueError as exc:
        raise ValueError("invalid_calendar_day") from exc
    if not date(2026, 11, 9) <= parsed <= date(2026, 12, 31):
        raise ValueError("day_outside_preregistered_future_window")
    return parsed


def _source_schedule(workflow_bytes):
    if type(workflow_bytes) is not bytes or not 0 < len(workflow_bytes) < 50000:
        raise ValueError("invalid_production_schedule_source")
    try:
        s = workflow_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("schedule_not_utf8") from exc
    # Count each line exactly once: never quietly compare a shifted schedule
    # to a frozen 56-slot forecast or imply the YAML was independently signed.
    cron_lines = re.findall(r"(?m)^\s+- cron: '([^']+)'\s*$", s)
    if (sorted(cron_lines) != sorted(CRONS) or
            "schedule:" not in s or "workflow_dispatch:" not in s or
            "github.ref == 'refs/heads/main'" not in s or
            "if: github.ref == 'refs/heads/main'" not in s):
        raise ValueError("production_schedule_changed_or_unverifiable")
    return True


def _slots(day):
    d = _check_day(day)
    return [
        datetime(d.year, d.month, d.day, hour, minute, tzinfo=JST)
        for hour in HOURS_JST for minute in MINUTES
    ]


def query_window(day, now_utc):
    if (type(now_utc) is not datetime or now_utc.utcoffset() != timedelta(0)):
        raise ValueError("invalid_observation_clock")
    d = _check_day(day)
    # Include a one-hour lead-in before the first 07:07 JST slot. This is a
    # created-at retrieval window, NOT a promised precise slot attribution.
    beginning = datetime(d.year, d.month, d.day, 6, 0, tzinfo=JST).astimezone(UTC)
    if not beginning < now_utc < (beginning + timedelta(days=2)):
        raise ValueError("observation_outside_valid_future_window")
    # The API query has an exact upper bound, so the supplied as-of instant
    # cannot accidentally include results observed later.
    return beginning, now_utc


def schedule_run_url(day, now_utc, page, event="schedule"):
    if event not in ("schedule", "workflow_dispatch"):
        raise ValueError("invalid_actions_event")
    if type(page) is not int or not 1 <= page <= 20:
        raise ValueError("invalid_actions_page")
    start, end = query_window(day, now_utc)
    window = (start.strftime("%Y-%m-%dT%H:%M:%SZ") + ".." +
              end.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return ROOT_URL + "/actions/runs?" + urllib.parse.urlencode({
        "event": event, "created": window,
        "per_page": PER_PAGE, "page": page,
    })


def audit_run_inventory(day, now_utc, workflow_bytes, pages, dispatch_pages=None):
    """Fully paginate a retrieved API window, without proving schedule coverage.

    A caller-provided page is untrusted; this pure function cannot attest
    actual API authenticity or excluded GitHub/server retention histories.
    """
    slots = _slots(day)
    _source_schedule(workflow_bytes)
    start, end = query_window(day, now_utc)
    if type(pages) is not list or not pages or len(pages) > 20:
        raise ValueError("missing_or_excess_api_pages")
    total = None
    allruns = []
    for page in pages:
        if (type(page) is not dict or type(page.get("total_count")) is not int
                or not 0 <= page["total_count"] <= MAX_RUNS
                or type(page.get("workflow_runs")) is not list
                or len(page["workflow_runs"]) > PER_PAGE):
            raise ValueError("invalid_actions_page_or_total")
        if total is None:
            total = page["total_count"]
        elif total != page["total_count"]:
            raise ValueError("inconsistent_actions_pagination_total")
        allruns.extend(page["workflow_runs"])
    expected_pages = max(1, (total + PER_PAGE - 1)//PER_PAGE)
    if len(pages) != expected_pages or len(allruns) != total:
        raise ValueError("actions_pagination_incomplete_or_overfull")
    seen = set()
    matches = []
    for r in allruns:
        if (type(r) is not dict or type(r.get("id")) is not int
                or r["id"] <= 0 or r["id"] in seen
                or r.get("event") != "schedule"):
            raise ValueError("unexpected_actions_run_or_duplicate_id")
        seen.add(r["id"])
        created = _at_utc(r.get("created_at"))
        if not start <= created <= end:
            raise ValueError("actions_run_outside_requested_time_window")
        if r.get("path") != WORKFLOW:
            continue
        if r.get("head_branch") != "main":
            raise ValueError("scheduled_capture_on_nonmain")
        if (r.get("status") not in ("queued", "in_progress", "completed")
                or r.get("conclusion") not in
                (None, "success", "failure", "cancelled", "skipped",
                 "timed_out", "action_required", "neutral", "stale")):
            raise ValueError("untrusted_run_state")
        matches.append({
            "run_id": r["id"],
            "created_at_utc": created.isoformat(),
            "status": r["status"],
            "conclusion": r["conclusion"],
        })
    matches.sort(key=lambda r: (r["created_at_utc"], r["run_id"]))
    # Separately enumerate explicit manual dispatches, not interchangeable with
    # schedule-created runs. This remains only a finite current API window.
    dispatch = []
    dispatch_total = None
    if dispatch_pages is not None:
        if (type(dispatch_pages) is not list or not dispatch_pages
                or len(dispatch_pages) > 20):
            raise ValueError("missing_or_excess_dispatch_pages")
        observed = set()
        seen_manual = 0
        for page in dispatch_pages:
            if (type(page) is not dict
                    or type(page.get("total_count")) is not int
                    or not 0 <= page["total_count"] <= MAX_RUNS
                    or type(page.get("workflow_runs")) is not list
                    or len(page["workflow_runs"]) > PER_PAGE):
                raise ValueError("invalid_manual_dispatch_api_page")
            if dispatch_total is None:
                dispatch_total = page["total_count"]
            elif dispatch_total != page["total_count"]:
                raise ValueError("manual_dispatch_pagination_changed")
            for run in page["workflow_runs"]:
                seen_manual += 1
                if (type(run) is not dict or type(run.get("id")) is not int
                        or run["id"] <= 0 or run["id"] in observed
                        or run["id"] in seen or
                        run.get("event") != "workflow_dispatch"):
                    raise ValueError("invalid_or_duplicate_manual_dispatch_run")
                observed.add(run["id"])
                created = _at_utc(run.get("created_at"))
                if not start <= created <= end:
                    raise ValueError("manual_dispatch_outside_requested_window")
                if run.get("path") != WORKFLOW:
                    continue
                if (run.get("head_branch") is None or
                        run.get("status") not in
                        ("queued", "in_progress", "completed") or
                        run.get("conclusion") not in
                        (None, "success", "failure", "cancelled", "skipped",
                         "timed_out", "action_required", "neutral", "stale")):
                    raise ValueError("untrusted_manual_dispatch_state")
                dispatch.append({
                    "run_id": run["id"],
                    "created_at_utc": created.isoformat(),
                    "branch": run["head_branch"],
                    "main_capture_branch": run["head_branch"] == "main",
                    "status": run["status"],
                    "conclusion": run["conclusion"],
                })
        if (len(dispatch_pages) != max(1, (dispatch_total + PER_PAGE - 1)//PER_PAGE)
                or seen_manual != dispatch_total):
            raise ValueError("manual_dispatch_pagination_incomplete")
        dispatch.sort(key=lambda x: (x["created_at_utc"], x["run_id"]))
    elapsed = [x for x in slots if x.astimezone(UTC) <= now_utc]
    future = [x for x in slots if x.astimezone(UTC) > now_utc]
    successes = sum(x["conclusion"] == "success" for x in matches)
    # Only a numerical comparison: the underlying GitHub scheduler can delay
    # run creation, may drop slots, and does not attach exact requested cron
    # times to these run-list records. This NEVER proves specific misses.
    return {
        "schema": SCHEMA,
        "status": "read_only_schedule_vs_observed_created_runs_NOT_slot_attribution",
        "day_jst": day,
        "as_of_utc": now_utc.isoformat(),
        "source_workflow_path": WORKFLOW,
        "three_source_cron_expressions_checked_against_snapshot": True,
        "expected_slots_for_full_day": len(slots),
        "expected_slot_times_jst": [v.isoformat() for v in slots],
        "elapsed_cron_slot_times_jst": [v.isoformat() for v in elapsed],
        "scheduled_slots_elapsed": len(elapsed),
        "scheduled_slots_not_yet_due": len(future),
        "api_query_window_start_utc": start.isoformat(),
        "api_query_window_end_utc": end.isoformat(),
        "api_runs_all_repo_workflows_in_window": total,
        "api_result_pagination_complete_for_supplied_window": True,
        "observed_matching_four_mode_scheduled_runs": len(matches),
        "observed_matching_workflow_success_conclusions": successes,
        "matching_scheduled_runs": matches,
        "manual_dispatch_api_checked": dispatch_pages is not None,
        "api_manual_dispatch_runs_all_repo_in_window": dispatch_total,
        "observed_matching_four_mode_manual_dispatch_runs": len(dispatch),
        "observed_manual_dispatch_main_branch_runs":
            sum(x["main_capture_branch"] for x in dispatch),
        "observed_manual_dispatch_nonmain_branch_runs":
            sum(not x["main_capture_branch"] for x in dispatch),
        "matching_manual_dispatch_runs": dispatch,
        "manual_dispatch_success_proves_capture_publication": False,
        "numerical_elapsed_minus_observed_run_count":
            len(elapsed) - len(matches),
        "this_difference_proves_individual_missed_or_failed_slots": False,
        "run_to_exact_cron_slot_attribution_verified": False,
        "observed_run_success_proves_forecast_publication": False,
        "complete_scheduled_and_rescue_run_inventory_verified": False,
        "api_responses_independently_authenticated_by_pure_function": False,
        "first_remote_candidate_receipts_verified": 0,
        "official_T12_six_120_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "Only runs returned in this time-windowed Actions list are counted. "
            "GitHub delayed/non-created scheduled jobs, undocumented rescues, "
            "workflow disablement and other external gaps are not independently "
            "exhausted. Expected cron-slot minus observed run count is a "
            "NUMERICAL gap, not verified missed executions. Run success alone "
            "does not prove candidate publication or first remote receipt."
        ),
    }


def _live_fetch_json(url):
    if not (url.startswith(ROOT_URL + "/actions/runs?event=schedule&")
            or url.startswith(ROOT_URL + "/actions/runs?event=workflow_dispatch&")):
        raise ValueError("not_allowlisted_readonly_actions_endpoint")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "boat-edge-position-sensitive-schedule-audit",
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            if r.status != 200 or r.headers.get("Age") is not None:
                raise ValueError("untrusted_actions_api_http_or_cache")
            stamp = parsedate_to_datetime(r.headers.get("Date"))
            if stamp.utcoffset() != timedelta(0):
                raise ValueError("invalid_actions_server_date")
            raw = r.read(5_000_001)
            if len(raw) > 5_000_000:
                raise ValueError("actions_response_too_large")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise ValueError("actions_api_http_" + str(exc.code)) from exc


def _git(*args):
    return subprocess.check_output(
        ["git", *args], timeout=30, stderr=subprocess.DEVNULL)


def live_audit(day, now_utc, fetch=_live_fetch_json, git=_git):
    if not callable(fetch) or not callable(git):
        raise ValueError("invalid_live_audit_dependency")
    ref = git("rev-parse", "--verify", SOURCE_REF + "^{commit}").decode().strip()
    if COMMIT_RE.fullmatch(ref) is None:
        raise ValueError("untrusted_main_ref")
    workflow = git("show", ref + ":" + WORKFLOW)
    def collect(event):
        rows = []
        for page_index in range(1, 21):
            obj = fetch(schedule_run_url(day, now_utc, page_index, event))
            rows.append(obj)
            if (type(obj) is dict and type(obj.get("total_count")) is int
                    and type(obj.get("workflow_runs")) is list and
                    len(rows) >= max(1, (obj["total_count"] + PER_PAGE - 1)//PER_PAGE)):
                break
        return rows
    scheduled = collect("schedule")
    dispatched = collect("workflow_dispatch")
    report = audit_run_inventory(day, now_utc, workflow, scheduled, dispatched)
    report["main_git_snapshot_sha"] = ref
    report["live_readonly_github_api_invoked"] = True
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", default=None)
    parser.add_argument("--live", action="store_true",
                        help="Opt-in read-only GitHub Actions GET; NEVER publishes")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    now = datetime.now(UTC)
    day = args.day or now.astimezone(JST).strftime("%Y%m%d")
    if args.live:
        report = live_audit(day, now)
    else:
        report = {
            "schema": SCHEMA,
            "status": "schedule_run_inventory_not_invoked",
            "first_remote_candidate_receipts_verified": 0,
            "complete_scheduled_and_rescue_run_inventory_verified": False,
            "formal": False, "promotion_allowed": False,
            "production_changed": False,
        }
    raw = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        if args.output.is_symlink() or args.output.exists():
            raise ValueError("output_must_be_new_regular_file")
        args.output.write_text(raw, encoding="utf-8")
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
