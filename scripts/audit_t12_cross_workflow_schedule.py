"""Read-only, historical schedule activation controls in the SAME UTC 00-12 hours.

The comparison intentionally excludes Nov 1-5: the selected collector,
entry-T12 control and CLEAN schedule configurations were edited/introduced
during Nov 3-5. Their current main cron expressions are only documented
assumptions; GitHub run-created_at does not identify the intended cron slot.

This audits metadata for trigger scarcity, never raw official source receipts,
GitHub's root cause, forecast validity or formal accuracy.
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.audit_official_pair_schedule_continuity import parse_utc

UTC = timezone.utc
DAY = re.compile(r"20[0-9]{6}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SCHEMA = "T12_CROSS_WORKFLOW_SCHEDULE_CONTROL_V1"
WORKFLOWS = {
    "official_pair": {
        "path": ".github/workflows/research-live-preview-evidence.yml",
        "cron": "*/5 0-12 * * *",
        "common_window_nominal_slots_per_day": 156,
    },
    "entry_t12_control": {
        "path": ".github/workflows/entry-course-t12-baseline.yml",
        "cron": "*/5 0-13 * * *",
        "common_window_nominal_slots_per_day": 156,
    },
    "clean_capture_control": {
        "path": ".github/workflows/clean-prospective.yml",
        "cron": "4,19,34,49 0-12 * * *",
        "common_window_nominal_slots_per_day": 52,
    },
}
PAGE_SIZE = 100
MAX_PAGES = 20


def compare(repo, start_day, end_day, token=None, *, fetch=None, as_of=None):
    if not isinstance(repo, str) or not REPO.fullmatch(repo):
        raise ValueError("invalid GitHub repository")
    if any(not isinstance(s, str) or not DAY.fullmatch(s)
           for s in (start_day, end_day)):
        raise ValueError("invalid UTC date")
    try:
        start = datetime.strptime(start_day, "%Y%m%d").replace(tzinfo=UTC)
        end = datetime.strptime(end_day, "%Y%m%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError("invalid UTC date") from exc
    days = (end-start).days + 1
    if days < 1 or days > 8:
        raise ValueError("history span must be 1 to 8 complete days")
    # Prevent invalid historical cron comparisons across workflow revisions.
    if start < datetime(2026, 11, 6, tzinfo=UTC):
        raise ValueError("historical configuration not stable before Nov 6")
    now = as_of if as_of is not None else datetime.now(UTC)
    if not isinstance(now, datetime) or now.utcoffset() != timedelta(0):
        raise ValueError("observation clock must be timezone-aware UTC")
    now = now.astimezone(UTC)
    if now < end + timedelta(hours=12, minutes=55):
        raise ValueError("end day has unfinished nominal schedule slots")
    if fetch is None and (not isinstance(token, str) or not token):
        raise ValueError("authenticated GitHub read required")
    root = "https://api.github.com/repos/" + repo + "/actions/runs"

    def request(url):
        if fetch is not None:
            return fetch(url)
        req = Request(url, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Cache-Control": "no-cache",
            "User-Agent": "BOAT-EDGE-T12-CROSS-WORKFLOW-AUDIT",
        })
        with urlopen(req, timeout=20) as response:
            if response.status != 200:
                raise ValueError("unexpected GitHub API status")
            return json.load(response)

    selected = {name: {"created_in_common_hours": 0,
                       "created_outside_common_hours": 0,
                       "conclusion_success": 0,
                       "conclusion_failure": 0,
                       "conclusion_other": 0,
                       "in_hours_run_ids": [],
                       "outside_hours_run_ids": []}
                for name in WORKFLOWS}
    rows_by_day = []
    global_ids = set()
    for i in range(days):
        date = (start+timedelta(days=i)).strftime("%Y-%m-%d")
        expected_day = (start+timedelta(days=i)).date()
        all_runs = []
        total = None
        for page in range(1, MAX_PAGES+1):
            query = urlencode({"event": "schedule", "created": date,
                               "per_page": PAGE_SIZE, "page": page})
            data = request(root + "?" + query)
            if not isinstance(data, dict) or not isinstance(data.get("workflow_runs"), list):
                raise ValueError("invalid GitHub schedule API response")
            count = data.get("total_count")
            part = data["workflow_runs"]
            if (type(count) is not int or count < 0
                    or (total is not None and total != count)
                    or len(part) > PAGE_SIZE):
                raise ValueError("invalid GitHub schedule pagination")
            total = count
            all_runs += part
            if len(all_runs) == total:
                break
            if len(all_runs) > total or len(part) != PAGE_SIZE:
                raise ValueError("incomplete GitHub schedule pagination")
        else:
            raise ValueError("schedule pagination exceeded bounded limit")

        daily = {name: {"in": 0, "off": 0} for name in WORKFLOWS}
        for run in all_runs:
            if not isinstance(run, dict) or run.get("event") != "schedule":
                raise ValueError("untrusted non-schedule run in schedule API")
            rid = run.get("id")
            if type(rid) is not int or rid <= 0 or rid in global_ids:
                raise ValueError("duplicate or invalid GitHub run identity")
            global_ids.add(rid)
            created = parse_utc(run.get("created_at"))
            if created.date() != expected_day or created > now:
                raise ValueError("cross-day or future GitHub run")
            path = run.get("path")
            if not isinstance(path, str):
                raise ValueError("workflow path missing")
            for name, config in WORKFLOWS.items():
                if path != config["path"]:
                    continue
                # Creation hour is an observation, not a verified exact slot.
                in_hours = created.hour < 13
                verdict = run.get("conclusion")
                record = selected[name]
                if in_hours:
                    daily[name]["in"] += 1
                    record["created_in_common_hours"] += 1
                    record["in_hours_run_ids"].append(rid)
                else:
                    daily[name]["off"] += 1
                    record["created_outside_common_hours"] += 1
                    record["outside_hours_run_ids"].append(rid)
                kind = (verdict if verdict in ("success", "failure")
                        else "other")
                record["conclusion_" + kind] += 1
                break
        rows_by_day.append({
            "day_utc": date,
            "total_repository_schedule_events": total,
            "controls": daily,
        })
    final = {}
    for name, config in WORKFLOWS.items():
        row = selected[name]
        expected = days * config["common_window_nominal_slots_per_day"]
        count = row["created_in_common_hours"]
        final[name] = {
            "workflow_path": config["path"],
            "declared_cron_assumption": config["cron"],
            "nominal_common_window_slots": expected,
            **row,
            "creation_hour_coverage_pct": round(100*count/expected, 2),
            "nominal_creation_count_shortfall": max(0, expected-count),
            "scheduled_slot_identity_verified": False,
            "source_http_attempts_verified": False,
            "formal": False,
        }
    return {
        "schema": SCHEMA,
        "repo": repo,
        "start_day_utc": start_day,
        "end_day_utc": end_day,
        "as_of_utc": now.isoformat(),
        "scope": "UTC 00:00-12:55 equal-time comparison, completed days only",
        "cron_assumptions_used_not_independently_verified_at_each_run": True,
        "observed_run_creation_cannot_prove_scheduled_slot": True,
        "github_root_cause_verified": False,
        "cross_workflow_scheduler_failure_proved": False,
        "absent_run_http_failures_proved": False,
        "raw_official_source_bytes_replayed": False,
        "new_formal_certifications": 0,
        "formal_accuracy_denominator": None,
        "formal": False,
        "t12_eligible": False,
        "accuracy_scoring_allowed": False,
        "controls": final,
        "daily": rows_by_day,
        "note": (
            "Source and two controls exhibit observed GitHub event=schedule "
            "run creation in comparable UTC hours, not intended cron-slot "
            "identity. Different workflows can have different contention, "
            "concurrency, actor and activation state; similarities do not "
            "identify GitHub as the root cause. Out-of-hours creations are "
            "reported separately, never assigned to missing slots."
        ),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--start-day", required=True)
    p.add_argument("--end-day", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    report = compare(a.repo, a.start_day, a.end_day,
                     token=os.environ.get("GITHUB_TOKEN"))
    output = Path(a.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("T12_CROSS_WORKFLOW_SCHEDULE_CONTROL=" + json.dumps(
        {k: v for k, v in report.items() if k != "daily"},
        ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
