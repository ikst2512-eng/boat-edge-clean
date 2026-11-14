"""Source-event handoff VETO ledger on pinned original forecasts; no dispatch.

A claim supplied from a different auditing owner is not the raw BOAT RACE
original or independent source/first-candidate receipt. A complete-looking
claim never authorizes freeze or scoring. This validates only claims, identity,
clock and coverage, and computes why the existing forecast cannot be promoted.
No result, network, source collector, timers, locks or production imports.
"""
import argparse
import json
import re
from collections import Counter
from datetime import timedelta
from pathlib import Path

from research.hole_pair_t12_polling_cadence_simulator import checked_rows, _clock

HEX64 = re.compile(r"[a-f0-9]{64}\Z")
FIELDS = frozenset({
    "race_code", "source_audit_report_sha256_claim",
    "source_last_original_received_jst_claim",
    "official_deadline_jst_claim",
    "racelist_original_sha256_claim",
    "beforeinfo_original_sha256_claim",
    "odds_original_sha256_claim",
    "exhibition_boats_claim", "distinct_trifecta_odds_claim",
    "github_source_archive_artifact_id_claim",
})


def _positive_int(x):
    return type(x) is int and x > 0


def _check_claim(item, code, day):
    """Check a separately supplied *claim*, without treating it as proof."""
    if type(item) is not dict or set(item) != FIELDS or item["race_code"] != code:
        raise ValueError("untrusted_or_cross_race_source_event")
    digest = item["source_audit_report_sha256_claim"]
    if type(digest) is not str or not HEX64.fullmatch(digest):
        raise ValueError("invalid_claimed_source_report_digest")
    for key in (
        "racelist_original_sha256_claim", "beforeinfo_original_sha256_claim",
        "odds_original_sha256_claim",
    ):
        value = item[key]
        if value is not None and (
            type(value) is not str or not HEX64.fullmatch(value)
        ):
            raise ValueError("invalid_claimed_original_component_digest")
    six, odds = item["exhibition_boats_claim"], item["distinct_trifecta_odds_claim"]
    if (type(six) is not int or not 0 <= six <= 6
            or type(odds) is not int or not 0 <= odds <= 120):
        raise ValueError("impossible_claimed_original_components")
    artifact = item["github_source_archive_artifact_id_claim"]
    if artifact is not None and not _positive_int(artifact):
        raise ValueError("invalid_claimed_remote_source_artifact_identity")
    received = _clock(item["source_last_original_received_jst_claim"], day)
    deadline = _clock(item["official_deadline_jst_claim"], day)
    return received, deadline


def audit(report, claimed_official_events=None):
    """Read-only per-race veto using an original report and zero trusted events."""
    day, reference, validated = checked_rows(report)
    originals = {row["race_code"]: row for row in report["rows"]}
    claims = {} if claimed_official_events is None else claimed_official_events
    if type(claims) is not dict or any(
        type(code) is not str or code not in originals for code in claims
    ):
        raise ValueError("orphan_or_invalid_official_event_claim")
    counters = Counter()
    rows = []
    for code, generation, cutoff in validated:
        row = originals[code]
        claimed = claims.get(code)
        blockers = [
            "no_independently_authenticated_official_source_original_bytes",
            "no_independent_official_source_server_receipt_and_cutoff",
            "current_forecast_original_consumption_unverified",
            "no_original_candidate_generated_after_verified_official_sources",
            "no_atomic_independent_first_candidate_acceptance",
        ]
        has_all_three = False
        source_chronology_claim = "no_official_source_handoff_claim"
        if claimed is None:
            blockers.extend([
                "same_race_official_racelist_original_missing",
                "same_race_six_boat_exhibition_missing",
                "same_race_distinct_120_way_odds_missing",
                "upstream_source_audit_report_missing",
            ])
            counters["no_handoff_claim"] += 1
        else:
            received, deadline = _check_claim(claimed, code, day)
            has_list = claimed["racelist_original_sha256_claim"] is not None
            has_before = (claimed["beforeinfo_original_sha256_claim"] is not None
                          and claimed["exhibition_boats_claim"] == 6)
            has_odds = (claimed["odds_original_sha256_claim"] is not None
                        and claimed["distinct_trifecta_odds_claim"] == 120)
            has_all_three = has_list and has_before and has_odds
            counters["supplied_unverified_source_claims"] += 1
            if not has_list:
                blockers.append("same_race_official_racelist_original_missing")
                counters["missing_racelist_claim"] += 1
            if not has_before:
                blockers.append("same_race_six_boat_exhibition_missing")
                counters["missing_exhibition_claim"] += 1
            if not has_odds:
                blockers.append("same_race_distinct_120_way_odds_missing")
                counters["missing_odds120_claim"] += 1
            if deadline != cutoff + timedelta(minutes=12):
                blockers.append("claimed_official_deadline_mismatches_original_forecast")
                counters["claimed_official_deadline_mismatch"] += 1
            if received >= cutoff:
                blockers.append("claimed_official_source_arrived_after_declared_t12")
                counters["claimed_source_not_before_declared_t12"] += 1
            if generation <= received:
                # Even IF all those supplied claims were authentic, the original
                # existing model could not have consumed a later source event.
                blockers.append("existing_forecast_generated_before_claimed_official_sources")
                counters["existing_forecast_predates_claimed_source"] += 1
                source_chronology_claim = "existing_forecast_generation_not_after_source_claim"
            else:
                source_chronology_claim = "generation_after_source_claim_not_authenticated"
            if has_all_three:
                counters["three_original_components_claimed_unverified"] += 1
        if row["beforeinfo_snapshot_status"] == "optional_beforeinfo_not_in_snapshot":
            blockers.append("current_forecast_has_no_beforeinfo_snapshot")
            counters["current_forecast_missing_beforeinfo"] += 1
        if reference >= cutoff:
            blockers.append("snapshot_reference_at_or_after_declared_t12")
            counters["declared_t12_window_elapsed_at_reference"] += 1
        else:
            counters["declared_t12_window_open_at_reference"] += 1
        rows.append({
            "race_code": code,
            "reference_jst": reference.isoformat(),
            "declared_t_minus_12_jst": cutoff.isoformat(),
            "declared_t12_open_at_reference": reference < cutoff,
            "official_handoff_claim_provided": claimed is not None,
            "all_three_official_original_components_claimed_only": has_all_three,
            "source_chronology_claim_classification": source_chronology_claim,
            "blocking_evidence_codes": sorted(set(blockers)),
            "dispatch_authorized": False,
            "official_original_bytes_independently_verified": False,
            "actual_model_official_original_consumption_verified": False,
            "independent_first_candidate_receipt_verified": False,
            "formal": False,
        })
    return {
        "schema": "HOLE_PAIR_OFFICIAL_EVENT_HANDOFF_VETO_NONFORMAL_V1",
        "source_main_commit": report["immutable_source_commit"],
        "day_jst": day,
        "original_source_races_examined": len(rows),
        "source_handoff_claims_supplied_unverified":
            counters["supplied_unverified_source_claims"],
        "official_handoff_claim_missing":
            counters["no_handoff_claim"],
        "claimed_three_original_components_unverified":
            counters["three_original_components_claimed_unverified"],
        "claimed_official_deadline_mismatch":
            counters["claimed_official_deadline_mismatch"],
        "existing_forecast_predates_claimed_source":
            counters["existing_forecast_predates_claimed_source"],
        "source_forecast_missing_beforeinfo":
            counters["current_forecast_missing_beforeinfo"],
        "declared_t12_window_elapsed_at_reference":
            counters["declared_t12_window_elapsed_at_reference"],
        "declared_t12_window_open_at_reference":
            counters["declared_t12_window_open_at_reference"],
        "authorized_dispatch_events": 0,
        "independent_official_source_originals_verified": 0,
        "independent_first_candidate_receipts_verified": 0,
        "official_full_day_schedule_verified": False,
        "prospective_pilot_formally_eligible": 0,
        "prospective_confirmation_formally_eligible": 0,
        "results_opened": False,
        "formal": False,
        "production_promotion_allowed": False,
        "rows": rows,
        "warning": (
            "This offline gate is a VETO on untrusted event handoffs. SHA256 "
            "strings, race IDs, supplied clocks and reported source completeness "
            "are unauthenticated claims. Never use this as a positive dispatch "
            "authorization, official T-12 certification or formal score."
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-report", required=True)
    p.add_argument("--upstream-handoff-claims",
                   help="Optional untrusted claims keyed by 12-digit race ID")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    def load(path):
        x = Path(path)
        if x.is_symlink() or not x.is_file() or x.stat().st_size > 3_000_000:
            raise ValueError("unsafe_source_event_file")
        return json.loads(x.read_text(encoding="utf-8"))
    result = audit(load(args.original_report),
                   load(args.upstream_handoff_claims)
                   if args.upstream_handoff_claims else None)
    dest = Path(args.output)
    if dest.is_symlink() or dest.exists():
        raise ValueError("will_not_overwrite_source_event_veto")
    dest.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)+"\n",
                    encoding="utf-8")
    print("REAL_ORIGINAL_SOURCE_EVENT_VETO", json.dumps({
        k: v for k, v in result.items() if k not in ("rows", "warning")
    }, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
