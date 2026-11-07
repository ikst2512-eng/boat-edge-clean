"""Read-only, fail-closed inventory of the official two-original collector's schedule.

GitHub Actions event=schedule metadata only. A run, including a green run, does
not prove HTTP source receipt, six-boat exhibition, or formal T-12 eligibility.
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

WORKFLOW_PATH = ".github/workflows/research-live-preview-evidence.yml"
EXPECTED_CRON = "*/5 0-12 * * *"  # Verified against main workflow; UTC, 156 slots.
UTC = timezone.utc
JST = timezone(timedelta(hours=9))
MAX_PAGES = 20
PAGE_SIZE = 100


def parse_utc(value):
    if not isinstance(value, str):
        raise ValueError("invalid schedule timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid schedule timestamp") from exc
    if stamp.utcoffset() != timedelta(0):
        raise ValueError("schedule timestamp must have UTC offset")
    return stamp.astimezone(UTC)


def inventory(repo, day, token, *, fetch=None, as_of=None):
    if not isinstance(repo, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("invalid repository")
    if not isinstance(day, str) or not re.fullmatch(r"20[0-9]{6}", day):
        raise ValueError("invalid UTC day")
    try:
        date = datetime.strptime(day, "%Y%m%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError("invalid UTC day") from exc
    if not isinstance(token, str) or not token:
        raise ValueError("GitHub read token required")
    now = as_of or datetime.now(UTC)
    if not isinstance(now, datetime) or now.utcoffset() != timedelta(0):
        raise ValueError("as_of must be timezone-aware UTC")
    now = now.astimezone(UTC)
    if now < date:
        elapsed = 0
    else:
        elapsed = sum(date + timedelta(hours=hour, minutes=minute) <= now
                      for hour in range(13) for minute in range(0, 60, 5))

    def request(url):
        if fetch is not None:
            return fetch(url)
        req = Request(url, headers={"Authorization": "Bearer " + token,
                                    "Accept": "application/vnd.github+json",
                                    "X-GitHub-Api-Version": "2022-11-28",
                                    "User-Agent": "BOAT-EDGE-T12-CONTINUITY-AUDIT"})
        with urlopen(req, timeout=20) as response:
            return json.load(response)

    base = "https://api.github.com/repos/" + repo + "/actions/runs"
    rows = []
    known_total = None
    for page in range(1, MAX_PAGES + 1):
        params = urlencode({"event": "schedule", "created": date.strftime("%Y-%m-%d"),
                            "per_page": PAGE_SIZE, "page": page})
        data = request(base + "?" + params)
        if not isinstance(data, dict) or not isinstance(data.get("workflow_runs"), list):
            raise ValueError("invalid GitHub schedule inventory")
        count = data.get("total_count")
        batch = data["workflow_runs"]
        if (type(count) is not int or count < 0 or len(batch) > PAGE_SIZE
                or (known_total is not None and count != known_total)):
            raise ValueError("inconsistent GitHub schedule pagination")
        known_total = count
        rows.extend(batch)
        if len(rows) == known_total:
            break
        if len(rows) > known_total or len(batch) != PAGE_SIZE:
            raise ValueError("incomplete GitHub schedule pagination")
    else:
        raise ValueError("GitHub schedule inventory exceeds page limit")

    ids = set()
    selected = []
    for run in rows:
        if not isinstance(run, dict) or run.get("event") != "schedule":
            raise ValueError("non-schedule item in schedule-only API response")
        rid = run.get("id")
        if type(rid) is not int or rid <= 0 or rid in ids:
            raise ValueError("duplicate or invalid GitHub run ID")
        ids.add(rid)
        created = parse_utc(run.get("created_at"))
        if created.date() != date.date() or created > now:
            raise ValueError("run lies outside the observed UTC day/time")
        path = run.get("path")
        if not isinstance(path, str):
            raise ValueError("run has no workflow path")
        if path != WORKFLOW_PATH:
            continue
        selected.append({"run_id": rid, "created_at_utc": created.isoformat(),
                         "created_at_jst": created.astimezone(JST).isoformat(),
                         "status": run.get("status"),
                         "conclusion": run.get("conclusion")})
    selected.sort(key=lambda r: r["created_at_utc"])
    expected = 13 * 12
    observed = len(selected)
    return {
        "schema": "OFFICIAL_PAIR_SCHEDULE_CONTINUITY_AUDIT_V1",
        "utc_day": day,
        "as_of_utc": now.isoformat(),
        "workflow_path": WORKFLOW_PATH,
        "expected_cron_assumption": EXPECTED_CRON,
        "expected_slots_full_day": expected,
        "elapsed_nominal_slots_at_snapshot": elapsed,
        "future_nominal_slots": expected - elapsed,
        "total_repository_schedule_runs": known_total,
        "observed_official_pair_schedule_runs": observed,
        "observed_to_elapsed_slot_pct": round(100 * observed / elapsed, 2) if elapsed else None,
        "nominal_invocation_count_deficit": max(0, elapsed - observed),
        "run_success": sum(r["conclusion"] == "success" for r in selected),
        "run_failure": sum(r["conclusion"] == "failure" for r in selected),
        "run_other_or_incomplete": sum(r["conclusion"] not in ("success", "failure")
                                       for r in selected),
        "schedule_slot_identity_verified": False,
        "missing_trigger_root_cause_verified": False,
        "raw_official_source_receipts_verified": False,
        "full_t12_source_certified": False,
        "forecast_usable": False,
        "note": ("Counts compare GitHub observed schedule events with nominal cron slots. "
                 "Delayed/dropped trigger attribution and the actual source contents "
                 "cannot be inferred from run metadata. Green no-op is not T-12 proof."),
        "runs": selected,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--day-utc", required=True, help="UTC YYYYMMDD; full day only after 12:55 UTC")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = inventory(args.repo, args.day_utc, os.environ.get("GITHUB_TOKEN", ""))
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print("OFFICIAL_PAIR_SCHEDULE_CONTINUITY=" +
          json.dumps({k: v for k, v in result.items() if k != "runs"}, sort_keys=True))


if __name__ == "__main__":
    main()
