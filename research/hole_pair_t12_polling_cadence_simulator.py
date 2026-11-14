"""Offline polling-cadence counterfactual on validated original main snapshot.

Never polls, schedules, freezes, signs, submits, retrieves results or certifies
official original source availability. All reception leads and safety margins
are EXPLICIT synthetic assumptions, even on real Git-original race cutoffs.
"""
import argparse
import json
import math
import re
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from research.hole_pair_real_main_snapshot_gate import SCHEMA as SOURCE_SCHEMA
from research.hole_pair_universe_coverage import race_day

JST = timezone(timedelta(hours=9))
DIGEST40 = re.compile(r"[a-f0-9]{40}\Z")
DIGEST64 = re.compile(r"[a-f0-9]{64}\Z")
CADENCES = (1, 2, 3, 5, 10, 15)
REQUIRED_REPORT = frozenset({
    "schema", "capture_day_jst", "immutable_source_commit",
    "reference_clock_jst", "original_main_forecast_ids_examined",
    "original_git_blob_sha1_verified_count", "original_source_sha256_computed_count",
    "optional_beforeinfo_absent_from_forecast",
    "beforeinfo_field_not_officially_verified",
    "locally_generated_before_declared_t12",
    "not_generated_before_declared_t12",
    "declared_t12_still_future_at_reference",
    "declared_t12_elapsed_at_reference",
    "same_race_official_t12_origins_authenticated",
    "first_independent_signed_candidate_receipts_authenticated",
    "whole_day_official_schedule_verified",
    "prospective_pilot_formally_eligible",
    "prospective_confirmation_formally_eligible",
    "formal", "production_promotion_allowed", "result_files_read",
    "rows", "warning",
})
REQUIRED_ROW = frozenset({
    "race_code", "source_git_blob_sha1",
    "source_sha256_from_verified_git_bytes", "local_generated_jst_claim",
    "local_declared_deadline_jst", "local_declared_t_minus_12_jst",
    "beforeinfo_snapshot_status", "generated_before_local_declared_t12",
    "declared_t12_open_at_reference",
    "official_complete_six_boat_beforeinfo_verified",
    "official_complete_120_way_odds_verified",
    "independent_first_candidate_receipt_verified", "formal_candidate",
})


def _clock(raw, day):
    if type(raw) is not str:
        raise ValueError("missing_or_nonstring_jst_clock")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as ex:
        raise ValueError("untrusted_jst_clock") from ex
    if dt.utcoffset() != timedelta(hours=9) or dt.strftime("%Y%m%d") != day:
        raise ValueError("different_day_or_wrong_jst_clock")
    return dt


def checked_rows(report):
    """Reject self-promoting, inconsistent or selectively omitted audit rows."""
    if (type(report) is not dict or set(report) != REQUIRED_REPORT
            or report.get("schema") != SOURCE_SCHEMA):
        raise ValueError("untrusted_original_snapshot_report_schema")
    day = report["capture_day_jst"]
    if (type(day) is not str or not re.fullmatch(r"20\d{6}", day)
            or day < "20261109"):
        raise ValueError("untrusted_snapshot_day")
    sha = report["immutable_source_commit"]
    if type(sha) is not str or not DIGEST40.fullmatch(sha):
        raise ValueError("untrusted_immutable_main_commit")
    rows = report["rows"]
    if type(rows) is not list or len(rows) > 500:
        raise ValueError("untrusted_snapshot_rows")
    if (any(type(report[k]) is not int or report[k] != len(rows)
            for k in ("original_main_forecast_ids_examined",
                      "original_git_blob_sha1_verified_count",
                      "original_source_sha256_computed_count"))):
        raise ValueError("inconsistent_original_source_hash_roster")
    if (any(report[k] is not False for k in (
            "formal", "production_promotion_allowed", "result_files_read",
            "whole_day_official_schedule_verified"))
            or any(report[k] != 0 for k in (
                "same_race_official_t12_origins_authenticated",
                "first_independent_signed_candidate_receipts_authenticated",
                "prospective_pilot_formally_eligible",
                "prospective_confirmation_formally_eligible"))):
        raise ValueError("forged_original_evidence_or_formal_admission")
    reference = _clock(report["reference_clock_jst"], day)
    counts = dict(present=0, absent=0, before=0, not_before=0, open=0, elapsed=0)
    parsed = []
    previous = None
    for row in rows:
        if type(row) is not dict or set(row) != REQUIRED_ROW:
            raise ValueError("unknown_or_missing_original_row_fields")
        code = race_day(row["race_code"], day)
        if previous is not None and code <= previous:
            raise ValueError("reordered_or_duplicate_original_race_code")
        previous = code
        for name, digest_re in (
            ("source_git_blob_sha1", DIGEST40),
            ("source_sha256_from_verified_git_bytes", DIGEST64),
        ):
            if type(row[name]) is not str or not digest_re.fullmatch(row[name]):
                raise ValueError("untrusted_original_digest_format")
        deadline = _clock(row["local_declared_deadline_jst"], day)
        generated = _clock(row["local_generated_jst_claim"], day)
        cutoff = deadline - timedelta(minutes=12)
        if cutoff.strftime("%Y%m%d") != day:
            raise ValueError("declared_cutoff_outside_race_day")
        if row["local_declared_t_minus_12_jst"] != cutoff.isoformat():
            raise ValueError("declared_t12_differs_from_original_deadline")
        before, open_ = generated < cutoff, reference < cutoff
        if (type(row["generated_before_local_declared_t12"]) is not bool
                or row["generated_before_local_declared_t12"] != before
                or type(row["declared_t12_open_at_reference"]) is not bool
                or row["declared_t12_open_at_reference"] != open_):
            raise ValueError("falsified_source_clock_classification")
        if any(row[k] is not False for k in (
            "official_complete_six_boat_beforeinfo_verified",
            "official_complete_120_way_odds_verified",
            "independent_first_candidate_receipt_verified", "formal_candidate",
        )):
            raise ValueError("forged_row_official_source_or_candidate_receipt")
        field = row["beforeinfo_snapshot_status"]
        if field not in (
            "optional_beforeinfo_not_in_snapshot",
            "beforeinfo_field_present_or_unknown_not_officially_verified",
        ):
            raise ValueError("untrusted_beforeinfo_field_status")
        counts["absent" if field.startswith("optional_") else "present"] += 1
        counts["before" if before else "not_before"] += 1
        counts["open" if open_ else "elapsed"] += 1
        parsed.append((code, generated, cutoff))
    required_counts = {
        "optional_beforeinfo_absent_from_forecast": counts["absent"],
        "beforeinfo_field_not_officially_verified": counts["present"],
        "locally_generated_before_declared_t12": counts["before"],
        "not_generated_before_declared_t12": counts["not_before"],
        "declared_t12_still_future_at_reference": counts["open"],
        "declared_t12_elapsed_at_reference": counts["elapsed"],
    }
    for key, expected in required_counts.items():
        if type(report[key]) is not int or report[key] != expected:
            raise ValueError("original_snapshot_aggregate_row_mismatch")
    return day, reference, parsed


def simulate(report, *, assumed_source_ready_lead_seconds=180,
             assumed_processing_reserve_seconds=30,
             first_git_source_sighting_hint_jst=None,
             cadence_minutes=CADENCES, poll_phase_offset_seconds=0):
    """Counterfactual dispatch opportunities ONLY; never produces tickets."""
    day, reference, rows = checked_rows(report)
    if (type(assumed_source_ready_lead_seconds) is not int
            or type(assumed_processing_reserve_seconds) is not int
            or not 0 < assumed_processing_reserve_seconds <
                assumed_source_ready_lead_seconds <= 3600):
        raise ValueError("untrusted_source_lead_or_processing_reserve")
    if (type(cadence_minutes) not in (tuple, list)
            or not 1 <= len(cadence_minutes) <= 24
            or any(type(n) is not int or not 1 <= n <= 120 for n in cadence_minutes)
            or list(cadence_minutes) != sorted(set(cadence_minutes))):
        raise ValueError("invalid_simulation_cadence_grid")
    if (type(poll_phase_offset_seconds) is not int
            or not 0 <= poll_phase_offset_seconds < 60):
        raise ValueError("invalid_untrusted_synthetic_poll_phase")
    if first_git_source_sighting_hint_jst is None:
        raise ValueError("missing_untrusted_initial_git_sighting_hint")
    hint = _clock(first_git_source_sighting_hint_jst, day)
    start = (datetime.combine(reference.date(), time(0, 0), JST)
             + timedelta(seconds=poll_phase_offset_seconds))
    scenarios = []
    for minutes in cadence_minutes:
        period = minutes * 60
        hits, misses, codes = 0, 0, []
        for code, generated, cutoff in rows:
            # Synthetic official-source availability: cutoff minus input lead.
            # This is NOT a statement that BOAT RACE data were ever ready.
            ready = cutoff - timedelta(seconds=assumed_source_ready_lead_seconds)
            ready = max(ready, generated, hint)
            end = cutoff - timedelta(seconds=assumed_processing_reserve_seconds)
            if end < ready:
                misses += 1
                continue
            first_tick = math.ceil((ready-start).total_seconds()/period)
            possible = start + timedelta(seconds=first_tick*period)
            if possible <= end:
                hits += 1
                codes.append(code)
            else:
                misses += 1
        scenarios.append({
            "hypothetical_poll_period_minutes": minutes,
            "clock_only_races_with_at_least_one_hypothetical_slot": hits,
            "clock_only_races_without_slot": misses,
            "clock_only_race_codes": codes,
            "official_input_actual_arrival_verified": False,
            "independent_remote_first_acceptance_verified": False,
            "formally_eligible": 0,
        })
    return {
        "schema": "HOLE_PAIR_T12_POLLING_CADENCE_COUNTERFACTUAL_V1",
        "method": "midnight_JST_aligned_hypothetical_polling",
        "source_commit": report["immutable_source_commit"],
        "hypothetical_poll_phase_offset_seconds": poll_phase_offset_seconds,
        "day_jst": day,
        "original_races_from_verified_git_snapshot": len(rows),
        "original_report_reference_jst": reference.isoformat(),
        "first_git_source_sighting_hint_jst_unverified": hint.isoformat(),
        "assumed_official_input_ready_seconds_before_declared_t12_NOT_OBSERVED":
            assumed_source_ready_lead_seconds,
        "assumed_processing_and_network_reserve_seconds_NOT_MEASURED":
            assumed_processing_reserve_seconds,
        "scenarios": scenarios,
        "actual_workflow_or_candidates_dispatched": False,
        "official_source_arrival_authenticated": False,
        "schedule_day_universe_verified": False,
        "first_independent_receipt_verified": False,
        "prospective_pilot_formally_eligible": 0,
        "prospective_confirmation_formally_eligible": 0,
        "formal": False,
        "production_promotion_allowed": False,
        "results_opened": False,
        "warning": (
            "This is a CLOCK-ONLY COUNTERFACTUAL, not a valid schedule design "
            "or observed coverage. The official-source-ready lead and processing "
            "reserve are hypothetical, source Git sighting is not independently "
            "authenticated, and no signed first candidate acceptance exists. "
            "Never backfill or use simulated slots as prospective observations."
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-report", required=True)
    p.add_argument("--source-lead-seconds", type=int, default=180)
    p.add_argument("--processing-reserve-seconds", type=int, default=30)
    p.add_argument("--poll-phase-offset-seconds", type=int, default=0)
    p.add_argument("--first-git-source-sighting-hint-jst", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    source = Path(args.original_report)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 3_000_000:
        raise ValueError("untrusted_original_source_audit_json")
    report = json.loads(source.read_text(encoding="utf-8"))
    result = simulate(
        report,
        assumed_source_ready_lead_seconds=args.source_lead_seconds,
        assumed_processing_reserve_seconds=args.processing_reserve_seconds,
        poll_phase_offset_seconds=args.poll_phase_offset_seconds,
        first_git_source_sighting_hint_jst=args.first_git_source_sighting_hint_jst,
    )
    dest = Path(args.output)
    if dest.is_symlink() or dest.exists():
        raise ValueError("will_not_overwrite_simulation_output")
    dest.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)+"\n",
                    encoding="utf-8")
    print("NONFORMAL_CADENCE_SIMULATION", json.dumps({
        "input_race_count": result["original_races_from_verified_git_snapshot"],
        "cadences": [{
            "min":x["hypothetical_poll_period_minutes"],
            "clock_only":x["clock_only_races_with_at_least_one_hypothetical_slot"],
        } for x in result["scenarios"]],
        "formal": False, "prospective_pilot_formally_eligible": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
