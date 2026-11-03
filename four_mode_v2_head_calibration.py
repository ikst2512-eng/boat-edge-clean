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
from research_model import probabilities, WIN

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
        "venue_sensitivity": {"by_venue": {}, "leave_one_venue_out": {},
                              "all_venue_deltas_negative": None},
        "unresolved_head_sensitivity": {
            "missing_reproduced_races": 0,
            "counterfactual_all_missing_best_case_brier_delta": None,
            "counterfactual_all_missing_worst_case_brier_delta": None,
            "counterfactual_full_cohort_brier_delta_range": None,
            "counterfactual_all_missing_best_case_log_delta": None,
            "counterfactual_all_missing_worst_case_log_delta": None,
            "minimum_adverse_missing_outcomes_to_reverse_observed_brier": None,
            "warning": "Mathematical possible-head bounds only, NOT predicted or verified outcomes.",
        },
        "leave_one_race_out": {
            "evaluated_exclusions": 0,
            "all_brier_deltas_negative": None,
            "brier_delta_range": None,
            "log_loss_delta_range": None,
            "brier_positive_exclusion_race_codes": [],
            "warning": "Sensitivity of the selected confirmed-only cohort, not external validation.",
        },
        "observed_boat1_wins": 0,
        "sum_predicted_boat1_wins": 0.0,
        "mean_predicted_boat1": None,
        "observed_boat1_rate": None,
        "boat1_brier_score": None,
        "six_head_brier_model": None,
        "six_head_brier_fixed_prior": None,
        "six_head_log_loss_model": None,
        "six_head_log_loss_fixed_prior": None,
        "six_head_model_minus_prior_brier": None,
        "six_head_model_minus_prior_log_loss": None,
        "six_head_brier_model_better_races": 0,
        "six_head_brier_prior_better_races": 0,
        "six_head_brier_ties": 0,
        "fixed_prior_head_probabilities": [round(w / sum(WIN), 6) for w in WIN],
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
    venue_stats = {}
    paired_race_deltas = []
    missing_counterfactual = []
    prior = [w / sum(WIN) for w in WIN]
    six_model_brier = six_prior_brier = 0.0
    six_model_log = six_prior_log = 0.0
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
            heads = [sum(prob for combo, prob in board if combo[0] == i)
                     for i in range(1, 7)]
            if (any(not math.isfinite(prob) or prob <= 0 or prob > 1
                    for prob in heads) or abs(sum(heads) - 1) > 1e-9):
                raise ValueError("bad_head_mass")
            p1 = heads[0]
        except (KeyError, ValueError, TypeError, OverflowError, AssertionError):
            rejected["invalid_model_input"] += 1
            continue
        output["reproduced_current_model"] += 1
        outcome = compare_race(code, root)
        if outcome.get("status") == "result_unavailable":
            output["missing_finish"] += 1
            hypothetical = []
            for first in range(1, 7):
                model_score = sum((heads[i] - int(i + 1 == first))**2 for i in range(6))
                prior_score = sum((prior[i] - int(i + 1 == first))**2 for i in range(6))
                hypothetical.append((model_score-prior_score,
                                     math.log(prior[first-1])-math.log(heads[first-1])))
            missing_counterfactual.append({
                "race_code": code,
                "brier_min": min(x[0] for x in hypothetical),
                "brier_max": max(x[0] for x in hypothetical),
                "log_min": min(x[1] for x in hypothetical),
                "log_max": max(x[1] for x in hypothetical),
            })
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
        head = int(winning[0])
        y = int(head == 1)
        model_brier = sum((heads[i] - int(i + 1 == head))**2 for i in range(6))
        prior_brier = sum((prior[i] - int(i + 1 == head))**2 for i in range(6))
        venue = code[8:10]
        if venue not in venue_stats:
            venue_stats[venue] = {"n": 0, "model_brier_sum": 0.0,
                                  "prior_brier_sum": 0.0,
                                  "model_log_sum": 0.0, "prior_log_sum": 0.0}
        v = venue_stats[venue]
        v["n"] += 1
        v["model_brier_sum"] += model_brier
        v["prior_brier_sum"] += prior_brier
        v["model_log_sum"] -= math.log(heads[head - 1])
        v["prior_log_sum"] -= math.log(prior[head - 1])
        paired_race_deltas.append((code, model_brier - prior_brier,
                                   -math.log(heads[head - 1]) + math.log(prior[head - 1])))
        six_model_brier += model_brier
        six_prior_brier += prior_brier
        six_model_log -= math.log(heads[head - 1])
        six_prior_log -= math.log(prior[head - 1])
        output["six_head_brier_model_better_races"] += int(model_brier < prior_brier - 1e-12)
        output["six_head_brier_prior_better_races"] += int(prior_brier < model_brier - 1e-12)
        output["six_head_brier_ties"] += int(abs(model_brier - prior_brier) <= 1e-12)
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
        output["six_head_brier_model"] = round(six_model_brier / n, 6)
        output["six_head_brier_fixed_prior"] = round(six_prior_brier / n, 6)
        output["six_head_log_loss_model"] = round(six_model_log / n, 6)
        output["six_head_log_loss_fixed_prior"] = round(six_prior_log / n, 6)
        output["six_head_model_minus_prior_brier"] = round(
            (six_model_brier - six_prior_brier) / n, 6)
        output["six_head_model_minus_prior_log_loss"] = round(
            (six_model_log - six_prior_log) / n, 6)
        output["constant_0_5_brier_on_same_cohort"] = round(
            sum(row["n"] * 0.25 for row in output["sample_by_day"].values()) / n, 6)
    if n:
        for venue, values in sorted(venue_stats.items()):
            count = values["n"]
            model_delta = values["model_brier_sum"] - values["prior_brier_sum"]
            log_delta = values["model_log_sum"] - values["prior_log_sum"]
            output["venue_sensitivity"]["by_venue"][venue] = {
                "n": count,
                "model_minus_prior_brier": round(model_delta / count, 6),
                "model_minus_prior_log_loss": round(log_delta / count, 6),
            }
            remainder_n = n - count
            output["venue_sensitivity"]["leave_one_venue_out"][venue] = {
                "n": remainder_n,
                "model_minus_prior_brier": round(
                    (six_model_brier - six_prior_brier - model_delta) / remainder_n, 6
                ) if remainder_n else None,
                "model_minus_prior_log_loss": round(
                    (six_model_log - six_prior_log - log_delta) / remainder_n, 6
                ) if remainder_n else None,
            }
        valid_loo = [v["model_minus_prior_brier"] for v in
                     output["venue_sensitivity"]["leave_one_venue_out"].values()
                     if v["model_minus_prior_brier"] is not None]
        output["venue_sensitivity"]["all_venue_deltas_negative"] = (
            len(venue_stats) >= 2 and len(valid_loo) == len(venue_stats)
            and all(delta < 0 for delta in valid_loo)
        )
        if sum(v["n"] for v in venue_stats.values()) != n:
            raise ValueError("venue_partition_mismatch")
    if n >= 2:
        brier_diffs = []
        log_diffs = []
        total_brier_diff = six_model_brier - six_prior_brier
        total_log_diff = six_model_log - six_prior_log
        for code, one_brier, one_log in paired_race_deltas:
            remainder_brier = (total_brier_diff - one_brier) / (n - 1)
            remainder_log = (total_log_diff - one_log) / (n - 1)
            brier_diffs.append(remainder_brier)
            log_diffs.append(remainder_log)
            if remainder_brier >= 0:
                output["leave_one_race_out"]["brier_positive_exclusion_race_codes"].append(code)
        output["leave_one_race_out"]["evaluated_exclusions"] = n
        output["leave_one_race_out"]["all_brier_deltas_negative"] = all(x < 0 for x in brier_diffs)
        output["leave_one_race_out"]["brier_delta_range"] = [
            round(min(brier_diffs), 6), round(max(brier_diffs), 6)]
        output["leave_one_race_out"]["log_loss_delta_range"] = [
            round(min(log_diffs), 6), round(max(log_diffs), 6)]
    sensitivity = output["unresolved_head_sensitivity"]
    m = len(missing_counterfactual)
    if m != output["missing_finish"]:
        raise ValueError("missing_counterfactual_partition_mismatch")
    sensitivity["missing_reproduced_races"] = m
    if m:
        min_b = sum(x["brier_min"] for x in missing_counterfactual)
        max_b = sum(x["brier_max"] for x in missing_counterfactual)
        min_log = sum(x["log_min"] for x in missing_counterfactual)
        max_log = sum(x["log_max"] for x in missing_counterfactual)
        sensitivity["counterfactual_all_missing_best_case_brier_delta"] = round(min_b/m, 6)
        sensitivity["counterfactual_all_missing_worst_case_brier_delta"] = round(max_b/m, 6)
        sensitivity["counterfactual_all_missing_best_case_log_delta"] = round(min_log/m, 6)
        sensitivity["counterfactual_all_missing_worst_case_log_delta"] = round(max_log/m, 6)
        combined = n + m
        observed_brier_delta = six_model_brier - six_prior_brier
        sensitivity["counterfactual_full_cohort_brier_delta_range"] = [
            round((observed_brier_delta + min_b)/combined, 6),
            round((observed_brier_delta + max_b)/combined, 6),
        ]
        # Hypothetical threshold using only the most adverse missing head
        # outcomes, without assuming anything about later unresolved races.
        running = observed_brier_delta
        for k, max_case in enumerate(
                sorted((x["brier_max"] for x in missing_counterfactual),
                       reverse=True), 1):
            running += max_case
            if running >= 0:
                sensitivity["minimum_adverse_missing_outcomes_to_reverse_observed_brier"] = k
                break
    if len(paired_race_deltas) != n:
        raise ValueError("leave_one_race_cohort_mismatch")
    for row in output["sample_by_day"].values():
        row["sum_predicted_boat1_wins"] = round(row["sum_predicted_boat1_wins"], 6)
    if (output["six_head_brier_model_better_races"] +
            output["six_head_brier_prior_better_races"] +
            output["six_head_brier_ties"] != n):
        raise ValueError("paired_score_partition_mismatch")
    if (output["reproduced_current_model"] !=
            n + output["missing_finish"] + output["invalid_or_untrusted_finish"]):
        raise ValueError("reproduction_cohort_partition_mismatch")
    output["rejected"] = dict(sorted(rejected.items()))
    return output


if __name__ == "__main__":
    print("V2_HEAD_CALIBRATION=" + json.dumps(assess(), sort_keys=True))
