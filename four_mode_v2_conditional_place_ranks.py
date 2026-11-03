"""Read-only conditional 2nd/3rd place rank audit on matched saved V2 races.

ORACLE diagnostics condition on ACTUAL winning head/pair for attribution only.
Those outcomes are NEVER supplied to prediction or candidate selection.
Does not estimate realizable pick accuracy or prove predeadline publication.
"""
import json
import math
import re
from pathlib import Path

from clean_four_modes import rank_modes
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from research_model import probabilities

ROOT = Path(__file__).resolve().parent
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
MODES = ("narrow", "hit", "balance", "hole")


def conditional_ranks(board, winning):
    """Ranks and probability for actual 2nd given actual 1st and actual
    3rd given actual first TWO. Both are post-result oracle conditions."""
    if (type(winning) is not str or
            not re.fullmatch(r"[1-6]-[1-6]-[1-6]", winning) or
            len(set(winning.split("-"))) != 3):
        raise ValueError("invalid_result")
    head, second, third = map(int, winning.split("-"))
    if len(board) != 120:
        raise ValueError("incomplete_probabilities")
    second_mass = {i: 0.0 for i in range(1, 7) if i != head}
    third_mass = {i: 0.0 for i in range(1, 7) if i not in (head, second)}
    for combo, prob in board:
        if len(combo) != 3 or not (prob > 0 and math.isfinite(prob)):
            raise ValueError("invalid_probability")
        if combo[0] == head:
            second_mass[combo[1]] += prob
            if combo[1] == second:
                third_mass[combo[2]] += prob
    ranks = []
    for dist, correct, denominator in (
            (second_mass, second, 5), (third_mass, third, 4)):
        if len(dist) != denominator or correct not in dist:
            raise ValueError("invalid_conditional_distribution")
        total = sum(dist.values())
        if not 0 < total <= 1 + 1e-8:
            raise ValueError("invalid_mass")
        shares = {boat: mass / total for boat, mass in dist.items()}
        ranking = sorted(shares, key=lambda boat: (-shares[boat], boat))
        ranks.append({
            "rank": ranking.index(correct) + 1,
            "probability": shares[correct],
            "top_candidate": ranking[0],
            "top_probability": shares[ranking[0]],
        })
    return ranks


def audit(root=ROOT):
    root = Path(root)
    output = {
        "status": "v2_oracle_conditional_place_rank_research_only",
        "formal": False,
        "independent_first_publication_verified": False,
        "uses_actual_winner_for_oracle_condition": True,
        "cohort": {"saved_v2": 0, "reproduced": 0, "paired": 0,
                   "missing_result": 0, "invalid": 0, "mismatch": 0},
        "second_given_actual_first": {
            "rank_counts": {str(i): 0 for i in range(1, 6)},
            "top1": 0, "top2": 0, "mean_assigned_probability": None},
        "third_given_actual_first_second": {
            "rank_counts": {str(i): 0 for i in range(1, 5)},
            "top1": 0, "top2": 0, "mean_assigned_probability": None},
        "by_winner_head": {str(i): {"n": 0, "second_top1": 0,
                                   "third_top1": 0} for i in range(1, 7)},
        "warning": "Oracle conditions use the actual outcome. NOT achievable forecasting performance. No holdout or independent deadline evidence.",
    }
    folder = root / "four_mode_forecasts"
    if not folder.is_dir():
        output["status"] = "no_forecast_directory"
        return output
    sums = [0.0, 0.0]
    cohort = output["cohort"]
    second_row = output["second_given_actual_first"]
    third_row = output["third_given_actual_first_second"]
    for path in sorted(folder.glob("*.json")):
        code = path.stem
        if not re.fullmatch(r"20[0-9]{10}", code):
            continue
        if path.is_symlink() or path.stat().st_size > 30000:
            cohort["invalid"] += 1
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if type(raw) is not dict:
                raise ValueError("invalid_archive")
        except (OSError, ValueError, TypeError):
            cohort["invalid"] += 1
            continue
        if raw.get("model_version") != VERSION:
            continue
        cohort["saved_v2"] += 1
        status, archive = archived_four_modes(code, root)
        if status != 200 or archive.get("model_version") != VERSION:
            cohort["invalid"] += 1
            continue
        try:
            board = probabilities(raw["input_national_win_rates"])
            reproduced = rank_modes(board)
            if any(
                [(row["combo"], row["p"]) for row in archive["modes"][mode]["tickets"]]
                != [(row["combo"], row["p"]) for row in reproduced[mode]["tickets"]]
                for mode in MODES):
                cohort["mismatch"] += 1
                continue
        except (KeyError, TypeError, ValueError, OverflowError, AssertionError):
            cohort["invalid"] += 1
            continue
        cohort["reproduced"] += 1
        outcome = compare_race(code, root)
        if outcome.get("status") == "result_unavailable":
            cohort["missing_result"] += 1
            continue
        if outcome.get("status") != "historical_comparison_only":
            cohort["invalid"] += 1
            continue
        try:
            winning = outcome["winning_ticket"]
            result_ranks = conditional_ranks(board, winning)
            head = winning[0]
        except (KeyError, ValueError, TypeError):
            cohort["invalid"] += 1
            continue
        cohort["paired"] += 1
        group = output["by_winner_head"][head]
        group["n"] += 1
        for i, (row, entry, key) in enumerate(zip(
                (second_row, third_row), result_ranks,
                ("second_top1", "third_top1"))):
            rank = entry["rank"]
            row["rank_counts"][str(rank)] += 1
            row["top1"] += int(rank == 1)
            row["top2"] += int(rank <= 2)
            sums[i] += entry["probability"]
            group[key] += int(rank == 1)
    n = cohort["paired"]
    for i, row in enumerate((second_row, third_row)):
        if (sum(row["rank_counts"].values()) != n or
                not 0 <= row["top1"] <= row["top2"] <= n):
            raise ValueError("invalid_rank_partition")
        row["mean_assigned_probability"] = round(sums[i] / n, 6) if n else None
    if sum(group["n"] for group in output["by_winner_head"].values()) != n:
        raise ValueError("winner_head_partition")
    return output


if __name__ == "__main__":
    print("V2_CONDITIONAL_PLACE_RANKS=" + json.dumps(audit(), sort_keys=True))
