#!/usr/bin/env python3
"""Research-only official K 92-day historical boat slots vs realized course comparison.

Uses the existing primary K LZH SHA-frozen reader and the existing chronological
athlete residual model. No duplicated K parser and no access to forecast code.
Boat-number identities are theoretically pre-race known, but official T-12
racelist HTTP receipt and actual race-entry forecasts remain unverified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__:
    from .research_official_k_c2_athlete_chronological_holdout import (
        official_rows, losses_for_target, FIELDS
    )
else:
    from research_official_k_c2_athlete_chronological_holdout import (
        official_rows, losses_for_target, FIELDS
    )

EXPECTED_COUNTS = {
    "eligible": 13815,
    "train": 9241,
    "holdout": 4574,
    "boat1_vs_actual_c1_mismatch": 116,
    "boat2_vs_actual_c2_mismatch": 706,
}
REFERENCE_ACTUAL_C1_BRIER = 0.24138865
REFERENCE_BOAT1_BRIER = 0.24156180
REFERENCE_BOAT2_BRIER = 0.24796172

def analyze(path: Path) -> dict:
    rows, sha, daily_sha = official_rows(path)
    train = [r for r in rows if r["month"] in ("08","09")]
    test = [r for r in rows if r["month"] == "10"]
    counts = {
        "eligible": len(rows),
        "train": len(train),
        "holdout": len(test),
        "boat1_vs_actual_c1_mismatch": sum(
            r["boat1_registration"] != r["c1_registration"] for r in rows
        ),
        "boat2_vs_actual_c2_mismatch": sum(
            r["boat2_registration"] != r["c2_registration"] for r in rows
        ),
    }
    if counts != EXPECTED_COUNTS:
        raise ValueError("pinned_cohort_or_course_entry_mismatch:" + str(counts))
    # Venue-specific course-change risk. Denominator is the *same fixed cohort*,
    # not all races or all beforeinfo snapshots. No per-race or athlete disclosure.
    venue_mismatch = {
        f"{venue:02d}": {
            "eligible": 0,
            "boat1_mismatch_count": 0,
            "boat2_mismatch_count": 0,
            "both_mismatch_count": 0,
        } for venue in range(1,25)
    }
    for row in rows:
        stat = venue_mismatch[row["venue"]]
        n1 = row["boat1_registration"] != row["c1_registration"]
        n2 = row["boat2_registration"] != row["c2_registration"]
        stat["eligible"] += 1
        stat["boat1_mismatch_count"] += int(n1)
        stat["boat2_mismatch_count"] += int(n2)
        stat["both_mismatch_count"] += int(n1 and n2)
    if any(v["eligible"] <= 0 for v in venue_mismatch.values()):
        raise ValueError("venue_not_covered")
    if sum(v["eligible"] for v in venue_mismatch.values()) != counts["eligible"]:
        raise ValueError("per_venue_denominator_drift")
    if (sum(v["boat1_mismatch_count"] for v in venue_mismatch.values())
            != counts["boat1_vs_actual_c1_mismatch"]
            or sum(v["boat2_mismatch_count"] for v in venue_mismatch.values())
            != counts["boat2_vs_actual_c2_mismatch"]):
        raise ValueError("per_venue_mismatch_count_drift")
    for stat in venue_mismatch.values():
        stat["boat1_mismatch_percent"] = round(
            100 * stat["boat1_mismatch_count"] / stat["eligible"], 4)
        stat["boat2_mismatch_percent"] = round(
            100 * stat["boat2_mismatch_count"] / stat["eligible"], 4)
    results = {}
    for target in FIELDS:
        actual = losses_for_target(train, test, target, identity_role="actual_course")
        boat = losses_for_target(train, test, target, identity_role="boat_number")
        results[target] = {
            "actual_course_hindsight": actual,
            "boat_number_identity": boat,
            "comparisons_vs_same_venue_baseline": {
                "actual_c1_athlete_brier_delta":
                    actual["delta_vs_venue"]["venue_plus_c1"]["brier"],
                "boat1_athlete_brier_delta":
                    boat["delta_vs_venue"]["venue_plus_c1"]["brier"],
                "boat2_athlete_brier_delta":
                    boat["delta_vs_venue"]["venue_plus_c2"]["brier"],
                "boat1_plus_boat2_brier_delta":
                    boat["delta_vs_venue"]["venue_plus_both"]["brier"],
            }
        }
    # This independently checked local historical result is a regression
    # invariant, never a prospective accuracy/production threshold.
    if (results["c1_escape"]["actual_course_hindsight"]["models"]
        ["venue_plus_c1"]["brier"] != REFERENCE_ACTUAL_C1_BRIER
        or results["c1_escape"]["boat_number_identity"]["models"]
        ["venue_plus_c1"]["brier"] != REFERENCE_BOAT1_BRIER
        or results["c1_escape"]["boat_number_identity"]["models"]
        ["venue_plus_c2"]["brier"] != REFERENCE_BOAT2_BRIER):
        raise ValueError("independent_local_historical_reference_mismatch")

    return {
        "schema": "BOAT_EDGE_OFFICIAL_K_202608_202610_BOATSLOT_VS_ACTUAL_COURSE_RESEARCH_V1",
        "class": "postrace_official_K_historical_time_holdout_not_T12",
        "period": "2026-08-01/2026-10-31",
        "train_period": "2026-08-01/2026-09-30",
        "test_period": "2026-10-01/2026-10-31",
        "source_artifact_id": 13607470249,
        "source_original_ZIP_sha256": sha,
        "source_daily_K_hashes_checked": len(daily_sha),
        "counts": counts,
        "per_venue_course_identity_mismatch": venue_mismatch,
        "design": {
            "actual_course_registrations_are_result_known": True,
            "boat_number_registrations_are_pre_race_observable_in_principle": True,
            "boat_number_registrations_independently_archived_pre_T12": False,
            "event_entry_and_eligibility_still_hindsight_selected": True,
            "historical_model_frozen_externally_before_holdout": False,
            "outcome_values_used_to_train_only_aug_sep": True,
            "venue_pseudo_n": 40,
            "athlete_residual_pseudo_n": 40,
            "paired_bootstrap_days": 31,
            "paired_bootstrap_reps": 4000,
            "bootstrap_seed": 1692,
            "unseen_athlete_residual": 0,
        },
        "outcomes": results,
        "official_racelist_T12_evidence_complete": False,
        "forecast_improvement_formally_proven": False,
        "production_feature_approved": False,
        "main_changed": False,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-zip", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.artifact_zip)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = result["outcomes"]["c1_escape"]
    print(json.dumps({
        "counts": result["counts"],
        "C1_escape_venue": summary["boat_number_identity"]["models"]["venue"]["brier"],
        "C1_escape_actual_1C": summary["actual_course_hindsight"]["models"]["venue_plus_c1"]["brier"],
        "C1_escape_boat1": summary["boat_number_identity"]["models"]["venue_plus_c1"]["brier"],
        "C1_escape_boat2": summary["boat_number_identity"]["models"]["venue_plus_c2"]["brier"],
        "official_T12_eligible": False
    }, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
