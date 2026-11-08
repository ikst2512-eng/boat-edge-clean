"""Historical V2 displayed estimated full-ticket coverage vs observed coverage.

STRICT reference-only calibration audit of immutable original Nov5-8 forecasts.
One exact CSV snapshot per day, independently persisted result file comparisons,
and manually reviewed official postrace non-scoreable exclusions are required.
This is not T-12 proof, an independently first-received candidate, a new
probability model, prospective testing, ROI or production scoring.
"""
import argparse
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

from collect_clean_results import JST, build_records, confirmed_record_is_usable
from four_mode_archive_api import archived_four_modes
from four_mode_nov05_08_daily_reference_audit import ROOT, DAYS, MODES, BUDGETS, VERSION
from four_mode_result_raw_csv_audit import evaluate, annotate_official_non_scored


def _estimated_coverage(original, mode):
    """Validate the old, *displayed* coverage estimate, never recompute it."""
    value = original["modes"][mode].get("estimated_coverage_pct")
    if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError("missing_or_invalid_original_estimated_coverage:" + mode)
    tickets = original["modes"][mode]["tickets"]
    if not isinstance(tickets, list) or len(tickets) != BUDGETS[mode]:
        raise ValueError("original_ticket_budget_mismatch:" + mode)
    combos = [x["combo"] for x in tickets]
    if len(set(combos)) != len(combos):
        raise ValueError("duplicate_original_ticket:" + mode)
    return value / 100.0, combos


def _new_stats():
    return {"races": 0, "estimated_hits_sum": 0.0, "estimated_square_sum": 0.0,
            "estimated_min": None, "estimated_max": None, "estimated_distinct": set(),
            "estimated_outcomes": [],
            "actual_full_ticket_hits": 0, "squared_error_sum": 0.0,
            "saved_results": 0, "public_only_results": 0}


def _accumulate(stats, probability, full_hit, result_kind):
    stats["races"] += 1
    if (not isinstance(probability, (int, float)) or isinstance(probability, bool)
            or not math.isfinite(probability) or not 0 <= probability <= 1):
        raise ValueError("untrusted_estimated_probability")
    stats["estimated_hits_sum"] += probability
    stats["estimated_square_sum"] += probability ** 2
    stats["estimated_min"] = (probability if stats["estimated_min"] is None
                               else min(stats["estimated_min"], probability))
    stats["estimated_max"] = (probability if stats["estimated_max"] is None
                               else max(stats["estimated_max"], probability))
    stats["estimated_distinct"].add(round(probability * 100, 4))
    stats["estimated_outcomes"].append((probability, int(full_hit)))
    stats["actual_full_ticket_hits"] += int(full_hit)
    stats["squared_error_sum"] += (probability - int(full_hit)) ** 2
    stats["saved_results"] += int(result_kind == "persisted")
    stats["public_only_results"] += int(result_kind == "public_unarchived")


def _descriptive_auc(rows):
    """Tie-aware ranking AUC for historical full-ticket hit vs miss, never a future guarantee."""
    if not isinstance(rows, list) or any(
        not isinstance(pair, tuple) or len(pair) != 2 or
        type(pair[1]) is not int or pair[1] not in (0, 1) or
        type(pair[0]) not in (int, float) or not math.isfinite(pair[0]) or
        not 0 <= pair[0] <= 1 for pair in rows
    ):
        raise ValueError("invalid_auc_histogram")
    positives = sum(y for _, y in rows)
    negatives = len(rows) - positives
    if not positives or not negatives:
        return None
    ordered = sorted(rows)
    negative_below = 0
    wins = 0.0
    i = 0
    while i < len(ordered):
        j = i
        score = ordered[i][0]
        count_positive = 0
        while j < len(ordered) and ordered[j][0] == score:
            count_positive += ordered[j][1]
            j += 1
        count_negative = j - i - count_positive
        wins += count_positive * negative_below + 0.5 * count_positive * count_negative
        negative_below += count_negative
        i = j
    auc = wins / (positives * negatives)
    if not 0 <= auc <= 1:
        raise ValueError("auc_out_of_bounds")
    return round(auc, 5)


def _summarize(stats):
    n = stats["races"]
    mean = stats["estimated_hits_sum"] / n if n else None
    variance = max(0.0, stats["estimated_square_sum"] / n - mean ** 2) if n else None
    if n and (stats["estimated_min"] is None or stats["estimated_max"] is None
              or len(stats["estimated_distinct"]) == 0 or
              len(stats["estimated_outcomes"]) != n):
        raise ValueError("estimated_spread_missing")
    return {
        "races": n,
        "estimated_full_list_hit_rate_pct": round(100 * stats["estimated_hits_sum"] / n, 2) if n else None,
        "estimated_full_list_min_pct": round(100 * stats["estimated_min"], 2) if n else None,
        "estimated_full_list_max_pct": round(100 * stats["estimated_max"], 2) if n else None,
        "estimated_full_list_population_stddev_pp": round(100 * math.sqrt(variance), 4) if n else None,
        "distinct_original_estimated_pct_values": len(stats["estimated_distinct"]),
        "descriptive_original_estimate_hit_discrimination_auc": _descriptive_auc(stats["estimated_outcomes"]),
        "observed_full_list_hit_rate_pct": round(100 * stats["actual_full_ticket_hits"] / n, 2) if n else None,
        "observed_minus_estimated_percentage_points": round(
            100 * (stats["actual_full_ticket_hits"] - stats["estimated_hits_sum"]) / n, 2) if n else None,
        "estimated_hit_count_sum": round(stats["estimated_hits_sum"], 3),
        "observed_hit_count": stats["actual_full_ticket_hits"],
        "mean_squared_error_brier_descriptive": round(stats["squared_error_sum"] / n, 6) if n else None,
        "persisted_result_count": stats["saved_results"],
        "public_only_result_count": stats["public_only_results"],
    }


def _leave_one_day_out_auc(day_stats):
    """Stress-test historical original estimates with each calendar day omitted.

    Not cross-validated training, a confidence interval, or prospective skill.
    """
    if type(day_stats) is not dict or set(day_stats) != set(DAYS):
        raise ValueError("invalid_leave_one_day_out_day_roster")
    for day in DAYS:
        if type(day_stats[day]) is not dict or set(day_stats[day]) != set(MODES):
            raise ValueError("invalid_leave_one_day_out_modes")
        for mode in MODES:
            stats = day_stats[day][mode]
            if (type(stats) is not dict or type(stats.get("estimated_outcomes")) is not list
                    or len(stats["estimated_outcomes"]) != stats.get("races")):
                raise ValueError("incomplete_leave_one_day_out_rows")
    by_mode = {}
    for mode in MODES:
        rows = {}
        aucs = []
        for excluded in DAYS:
            included = [day for day in DAYS if day != excluded]
            outcomes = [item for day in included
                        for item in day_stats[day][mode]["estimated_outcomes"]]
            positive = sum(hit for _, hit in outcomes)
            auc = _descriptive_auc(outcomes)
            rows[excluded] = {
                "excluded_day": excluded,
                "included_days": included,
                "included_races": len(outcomes),
                "observed_full_list_hits": positive,
                "observed_full_list_misses": len(outcomes) - positive,
                "descriptive_original_estimate_hit_discrimination_auc": auc,
            }
            if auc is not None:
                aucs.append(auc)
        by_mode[mode] = {
            "excluding_each_day": rows,
            "evaluable_day_exclusions": len(aucs),
            "minimum_three_day_auc": min(aucs) if aucs else None,
            "maximum_three_day_auc": max(aucs) if aucs else None,
            "range_across_omitted_days": (round(max(aucs) - min(aucs), 5)
                                           if aucs else None),
            "not_prospective_or_cross_validated_model_training": True,
        }
    return by_mode


def audit(root, raw_by_day, official_reference, observed_at=None):
    """Fail closed unless every historical original has a verified outcome or approved non-scoreable exclusion."""
    root = Path(root)
    observed_at = observed_at or datetime.now(JST)
    raw_status = evaluate(root, raw_by_day, observed_at=observed_at)
    official = annotate_official_non_scored(raw_status, official_reference)
    if (raw_status["totals"].get("saved_result_rows_disagree_or_not_present", 0) != 0
            or raw_status["totals"].get("saved_result_rows_matched_current_csv", 0)
               != raw_status["frozen_original_result_reference"]["evaluated"]):
        raise ValueError("archived_result_conflicts_current_raw")
    non_scoreable = set(official["reviewed_non_scored_races"])
    if len(non_scoreable) != official["non_scored_total"]:
        raise ValueError("non_scoreable_duplicate")
    by_day = {}
    daily_raw_stats = {}
    pooled = {m: _new_stats() for m in MODES}
    all_codes = set()
    kinds = Counter()
    for day in DAYS:
        current = build_records(day, raw_by_day[day], observed_at)
        daystats = {m: _new_stats() for m in MODES}
        for path in sorted((root / "four_mode_forecasts").glob(day + "*.json")):
            code = path.stem
            if code in all_codes:
                raise ValueError("duplicate_original_race")
            all_codes.add(code)
            status, validated = archived_four_modes(code, root)
            if status != 200 or validated["model_version"] != VERSION:
                raise ValueError("untrusted_or_mixed_original_forecast:" + code)
            if code in non_scoreable:
                if code in current:
                    raise ValueError("official_non_scoreable_has_valid_trifecta:" + code)
                kinds["non_scoreable_excluded"] += 1
                continue
            record = current.get(code)
            if record is None:
                raise ValueError("missing_nonexcluded_published_trifecta:" + code)
            deadline = datetime.fromisoformat(validated["deadline_jst"])
            source = datetime.fromisoformat(record["confirmed_at_jst"])
            if source <= deadline:
                raise ValueError("postrace_source_time_not_after_deadline:" + code)
            saved_path = root / "confirmed_results" / (code + ".json")
            if saved_path.exists() or saved_path.is_symlink():
                if not confirmed_record_is_usable(saved_path, code):
                    raise ValueError("untrusted_persisted_result:" + code)
                old = json.loads(saved_path.read_bytes())
                if (old["finish_order"] != record["finish_order"]
                        or datetime.fromisoformat(old["confirmed_at_jst"]) != source):
                    raise ValueError("saved_source_result_mismatch:" + code)
                kind = "persisted"
            else:
                kind = "public_unarchived"
            kinds[kind] += 1
            original = json.loads(path.read_bytes())
            winning = "-".join(map(str, record["finish_order"]))
            for mode in MODES:
                probability, tickets = _estimated_coverage(original, mode)
                full_hit = winning in tickets
                _accumulate(daystats[mode], probability, full_hit, kind)
                _accumulate(pooled[mode], probability, full_hit, kind)
        by_day[day] = {mode: _summarize(stats) for mode, stats in daystats.items()}
        daily_raw_stats[day] = daystats
    forecast_roster = raw_status["frozen_original_result_reference"]["forecast_files"]
    expected_scoreable = forecast_roster - len(non_scoreable)
    if (len(all_codes) != forecast_roster
            or kinds["non_scoreable_excluded"] != len(non_scoreable)
            or kinds["persisted"] != raw_status["frozen_original_result_reference"]["evaluated"]
            or kinds["public_unarchived"] != official["remaining_unresolved_result_races"]
            or kinds["persisted"] + kinds["public_unarchived"] != expected_scoreable
            or any(stats["races"] != expected_scoreable for stats in pooled.values())):
        raise ValueError("calibration_roster_does_not_reconcile")
    return {
        "schema": "FOUR_MODE_V2_NOV05_08_ORIGINAL_ESTIMATED_FULL_COVERAGE_CALIBRATION_V1",
        "status": "descriptive_historical_original_full_ticket_coverage_only",
        "archived_original_forecasts": forecast_roster,
        "postrace_scoreable": expected_scoreable,
        "non_scoreable_excluded": len(non_scoreable),
        "persisted_results": kinds["persisted"],
        "public_only_postrace_results": kinds["public_unarchived"],
        "ticket_budgets": dict(BUDGETS),
        "mode": {m: _summarize(pooled[m]) for m in MODES},
        "by_day": by_day,
        "leave_one_day_out_original_auc": _leave_one_day_out_auc(daily_raw_stats),
        "compares_full_mode_ticket_lists_not_top10_for_16_or_22_budget": True,
        "original_estimated_coverage_is_uncalibrated_model_output": True,
        "postrace_csv_latest_snapshot_not_historical_first_receipt": True,
        "official_non_scoreable_reference_manual_not_live_verified_by_CI": True,
        "source_raw_bytes_replayed_from_earlier_research_CI_step": True,
        "research_cohort_may_be_selection_biased": True,
        "prediction_spread_is_not_proof_of_discrimination": True,
        "auc_is_historical_same_cohort_not_future_holdout": True,
        "leave_one_day_out_is_descriptive_robustness_not_prospective": True,
        "predictive_calibration_proven": False,
        "prospective_candidate_pairs": 0,
        "formal": False,
        "model_promotion_allowed": False,
        "warning": "Observed gap is descriptive only. Do not rescale displayed probabilities, modify ticket ranks or claim future performance without independent preregistered forward validation.",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--official-reference", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    source = {day: (args.source_dir / (day + ".csv")).read_bytes() for day in DAYS}
    official = json.loads(args.official_reference.read_bytes())
    report = audit(args.root, source, official)
    encoded = json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print("FOUR_MODE_ORIGINAL_FULL_COVERAGE_CALIBRATION=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
