"""Read-only, bounded, historical GitHub schedule creation-count trend.

Preserves uncertainty: event=schedule run creation is not a verified cron slot,
a raw official source receipt, or evidence of failed HTTP for absent events.
Never emits formal accuracy certification.
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.audit_official_pair_schedule_continuity import (
    inventory, WORKFLOW_PATH, EXPECTED_CRON,
)

DAY = re.compile(r"20[0-9]{6}\Z")
SCHEMA = "OFFICIAL_PAIR_SCHEDULE_TREND_AUDIT_V1"
SOURCE = "OFFICIAL_PAIR_SCHEDULE_CONTINUITY_AUDIT_V1"
PER_DAY_SLOTS = 156


def trend(repo, start_day, end_day, token, *, daily=inventory, as_of=None):
    """Re-read each complete UTC racing day from GitHub Actions; fail closed."""
    if not all(isinstance(x, str) and DAY.fullmatch(x)
               for x in (start_day, end_day)):
        raise ValueError("invalid UTC day range")
    if not isinstance(token, str) or not token:
        raise ValueError("authenticated GitHub read token required")
    try:
        start = datetime.strptime(start_day, "%Y%m%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_day, "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("invalid calendar day") from exc
    days = (end-start).days+1
    if not 1 <= days <= 14:
        raise ValueError("historical day range must span 1 to 14 days")
    now = as_of or datetime.now(timezone.utc)
    if (not isinstance(now, datetime) or now.utcoffset() != timedelta(0)):
        raise ValueError("observation must use timezone-aware UTC")
    now = now.astimezone(timezone.utc)
    if now < end + timedelta(hours=12, minutes=55):
        raise ValueError("last historical racing-day cron slot not yet elapsed")

    rows = []
    seen_global = set()
    counts = {"observed": 0, "in_hours": 0, "out_hours": 0,
              "success": 0, "failure": 0, "other": 0}
    for i in range(days):
        day = (start + timedelta(days=i)).strftime("%Y%m%d")
        one = daily(repo, day, token, as_of=now)
        if (not isinstance(one, dict)
                or one.get("schema") != SOURCE
                or one.get("utc_day") != day
                or one.get("expected_cron_assumption") != EXPECTED_CRON
                or one.get("workflow_path") != WORKFLOW_PATH
                or one.get("expected_slots_full_day") != PER_DAY_SLOTS
                or one.get("elapsed_nominal_slots_at_snapshot") != PER_DAY_SLOTS
                or one.get("future_nominal_slots") != 0
                or one.get("schedule_slot_identity_verified") is not False
                or one.get("missing_trigger_root_cause_verified") is not False
                or one.get("raw_official_source_receipts_verified") is not False
                or one.get("full_t12_source_certified") is not False):
            raise ValueError("incomplete, cross-day or overclaimed daily audit")
        recorded = one.get("runs")
        observed = one.get("observed_official_pair_schedule_runs")
        inside = one.get("observed_within_declared_cron_hours")
        outside = one.get("observed_outside_declared_cron_hours")
        successful = one.get("run_success")
        failed = one.get("run_failure")
        other = one.get("run_other_or_incomplete")
        if (not isinstance(recorded, list)
                or any(type(v) is not int or v < 0
                       for v in (observed, inside, outside, successful, failed, other))
                or observed != len(recorded)
                or observed != inside+outside
                or observed != successful+failed+other):
            raise ValueError("inconsistent schedule event counts")
        ids = []
        actual_inside = 0
        status = {"success": 0, "failure": 0, "other": 0}
        for row in recorded:
            if not isinstance(row, dict):
                raise ValueError("malformed scheduled workflow run")
            rid = row.get("run_id")
            if type(rid) is not int or rid <= 0 or rid in seen_global:
                raise ValueError("duplicate or invalid GitHub workflow run")
            seen_global.add(rid)
            ids.append(rid)
            created_raw = row.get("created_at_utc")
            if not isinstance(created_raw, str):
                raise ValueError("missing UTC creation time")
            try:
                created = datetime.fromisoformat(created_raw)
            except ValueError as exc:
                raise ValueError("invalid UTC run creation time") from exc
            if (created.utcoffset() != timedelta(0)
                    or created.date().strftime("%Y%m%d") != day
                    or created > now):
                raise ValueError("cross-day or future run creation")
            expected_inside = created.hour < 13
            if row.get("created_within_declared_cron_hours") is not expected_inside:
                raise ValueError("creation-hour classification disagreeing with UTC")
            actual_inside += int(expected_inside)
            code = row.get("conclusion")
            status[code if code in ("success", "failure") else "other"] += 1
        if (actual_inside != inside or status["success"] != successful
                or status["failure"] != failed or status["other"] != other):
            raise ValueError("event metadata and summary counts disagree")
        for k, v in (("observed", observed), ("in_hours", inside),
                     ("out_hours", outside), ("success", successful),
                     ("failure", failed), ("other", other)):
            counts[k] += v
        rows.append({
            "day_utc_jst": day,
            "nominal_configured_slots": PER_DAY_SLOTS,
            "observed_schedule_run_creations": observed,
            "created_in_declared_hours": inside,
            "created_outside_declared_hours": outside,
            "run_success": successful,
            "run_failure": failed,
            "run_other_or_incomplete": other,
            "run_ids": ids,
            "observation_rate_pct": round(observed/PER_DAY_SLOTS*100, 2),
            "raw_original_sources_verified": False,
        })
    nominal = days*PER_DAY_SLOTS
    return {
        "schema": SCHEMA,
        "repo": repo,
        "start_day_jst": start_day,
        "end_day_jst": end_day,
        "as_of_utc": now.isoformat(),
        "scope": "complete UTC 00:00-12:55 schedule window equals same JST racing day",
        "configured_nominal_slots": nominal,
        "observed_schedule_run_creations": counts["observed"],
        "created_in_declared_cron_hours": counts["in_hours"],
        "created_outside_declared_cron_hours": counts["out_hours"],
        "run_success": counts["success"],
        "run_failure": counts["failure"],
        "run_other_or_incomplete": counts["other"],
        "nominal_invocation_count_shortfall": max(0,nominal-counts["observed"]),
        "run_creation_to_nominal_slot_pct": round(100*counts["observed"]/nominal,2),
        "actual_slot_identity_verified": False,
        "missing_trigger_root_cause_verified": False,
        "absent_run_http_errors_proved": False,
        "official_source_originals_replayed": False,
        "formal": False,
        "t12_eligible": False,
        "accuracy_scoring_allowed": False,
        "formal_accuracy_denominator": None,
        "days": rows,
        "warning": (
            "Count shortfall is not proof that an exact cron slot was skipped, "
            "that GitHub scheduler failed, or that absent runs tried HTTP. "
            "Off-hours run creation may reflect delayed schedule events. "
            "A successful Actions run may contain no eligible races."
        )
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",required=True)
    p.add_argument("--start-day",required=True)
    p.add_argument("--end-day",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=trend(a.repo,a.start_day,a.end_day,os.environ.get("GITHUB_TOKEN"))
    target=Path(a.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                      encoding="utf-8")
    print("T12_MULTIDAY_SCHEDULE_TREND="+json.dumps(
        {k:v for k,v in result.items() if k!="days"},ensure_ascii=False))


if __name__=="__main__":
    main()
