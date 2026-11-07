"""Research-only venue-mix audit for historical vs post-race November wind cohorts.

Never imports a forecast model or treats result weather as predeadline evidence.
The inputs are descriptive counts. Output values are NOT causal wind effects.
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "docs" / "research"
BANDS = ("0-2m", "3-4m", "5m+")


def wilson_95(success, n):
    if not n:
        return None
    z = 1.959963984540054
    p = success / n
    den = 1 + z*z/n
    mid = (p + z*z/(2*n)) / den
    spread = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return [round(100*(mid-spread), 2), round(100*(mid+spread), 2)]


def _valid_counts(data):
    if data.get("approved_for_prediction") is not False or data.get("post_race_weather") is not True:
        raise ValueError("holdout_is_not_confirmed_research_only")
    if data.get("official_result_reconciled") is not False:
        raise ValueError("holdout_cannot_claim_official_reconciliation")
    if data["validation"]["input_rows"] != (
        data["validation"]["accepted"] + data["validation"]["excluded"]
    ):
        raise ValueError("invalid_exclusion_total")
    if set(data["venues"]) != {f"{i:02d}" for i in range(1, 25)}:
        raise ValueError("incomplete_24_venues")
    for band in BANDS:
        summary = data["national"][band]
        n = summary["n"]
        if any(x < 0 for x in summary["winner_course_counts"]):
            raise ValueError("negative_course_count")
        if len(summary["winner_course_counts"]) != 6:
            raise ValueError("missing_six_courses")
        if sum(summary["winner_course_counts"]) != n:
            raise ValueError("national_course_reconciliation_failed")
        if sum(summary["winning_method_counts"].values()) != n:
            raise ValueError("national_method_reconciliation_failed")
        if sum(summary["wind_direction_raw_counts"].values()) != n:
            raise ValueError("national_direction_reconciliation_failed")
        if sum(data["venues"][v][band]["n"] for v in data["venues"]) != n:
            raise ValueError("venue_band_reconciliation_failed")
        for v in data["venues"]:
            s = data["venues"][v][band]
            if len(s["winner_course_counts"]) != 6 or sum(s["winner_course_counts"]) != s["n"]:
                raise ValueError("venue_course_reconciliation_failed")
            if sum(s["winning_method_counts"].values()) != s["n"]:
                raise ValueError("venue_method_reconciliation_failed")
            if sum(s["wind_direction_raw_counts"].values()) != s["n"]:
                raise ValueError("venue_direction_reconciliation_failed")
    if sum(data["national"][b]["n"] for b in BANDS) != data["validation"]["accepted"]:
        raise ValueError("accepted_race_count_mismatch")


def analyze(historical, holdout, national_min_n=100, venue_min_n=30):
    """Reweight old per-venue rates to each holdout band venue mix; do not fit."""
    if national_min_n < 1 or venue_min_n < 1:
        raise ValueError("minimum_n_must_be_positive")
    _valid_counts(holdout)
    if historical.get("official_binary_reconciliation") is not False:
        raise ValueError("historical_official_reconciliation_unverified")
    old = {v["code"]: v for v in historical["venues"]}
    if set(old) != set(holdout["venues"]):
        raise ValueError("historical_venue_mismatch")
    if historical.get("period") != "2026-08-01 to 2026-10-31":
        raise ValueError("historical_period_not_fixed")
    if holdout.get("period") != "2026-11-01..2026-11-05":
        raise ValueError("holdout_period_not_fixed")
    result = {}
    unrounded_baselines = {}
    for band in BANDS:
        s = holdout["national"][band]
        n = s["n"]
        if not n:
            result[band] = {"n": 0, "status": "no_observations"}
            continue
        observed = 100 * s["winner_course_counts"][0] / n
        old_calm_expected = 0.0
        old_same_band_expected = 0.0
        supported = True
        for venue, v in holdout["venues"].items():
            weight = v[band]["n"]
            if not weight:
                continue
            history = old[venue]["wind_bands"]
            calm, sample = history["0-2m"], history[band]
            if calm["n"] <= 0 or sample["n"] <= 0:
                supported = False
                break
            old_calm_expected += weight * calm["actual_course1_first_pct"] / n
            old_same_band_expected += weight * sample["actual_course1_first_pct"] / n
        eligible_venues = [
            venue for venue, v in holdout["venues"].items()
            if v[band]["n"] >= venue_min_n
            and v["0-2m"]["n"] >= venue_min_n
        ]
        if supported:
            unrounded_baselines[band] = old_calm_expected
        result[band] = {
            "n": n,
            "winner_course1_count": s["winner_course_counts"][0],
            "observed_course1_pct": round(observed, 2),
            "observed_ci95_pct": wilson_95(s["winner_course_counts"][0], n),
            "national_descriptive_min_n_met": n >= national_min_n,
            "holdout_venue_comparison_eligible": eligible_venues,
            "old_calm_pct_reweighted_to_holdout_venue_mix": (
                round(old_calm_expected, 2) if supported else None),
            "old_same_band_pct_reweighted_to_holdout_venue_mix": (
                round(old_same_band_expected, 2) if supported else None),
            "old_same_band_and_calm_coverage_complete": supported,
        }
    baseline = result["0-2m"]
    for band in BANDS[1:]:
        target = result[band]
        if target["n"] and baseline["n"]:
            target["raw_vs_holdout_calm_pt"] = round(
                100 * holdout["national"][band]["winner_course_counts"][0] / target["n"]
                - 100 * holdout["national"]["0-2m"]["winner_course_counts"][0] / baseline["n"], 2)
            if band in unrounded_baselines and "0-2m" in unrounded_baselines:
                target["venue_composition_only_shift_pt"] = round(
                    unrounded_baselines[band] - unrounded_baselines["0-2m"], 2)
                target["remainder_not_attributable_to_wind_pt"] = round(
                    target["raw_vs_holdout_calm_pt"]
                    - target["venue_composition_only_shift_pt"], 2)
    return {
        "schema": "VENUE_WIND_HOLDOUT_VENUE_MIX_AUDIT_V1",
        "research_only": True,
        "predeadline_input_approved": False,
        "forecast_improvement_proven": False,
        "historical_window": historical["period"],
        "holdout_window": holdout["period"],
        "historical_percentages_rounded_to_0_01": True,
        "groups": result,
        "limitations": [
            "Outcome weather is recorded after the race; never use as T-12 input.",
            "Venue-mix reweighting controls ONLY venue composition, not race/athlete/season/tide/wind direction.",
            "Differences and the remainder are descriptive, NOT estimates of causal wind effects.",
            "Small or empty samples cannot qualify as prediction improvements.",
            "Historical rates were archived rounded to 0.01 percentage points.",
            "No Top-N, probability calibration or independent official result reconciliation."
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, default=ROOT / "venue_wind_202608_202610_24venues_research_only.json")
    parser.add_argument("--holdout", type=Path, default=ROOT / "venue_wind_nov01_05_out_of_period_research_only.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    old = json.loads(args.history.read_text(encoding="utf-8"))
    new = json.loads(args.holdout.read_text(encoding="utf-8"))
    content = json.dumps(analyze(old, new), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
