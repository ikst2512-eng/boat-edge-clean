"""Read-only V2 winner-head miss profile on confirmed same-race results.

Profiles head absence against the winner's rank in the six archived national
win rates and in the reproduced model's six first-place probabilities.
Results NEVER enter prediction or candidate selection. Historical research only.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from research_model import probabilities
from clean_four_modes import rank_modes

ROOT = Path(__file__).resolve().parent
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
MODES = ("narrow", "hit", "balance", "hole")


def audit(root=ROOT):
    root = Path(root)
    folder = root / "four_mode_forecasts"
    stats = {mode: {
        "matched": 0, "head_absent": 0, "head_present": 0,
        "head_absent_winner_rate_rank": {str(i): 0 for i in range(1, 7)},
        "head_absent_winner_model_rank": {str(i): 0 for i in range(1, 7)},
        "head_absent_winner_boat": {str(i): 0 for i in range(1, 7)},
        "head_absent_winner_national_rate_top2": 0,
        "head_absent_winner_model_head_top2": 0,
        "head_absent_winner_probability_sum": 0.0,
        "head_present_winner_probability_sum": 0.0,
        "head_absent_winner_probability_mean": None,
        "head_present_winner_probability_mean": None,
    } for mode in MODES}
    output = {
        "status": "v2_winner_head_miss_profile_research_only",
        "formal": False, "independent_first_publication_verified": False,
        "matched_confirmed": 0, "missing": 0, "invalid": 0,
        "nonreproduced": 0, "by_mode": stats,
        "hit_head_absent_balance_head_present": 0,
        "hit_head_absent_balance_full_ticket_hit": 0,
        "warning": "Descriptive result-matched V2 cohort, not a holdout or causal race-dynamics explanation.",
    }
    if not folder.is_dir():
        output["status"] = "no_forecast_directory"
        return output
    for path in sorted(folder.glob("*.json")):
        code = path.stem
        if not re.fullmatch(r"20[0-9]{10}", code):
            continue
        if path.is_symlink() or path.stat().st_size > 30000:
            output["invalid"] += 1
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if type(raw) is not dict:
                raise ValueError("invalid_json")
        except (OSError, ValueError, TypeError):
            output["invalid"] += 1
            continue
        if raw.get("model_version") != VERSION:
            continue
        code_status, archive = archived_four_modes(code, root)
        if code_status != 200 or archive.get("model_version") != VERSION:
            output["invalid"] += 1
            continue
        try:
            rates = raw["input_national_win_rates"]
            board = probabilities(rates)
            reproduced = rank_modes(board)
            if any(
                [(x["combo"], x["p"]) for x in archive["modes"][mode]["tickets"]]
                != [(x["combo"], x["p"]) for x in reproduced[mode]["tickets"]]
                for mode in MODES
            ):
                output["nonreproduced"] += 1
                continue
            head_probs = [sum(p for ticket, p in board if ticket[0] == n)
                          for n in range(1, 7)]
            if abs(sum(head_probs) - 1) > 1e-9 or any(
                    not math.isfinite(p) or p <= 0 for p in head_probs):
                raise ValueError("invalid_head_probability")
        except (ValueError, KeyError, TypeError, OverflowError, AssertionError):
            output["invalid"] += 1
            continue
        compared = compare_race(code, root)
        if compared.get("status") == "result_unavailable":
            output["missing"] += 1
            continue
        if compared.get("status") != "historical_comparison_only":
            output["invalid"] += 1
            continue
        winning = compared.get("winning_ticket")
        if (type(winning) is not str or
                not re.fullmatch(r"[1-6]-[1-6]-[1-6]", winning) or
                len(set(winning.split("-"))) != 3):
            output["invalid"] += 1
            continue
        head = int(winning[0])
        national_rank = 1 + sum(value > rates[head-1] for value in rates)
        model_rank = 1 + sum(value > head_probs[head-1] for value in head_probs)
        if not (1 <= national_rank <= 6 and 1 <= model_rank <= 6):
            raise ValueError("invalid_head_rank")
        output["matched_confirmed"] += 1
        absent = {}
        for mode in MODES:
            row = stats[mode]
            tickets = [x["combo"] for x in archive["modes"][mode]["tickets"]]
            is_absent = not any(ticket[0] == str(head) for ticket in tickets)
            absent[mode] = is_absent
            row["matched"] += 1
            row["head_absent"] += int(is_absent)
            row["head_present"] += int(not is_absent)
            if is_absent:
                row["head_absent_winner_rate_rank"][str(national_rank)] += 1
                row["head_absent_winner_model_rank"][str(model_rank)] += 1
                row["head_absent_winner_boat"][str(head)] += 1
                row["head_absent_winner_national_rate_top2"] += int(national_rank <= 2)
                row["head_absent_winner_model_head_top2"] += int(model_rank <= 2)
                row["head_absent_winner_probability_sum"] += head_probs[head - 1]
            else:
                row["head_present_winner_probability_sum"] += head_probs[head - 1]
        if absent["hit"] and not absent["balance"]:
            output["hit_head_absent_balance_head_present"] += 1
            if winning in [ticket["combo"] for ticket in archive["modes"]["balance"]["tickets"]]:
                output["hit_head_absent_balance_full_ticket_hit"] += 1
    n = output["matched_confirmed"]
    for mode, row in stats.items():
        if (row["matched"] != n or
                row["head_absent"] + row["head_present"] != n or
                sum(row["head_absent_winner_rate_rank"].values()) != row["head_absent"] or
                sum(row["head_absent_winner_model_rank"].values()) != row["head_absent"] or
                sum(row["head_absent_winner_boat"].values()) != row["head_absent"]):
            raise ValueError("head_miss_partition_mismatch")
        for label in ("head_absent", "head_present"):
            field = label + "_winner_probability_sum"
            mean = label + "_winner_probability_mean"
            count = row[label]
            row[mean] = round(row[field] / count, 6) if count else None
            row[field] = round(row[field], 6)
    if output["hit_head_absent_balance_full_ticket_hit"] > output["hit_head_absent_balance_head_present"]:
        raise ValueError("balance_rescue_partition_mismatch")
    return output


if __name__ == "__main__":
    print("V2_WINNER_HEAD_MISS_PROFILE=" + json.dumps(audit(), sort_keys=True))
