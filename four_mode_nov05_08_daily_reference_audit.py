"""Read-only Nov 5-8 V2 saved-forecast versus persisted independent-result audit.

Historical descriptive coverage ONLY, never official T-12 certification or a
prospective candidate-vs-baseline performance test. In particular, the saved
result record's source_sha256 has not been independently replayed against the
published raw CSV by this script. No new forecasts, candidate ranks or results
are generated or modified.
"""
import argparse
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from collect_clean_results import confirmed_record_is_usable
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import classify_ticket_miss

ROOT = Path(__file__).resolve().parent
DAYS = ("20261105", "20261106", "20261107", "20261108")
MODES = ("narrow", "hit", "balance", "hole")
TOPS = (1, 3, 5, 10)
BUDGETS = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
CODE = re.compile(r"20[0-9]{10}\Z")
CAUSES = ("covered", "winner_head_absent", "winner_second_pair_absent", "winner_third_absent")
PAIRS = (("narrow", "hit"), ("hit", "balance"), ("balance", "hole"))


def _result(path, code, deadline):
    """Apply existing result trust gate and stricter research timing."""
    if not confirmed_record_is_usable(path, code):
        raise ValueError("untrusted_result_or_source")
    obj = json.loads(path.read_bytes())
    confirmed = datetime.fromisoformat(obj["confirmed_at_jst"])
    collected = datetime.fromisoformat(obj["collected_at_jst"])
    if confirmed <= deadline or collected < confirmed:
        raise ValueError("result_timestamp_not_post_deadline_or_collection")
    order = obj["finish_order"]
    if (type(order) is not list or len(order) != 3
            or any(type(x) is not int or x not in range(1, 7) for x in order)
            or len(set(order)) != 3):
        raise ValueError("invalid_finish_order")
    return "-".join(map(str, order))


def _new_mode():
    return {"top_hits": {f"top{n}": 0 for n in TOPS},
            "top_pct": {f"top{n}": None for n in TOPS},
            "miss_partition": {cause: 0 for cause in CAUSES},
            "first_boat_missing": 0}


def _pending_bounds(hits, evaluated, pending):
    """Worst-case deterministic missing-result range, NOT a confidence interval."""
    if (any(type(x) is not int or x < 0 for x in (hits, evaluated, pending))
            or hits > evaluated):
        raise ValueError("invalid_bounds_input")
    total = evaluated + pending
    return {"saved_valid_with_or_without_result": total,
            "confirmed_only_hits": hits,
            "lower_percent_all_pending_miss": round(100 * hits / total, 2) if total else None,
            "upper_percent_all_pending_hit": round(100 * (hits + pending) / total, 2) if total else None,
            "interpretation": "missing_outcomes_extreme_bounds_not_confidence_interval"}


def _paired_empty():
    return {a + "_vs_" + b: {"both": 0, "left_only": 0, "right_only": 0,
                              "neither": 0} for a, b in PAIRS}


def _paired_add(target, key, left, right):
    branch = ("both" if left and right else "left_only" if left else
              "right_only" if right else "neither")
    target[key][branch] += 1


def _pooled_reference(reports):
    evaluated = sum(r["evaluated"] for r in reports.values())
    pending = sum(r["pending_result_count"] for r in reports.values())
    by_mode = {}
    for mode in MODES:
        hits = {f"top{n}": sum(g["mode"][mode]["top_hits"][f"top{n}"]
                              for g in reports.values()) for n in TOPS}
        covered = sum(g["mode"][mode]["miss_partition"]["covered"]
                      for g in reports.values())
        if covered < hits["top10"]:
            raise AssertionError("top10_exceeds_full_list")
        by_mode[mode] = {
            "top_hits": hits,
            "top_pct_confirmed_only": {k: round(100 * v / evaluated, 2)
                                       if evaluated else None for k, v in hits.items()},
            "top_pending_bounds": {k: _pending_bounds(v, evaluated, pending)
                                   for k, v in hits.items()},
            "full_list_covered": covered,
            "full_list_covered_pending_bounds": _pending_bounds(covered, evaluated, pending),
            "full_list_correct_beyond_top10": covered - hits["top10"],
            "miss_partition": {cause: sum(g["mode"][mode]["miss_partition"][cause]
                                          for g in reports.values()) for cause in CAUSES}
        }
    paired = _paired_empty()
    for g in reports.values():
        for key, counts in g["paired_top10"].items():
            for field, value in counts.items():
                paired[key][field] += value
    for key, counts in paired.items():
        if sum(counts.values()) != evaluated:
            raise AssertionError("paired_top10_partition_mismatch:" + key)
    return {"confirmed_denominator": evaluated, "pending_outcome_count": pending,
            "known_plus_pending_denominator": evaluated + pending,
            "missing_result_intervals_are_not_confidence_intervals": True,
            "mode": by_mode, "same_race_original_top10_pairs": paired,
            "warning": "These extremes are descriptive bounds over as-yet unresolved outcomes, not confidence intervals or comparative causal improvement."}


def audit(root=ROOT, days=DAYS):
    root = Path(root)
    days = tuple(days)
    if (not days or any(not isinstance(x, str) or not re.fullmatch(r"20[0-9]{6}", x)
                        for x in days) or len(set(days)) != len(days)):
        raise ValueError("invalid_days")
    reports = {}
    all_excluded = Counter()
    for day in days:
        forecast_dir = root / "four_mode_forecasts"
        paths = (sorted(forecast_dir.glob(day + "*.json")) if forecast_dir.is_dir() else [])
        group = {"forecast_files": len(paths), "v2_archives": 0, "evaluated": 0,
                 "pending_result_count": 0, "pending_result_codes": [],
                 "excluded_count": 0, "excluded_reasons": {},
                 "excluded_samples": {}, "mode": {m: _new_mode() for m in MODES},
                 "paired_top10": _paired_empty(),
                 "first_place_result_counts": {str(n): 0 for n in range(1, 7)}}
        reasons = Counter()
        samples = {}
        for path in paths:
            code = path.stem
            reason = None
            try:
                if (not CODE.fullmatch(code) or code[:8] != day
                        or path.is_symlink() or not path.is_file()
                        or path.stat().st_size > 30000):
                    raise ValueError("unsafe_or_invalid_forecast_path")
                status, forecast = archived_four_modes(code, root)
                if status != 200:
                    raise ValueError("invalid_saved_forecast")
                if forecast["model_version"] != VERSION:
                    raise ValueError("not_v2_model_version")
                deadline = datetime.fromisoformat(forecast["deadline_jst"])
                generated = datetime.fromisoformat(forecast["generated_at_jst"])
                if (deadline.utcoffset() != timedelta(hours=9)
                        or generated.utcoffset() != timedelta(hours=9)
                        or deadline.strftime("%Y%m%d") != day
                        or generated >= deadline):
                    raise ValueError("forecast_timestamp_inconsistent")
                if any(len(forecast["modes"][m]["tickets"]) != BUDGETS[m] for m in MODES):
                    raise ValueError("inconsistent_mode_ticket_budget")
                group["v2_archives"] += 1
                result_path = root / "confirmed_results" / (code + ".json")
                if not result_path.is_file() and not result_path.is_symlink():
                    group["pending_result_codes"].append(code)
                    continue
                winning = _result(result_path, code, deadline)
                data = {}
                for mode in MODES:
                    tickets = [x["combo"] for x in forecast["modes"][mode]["tickets"]]
                    if len(set(tickets)) != len(tickets):
                        raise ValueError("duplicate_saved_tickets")
                    rank = tickets.index(winning) + 1 if winning in tickets else None
                    miss = classify_ticket_miss(tickets, winning)
                    if miss not in CAUSES or (rank is not None) != (miss == "covered"):
                        raise ValueError("miss_partition_inconsistent")
                    data[mode] = (rank, miss)
                group["evaluated"] += 1
                group["first_place_result_counts"][winning[0]] += 1
                for mode in MODES:
                    rank, miss = data[mode]
                    row = group["mode"][mode]
                    for n in TOPS:
                        row["top_hits"][f"top{n}"] += int(rank is not None and rank <= n)
                    row["miss_partition"][miss] += 1
                    row["first_boat_missing"] += int(miss == "winner_head_absent")
                for a, b in PAIRS:
                    key = a + "_vs_" + b
                    left_rank = data[a][0]
                    right_rank = data[b][0]
                    _paired_add(group["paired_top10"], key,
                                left_rank is not None and left_rank <= 10,
                                right_rank is not None and right_rank <= 10)
            except (KeyError, OSError, ValueError, TypeError, OverflowError,
                    json.JSONDecodeError, UnicodeError) as exc:
                reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            if reason is not None:
                reasons[reason] += 1
                samples.setdefault(reason, code)
        group["pending_result_count"] = len(group["pending_result_codes"])
        group["excluded_count"] = sum(reasons.values())
        group["excluded_reasons"] = dict(sorted(reasons.items()))
        group["excluded_samples"] = dict(sorted(samples.items()))
        all_excluded.update(reasons)
        for mode in MODES:
            row = group["mode"][mode]
            for n in TOPS:
                k = f"top{n}"
                row["top_pct"][k] = (round(100 * row["top_hits"][k] / group["evaluated"], 2)
                                     if group["evaluated"] else None)
            hits = row["top_hits"]
            if any(hits[f"top{a}"] > hits[f"top{b}"] for a, b in ((1, 3), (3, 5), (5, 10))):
                raise AssertionError("non_monotone_topn")
            if sum(row["miss_partition"].values()) != group["evaluated"]:
                raise AssertionError("partition_does_not_sum_to_denominator")
            row["top_pending_bounds"] = {f"top{n}": _pending_bounds(
                hits[f"top{n}"], group["evaluated"], group["pending_result_count"])
                for n in TOPS}
            if row["miss_partition"]["covered"] < hits["top10"]:
                raise AssertionError("top10_exceeds_full_list")
        if (group["evaluated"] + group["pending_result_count"] + group["excluded_count"]
                != group["forecast_files"]):
            raise AssertionError("forecast_roster_not_fully_accounted")
        for key, counts in group["paired_top10"].items():
            if sum(counts.values()) != group["evaluated"]:
                raise AssertionError("same_race_pair_denominator_mismatch:" + key)
        if sum(group["first_place_result_counts"].values()) != group["evaluated"]:
            raise AssertionError("winning_head_distribution_mismatch")
        reports[day] = group
    return {
        "schema": "FOUR_MODE_NOV05_08_REFERENCE_DAILY_AUDIT_V1",
        "status": "saved_original_vs_independently_persisted_result_reference_only",
        "days": list(days),
        "by_day": reports,
        "reference_overall": _pooled_reference(reports),
        "totals": {
            "forecast_files": sum(r["forecast_files"] for r in reports.values()),
            "evaluated": sum(r["evaluated"] for r in reports.values()),
            "pending_results": sum(r["pending_result_count"] for r in reports.values()),
            "excluded": sum(r["excluded_count"] for r in reports.values()),
            "excluded_reasons": dict(sorted(all_excluded.items()))
        },
        "interpretation": "Descriptive historical coverage, not future candidate improvement.",
        "result_source_bytes_reverified": False,
        "independent_candidate_first_remote_receipt_verified": False,
        "official_T_minus_12_six_boat_and_120_odds_verified": False,
        "complete_schedule_run_inventory_verified": False,
        "formal": False,
        "formal_count": 0,
        "prospective_candidate_pairs": 0,
        "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "wind_ST_entry_motor_causality": "not_determined",
        "gemini_live_api_reanalysis": "not_performed",
        "guardrail": "Nov5-8 outcomes cannot be used as prospective validation of PR1693 candidate; use preregistered future cohort only."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.root)
    result = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    print("FOUR_MODE_NOV05_08_REFERENCE=" + json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
