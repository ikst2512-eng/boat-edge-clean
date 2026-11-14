"""Batch historical four-mode ticket-coverage research. Never official hit rates."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from four_mode_frozen_diagnostic import compare_race

MODES = ("narrow", "hit", "balance", "hole")
CATEGORIES = ("covered", "winner_head_absent", "winner_second_pair_absent", "winner_third_absent")


def summarize(codes, root=Path(__file__).resolve().parent, comparator=compare_race):
    if not 1 <= len(codes) <= 30 or len(set(codes)) != len(codes):
        raise ValueError("require 1-30 distinct race codes")
    if any(not isinstance(code, str) or not re.fullmatch(r"20[0-9]{10}", code) for code in codes):
        raise ValueError("invalid race code")
    rows = [comparator(code, root) for code in codes]
    eligible = [r for r in rows if r.get("status") == "historical_comparison_only"
                and r.get("formal") is False and r.get("remote_first_seen_verified") is False]
    # Fail closed: missing/invalid flags are never silently counted as misses.
    for row in eligible:
        if not isinstance(row.get("modes"), dict):
            raise ValueError("untrusted_mode_rows")
        for mode in MODES:
            part = row["modes"].get(mode)
            if not isinstance(part, dict):
                raise ValueError("untrusted_mode_rows")
            if "winning_rank" not in part:
                raise ValueError("missing_winning_rank")
            rank = part["winning_rank"]
            if rank is not None and (type(rank) is not int or rank < 1):
                raise ValueError("invalid_winning_rank")
            flags = [part.get(f"top{n}") for n in (3, 5, 10)]
            if any(type(flag) is not bool for flag in flags):
                raise ValueError("invalid_topn_flags")
            if any(flag != (rank is not None and rank <= n) for flag, n in zip(flags, (3, 5, 10))):
                raise ValueError("rank_topn_mismatch")
            if (flags[0] and not flags[1]) or (flags[1] and not flags[2]):
                raise ValueError("nonmonotonic_topn")
            if part.get("coverage_diagnostic") not in CATEGORIES:
                raise ValueError("invalid_coverage")
            if flags[2] and part["coverage_diagnostic"] != "covered":
                raise ValueError("covered_without_top10")
            if part.get("race_dynamics_cause") != "not_determined":
                raise ValueError("untrusted_dynamics")
    by_mode = {}
    for mode in MODES:
        counts = Counter()
        hits = {f"top{n}": 0 for n in (1, 3, 5, 10)}
        for row in eligible:
            part = row["modes"][mode]
            category = part["coverage_diagnostic"]
            if category not in CATEGORIES or part.get("race_dynamics_cause") != "not_determined":
                raise ValueError("untrusted diagnostic")
            counts[category] += 1
            for n in (1, 3, 5, 10):
                hits[f"top{n}"] += int(part["winning_rank"] == 1 if n == 1 else part[f"top{n}"] is True)
        by_mode[mode] = {"evaluated": len(eligible), "coverage": dict(counts),
                         "topn_hits": hits,
                         "historical_topn_pct": {k: round(100 * v / len(eligible), 2)
                                                 if eligible else None for k, v in hits.items()}}
    # All six unordered mode pairs on exactly the same eligible race IDs.
    # Keep the historical three adjacent pairs below for existing consumers.
    pairwise = {}
    for left, right in (("narrow", "hit"), ("narrow", "balance"), ("narrow", "hole"),
                        ("hit", "balance"), ("hit", "hole"), ("balance", "hole")):
        topn = {}
        for n in (1, 3, 5, 10):
            key = f"top{n}"
            counts = {"both": 0, "left_only": 0, "right_only": 0, "neither": 0}
            for row in eligible:
                l = (row["modes"][left]["winning_rank"] == 1 if n == 1 else row["modes"][left][key] is True)
                rr = (row["modes"][right]["winning_rank"] == 1 if n == 1 else row["modes"][right][key] is True)
                group = "both" if l and rr else "left_only" if l else "right_only" if rr else "neither"
                counts[group] += 1
            counts["net_additional_hits"] = counts["right_only"] - counts["left_only"]
            counts["net_percentage_points"] = (round(100 * counts["net_additional_hits"] / len(eligible), 2)
                                                if eligible else None)
            counts["evaluated"] = len(eligible)
            topn[key] = counts
        # Preserve the old top10 contract for existing research consumers.
        ten = topn["top10"]
        pairwise[left + "_vs_" + right] = {
            "evaluated": len(eligible), "both_top10": ten["both"],
            "left_only_top10": ten["left_only"], "right_only_top10": ten["right_only"],
            "neither_top10": ten["neither"], "topn": topn, "formal": False}
    legacy_pairs = {key: pairwise[key] for key in
                    ("narrow_vs_hit", "hit_vs_balance", "balance_vs_hole")}
    # The winning result is consulted only for retrospective audit, never for
    # model ranking or deciding which candidate ticket to replace.
    per_race = [
        {"race_code": row["race_code"],
         "winning_ticket": row.get("winning_ticket"),
         "modes": {mode: {
             "winning_rank": row["modes"][mode]["winning_rank"],
             "top1": row["modes"][mode]["winning_rank"] == 1,
             "top3": row["modes"][mode]["top3"],
             "top5": row["modes"][mode]["top5"],
             "top10": row["modes"][mode]["top10"],
             "coverage_diagnostic": row["modes"][mode]["coverage_diagnostic"]}
             for mode in MODES}}
        for row in eligible]
    return {"schema": "FOUR_MODE_HISTORICAL_AI_BATCH_V1",
            "formal": False, "simulated_only": True, "model_improvement_proven": False,
            "remote_first_seen_verified": False,
            "requested": len(codes), "historical_comparable": len(eligible),
            "unavailable": [{"race_code": row.get("race_code"), "status": row.get("status")}
                            for row in rows if row not in eligible],
            "modes": by_mode, "paired_top10": legacy_pairs,
            "pairwise_topn": pairwise, "per_race": per_race,
            "warning": "Historical coverage only; not independently predeadline verified. No racing dynamics cause inferred."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("codes", nargs="+")
    args = parser.parse_args()
    print(json.dumps(summarize(args.codes), ensure_ascii=False, sort_keys=True))
