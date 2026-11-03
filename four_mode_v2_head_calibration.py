"""Read-only exploratory calibration of boat-one head probability on V2 races.

Uses independently stored confirmed finish *only for scoring*, not for producing
forecasts. Current-code reproduction != independent first-add provenance.
Missing outcomes never become losses. No tuning or model promotion.
"""
import json
import math
import re
from pathlib import Path
from collections import Counter

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from clean_four_modes import rank_modes
from research_model import probabilities

ROOT = Path(__file__).resolve().parent
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
MODES = ("narrow", "hit", "balance", "hole")


def assess(root=ROOT):
    root = Path(root)
    folder = root / "four_mode_forecasts"
    output = {
        "status": "v2_boat1_probability_research_only",
        "formal": False,
        "independent_first_publication_verified": False,
        "independent_future_holdout_verified": False,
        "saved_v2_archives": 0,
        "reproduced_current_model": 0,
        "matched_valid_finish": 0,
        "missing_finish": 0,
        "invalid_or_untrusted_finish": 0,
        "not_reproduced": 0,
        "rejected": {},
        "sample_by_day": {},
        "observed_boat1_wins": 0,
        "sum_predicted_boat1_wins": 0.0,
        "mean_predicted_boat1": None,
        "observed_boat1_rate": None,
        "boat1_brier_score": None,
        "constant_0_5_brier_on_same_cohort": None,
        "warning": "Descriptive selected-result cohort; not official skill or calibration evidence.",
    }
    if not folder.is_dir():
        output["status"] = "no_forecast_directory"
        return output
    rejected = Counter()
    expected_sum = 0.0
    brier_sum = 0.0
    wins = 0
    for path in sorted(folder.glob("*.json")):
        code = path.stem
        if not re.fullmatch(r"20[0-9]{10}", code):
            continue
        if path.is_symlink() or path.stat().st_size > 30000:
            rejected["unsafe_file"] += 1
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if type(raw) is not dict:
                raise ValueError("invalid_json_object")
        except (OSError, ValueError, TypeError):
            rejected["unreadable_json"] += 1
            continue
        if raw.get("model_version") != VERSION:
            continue
        output["saved_v2_archives"] += 1
        status, archive = archived_four_modes(code, root)
        if status != 200 or archive.get("model_version") != VERSION:
            rejected["invalid_archive"] += 1
            continue
        try:
            rates = raw["input_national_win_rates"]
            board = probabilities(rates)
            forecast = rank_modes(board)
            if any(
                [(t["combo"], t["p"]) for t in archive["modes"][mode]["tickets"]]
                != [(t["combo"], t["p"]) for t in forecast[mode]["tickets"]]
                for mode in MODES
            ):
                output["not_reproduced"] += 1
                continue
            p1 = sum(prob for combo, prob in board if combo[0] == 1)
            if not math.isfinite(p1) or not 0 <= p1 <= 1:
                raise ValueError("bad_head_mass")
        except (KeyError, ValueError, TypeError, OverflowError, AssertionError):
            rejected["invalid_model_input"] += 1
            continue
        output["reproduced_current_model"] += 1
        outcome = compare_race(code, root)
        if outcome.get("status") == "result_unavailable":
            output["missing_finish"] += 1
            continue
        if outcome.get("status") != "historical_comparison_only":
            output["invalid_or_untrusted_finish"] += 1
            continue
        winning = outcome.get("winning_ticket")
        if (type(winning) is not str or
                not re.fullmatch(r"[1-6]-[1-6]-[1-6]", winning) or
                len(set(winning.split("-"))) != 3):
            output["invalid_or_untrusted_finish"] += 1
            continue
        y = int(winning.startswith("1-"))
        output["matched_valid_finish"] += 1
        wins += y
        expected_sum += p1
        brier_sum += (p1 - y)**2
        day = code[:8]
        if day not in output["sample_by_day"]:
            output["sample_by_day"][day] = {
                "n": 0, "boat1_wins": 0, "sum_predicted_boat1_wins": 0.0,
            }
        row = output["sample_by_day"][day]
        row["n"] += 1
        row["boat1_wins"] += y
        row["sum_predicted_boat1_wins"] += p1
    n = output["matched_valid_finish"]
    output["observed_boat1_wins"] = wins
    output["sum_predicted_boat1_wins"] = round(expected_sum, 6)
    if n:
        output["mean_predicted_boat1"] = round(expected_sum / n, 6)
        output["observed_boat1_rate"] = round(wins / n, 6)
        output["boat1_brier_score"] = round(brier_sum / n, 6)
        output["constant_0_5_brier_on_same_cohort"] = round(
            sum(row["n"] * 0.25 for row in output["sample_by_day"].values()) / n, 6)
    for row in output["sample_by_day"].values():
        row["sum_predicted_boat1_wins"] = round(row["sum_predicted_boat1_wins"], 6)
    if (output["reproduced_current_model"] !=
            n + output["missing_finish"] + output["invalid_or_untrusted_finish"]):
        raise ValueError("reproduction_cohort_partition_mismatch")
    output["rejected"] = dict(sorted(rejected.items()))
    return output


if __name__ == "__main__":
    print("V2_HEAD_CALIBRATION=" + json.dumps(assess(), sort_keys=True))
