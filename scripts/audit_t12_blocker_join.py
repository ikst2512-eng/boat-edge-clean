"""Cross-check same-JST-day schedule and durable official-three-source inventory.

Both inputs must come from independent read-only GitHub audits. This is a
deficit inventory, NOT a promotion engine, a source-byte replay, or an
authoritative first-remote-acceptance / formal accuracy certificate.
"""
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

JST = timedelta(hours=9)
SCHEDULE = "OFFICIAL_PAIR_SCHEDULE_CONTINUITY_AUDIT_V1"
ARCHIVE = "T12_EXTERNAL_ARCHIVE_DAY_PRESENCE_AUDIT_V1"
OUTPUT = "T12_SAME_DAY_EVIDENCE_BLOCKER_JOIN_V1"


def join(schedule, archive):
    if not isinstance(schedule, dict) or not isinstance(archive, dict):
        raise ValueError("two independent audit objects required")
    if schedule.get("schema") != SCHEDULE or archive.get("schema") != ARCHIVE:
        raise ValueError("wrong audit schema")
    # Collector cron runs 00:00-12:55 UTC = 09:00-21:55 on SAME JST date.
    day = schedule.get("utc_day")
    if (not isinstance(day, str) or not isinstance(archive.get("day_jst"), str)
            or day != archive["day_jst"]):
        raise ValueError("mismatched UTC schedule and JST official source day")
    try:
        datetime.strptime(day, "%Y%m%d")
        seen = datetime.fromisoformat(schedule["as_of_utc"])
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("invalid independent schedule clock") from exc
    if seen.utcoffset() != timedelta(0):
        raise ValueError("schedule observation must be UTC")
    if seen.date().strftime("%Y%m%d") != day:
        raise ValueError("cross-day schedule snapshot")
    if (schedule.get("workflow_path")
            != ".github/workflows/research-live-preview-evidence.yml"
            or schedule.get("expected_cron_assumption") != "*/5 0-12 * * *"):
        raise ValueError("different workflow or cron assumption")
    elapsed = schedule.get("elapsed_nominal_slots_at_snapshot")
    observed = schedule.get("observed_official_pair_schedule_runs")
    in_hours = schedule.get("observed_within_declared_cron_hours")
    outside = schedule.get("observed_outside_declared_cron_hours")
    nominal = schedule.get("expected_slots_full_day")
    runs = schedule.get("runs")
    if (any(type(v) is not int or v < 0 for v in
            (elapsed, observed, in_hours, outside, nominal))
            or nominal != 156 or not 0 <= elapsed <= nominal
            or observed != in_hours + outside
            or not isinstance(runs, list) or len(runs) != observed
            or schedule.get("schedule_slot_identity_verified") is not False
            or schedule.get("raw_official_source_receipts_verified") is not False
            or schedule.get("full_t12_source_certified") is not False):
        raise ValueError("unreconciled or overclaimed schedule inventory")
    day_present = archive.get("day_directory_present")
    n_races = archive.get("race_directory_count")
    race_dirs = archive.get("race_directories")
    existing_days = archive.get("existing_day_directories")
    if (type(day_present) is not bool
            or type(n_races) is not int or n_races < 0
            or not isinstance(race_dirs, list) or len(race_dirs) != n_races
            or len(set(race_dirs)) != n_races
            or not isinstance(existing_days, list)
            or day_present != (day in existing_days)
            or (not day_present and n_races != 0)
            or archive.get("status") != (
                "persisted_race_directories_unverified"
                if day_present else "no_persisted_three_original_day_directory")
            or archive.get("evidence_branch") != "research-t12-external-evidence"
            or archive.get("originals_replayed") is not False
            or archive.get("github_initial_remote_receipt_verified") is not False
            or archive.get("full_t12_source_certified") is not False
            or archive.get("formal") is not False):
        raise ValueError("unreconciled or overclaimed three-original inventory")
    for race in race_dirs:
        if (not isinstance(race, str) or len(race) != 12
                or not race.isdigit() or not race.startswith(day)
                or int(race[8:10]) not in range(1, 25)
                or int(race[10:12]) not in range(1, 13)):
            raise ValueError("invalid race candidate directory")
    in_hours_deficit = max(0, elapsed - in_hours)
    report = {
        "schema": OUTPUT,
        "day_jst": day,
        "schedule_as_of_utc": seen.isoformat(),
        "official_pair_collector_schedule_runs_observed": observed,
        "official_pair_collector_schedule_runs_created_in_cron_hours": in_hours,
        "nominal_elapsed_five_minute_slots": elapsed,
        "invocation_count_deficit_in_cron_hours": in_hours_deficit,
        "invocation_count_coverage_pct": (
            round(100 * in_hours / elapsed, 2) if elapsed else None),
        "schedule_missing_trigger_cause_known": False,
        "per_slot_http_failures_inferred": False,
        "evidence_branch_commit_sha": archive.get("evidence_branch_commit_sha"),
        "durable_three_original_race_directories": n_races,
        "unverified_race_directory_names": sorted(race_dirs),
        "archived_original_bytes_verified_by_this_join": False,
        "candidate_status": ("no_durable_three_originals"
                             if n_races == 0 else
                             "durable_directories_exist_but_not_verified"),
        "missing_requirements": [
            *(["no_durable_official_three_original_race_directories"]
              if n_races == 0 else
              ["persisted_official_three_original_bytes_not_reaudited"]),
            "post_official_source_frozen_forecast_not_replayed",
            "independent_model_input_consumption_unverified",
            "independent_first_git_remote_receipt_unverified",
            "final_race_entry_not_independently_verified",
        ],
        "priority_owner": "source_collector_owner_1",
        "provenance_note": (
            "The schedule and Git tree are two different metadata observations. "
            "This join never infers HTTP outcomes, missing cron cause, raw source "
            "completeness or a formal prediction from metadata alone."),
        "new_formal_certifications": 0,
        "formal_accuracy_denominator": None,
        "formal": False,
        "t12_eligible": False,
        "accuracy_scoring_allowed": False,
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    schedule = json.loads(Path(args.schedule).read_text(encoding="utf-8"))
    archive = json.loads(Path(args.archive).read_text(encoding="utf-8"))
    result = join(schedule, archive)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("T12_SAME_DAY_EVIDENCE_BLOCKERS=" +
          json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
