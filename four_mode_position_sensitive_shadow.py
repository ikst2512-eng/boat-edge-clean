"""Research-only per-position conditional tilt over frozen CLEAN four-mode prior.

NEVER imported by the production capture, UI or result-scoring paths.
No results/odds/weather/exhibition read; no original forecast is rewritten.
This is a *candidate*, not a verified improvement or betting instruction.
"""
from collections import Counter
from datetime import datetime
from itertools import permutations
from pathlib import Path
import argparse
import json
import math
import re

from research_model import probabilities
from clean_four_modes import rank_modes

ROOT = Path(__file__).resolve().parent
VERSION = "RESEARCH_POSITION_SENSITIVE_V1_UNCALIBRATED"
BASELINE_VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
MODES = ("narrow", "hit", "balance", "hole")
# Fixed before any outcome comparison. These are NOT fitted/calibrated coefficients.
SECOND_BETA = 0.50
THIRD_BETA = 0.25
VALID = set(permutations(range(1, 7), 3))


def shadow_probabilities(national_win_rates):
    """Tilt conditional 2nd/3rd distributions, preserving each first-boat mass.

    p0 is the frozen 120-combination V2 research probability board.
    For each head h, modify p0(h,s,t) by exp(.50*(r_s-mean(r_not_h))
    + .25*(r_t-mean(r_not_hs))), then renormalize WITHIN h.
    This isolates the missing 2nd/3rd rate sensitivity, rather than
    pretending it fixes the first-boat prior.
    """
    base = probabilities(national_win_rates)  # validates six finite positive rates
    rates = tuple(float(x) for x in national_win_rates)
    total_rate = sum(rates)
    original_head = [0.0] * 6
    tilted_head = [0.0] * 6
    adjusted = []
    for ticket, p in base:
        head, second, third = ticket
        first_remaining_mean = (total_rate - rates[head - 1]) / 5
        second_remaining_mean = (total_rate - rates[head - 1] - rates[second - 1]) / 4
        exponent = (SECOND_BETA * (rates[second - 1] - first_remaining_mean)
                    + THIRD_BETA * (rates[third - 1] - second_remaining_mean))
        changed = p * math.exp(exponent)
        if not math.isfinite(changed) or changed <= 0:
            raise ValueError("nonfinite_tilted_probability")
        original_head[head - 1] += p
        tilted_head[head - 1] += changed
        adjusted.append((ticket, changed))
    if len(adjusted) != 120 or {t for t, _ in adjusted} != VALID:
        raise ValueError("incomplete_probability_board")
    if not all(x > 0 and math.isfinite(x) for x in tilted_head):
        raise ValueError("invalid_head_normalizer")
    board = [
        (t, p * original_head[t[0] - 1] / tilted_head[t[0] - 1])
        for t, p in adjusted
    ]
    if abs(sum(p for _, p in board) - 1.0) > 1e-9:
        raise ValueError("normalization_failed")
    return sorted(board, key=lambda item: (-item[1], item[0]))


def shadow_modes(national_win_rates):
    """Standalone research output: never labeled as live or official."""
    return {
        "research_only": True,
        "formal": False,
        "production_forecast": False,
        "model_improvement_proven": False,
        "buy_recommendation": False,
        "model_version": VERSION,
        "available_inputs": ["national_win_rates_six_boats"],
        "missing_inputs": ["verified_predeadline_exhibition", "verified_predeadline_odds",
                           "wind", "motor", "entry_course", "wall"],
        "modes": rank_modes(shadow_probabilities(national_win_rates)),
    }


def audit_day(day, root=ROOT):
    """INPUT-ONLY historical diagnostic. No result/payout file is opened.

    Compare generated research shadow to the exact stored V2 baseline.
    Does NOT attest first-Git-add, time-of-first-receipt or prediction skill.
    """
    if not re.fullmatch(r"20[0-9]{6}", day):
        raise ValueError("invalid_day")
    directory = Path(root) / "four_mode_forecasts"
    archives = sorted(directory.glob(day + "[0-9][0-9][0-9][0-9].json")) if directory.is_dir() else []
    out = {
        "status": "historical_input_only_shadow_diagnostic",
        "day_jst": day,
        "baseline": BASELINE_VERSION,
        "candidate": VERSION,
        "research_only": True,
        "formal": False,
        "production_forecast": False,
        "forward_holdout_scored": 0,
        "model_improvement_proven": False,
        "first_remote_receipt_verified": False,
        "archived_files": len(archives),
        "compared": 0,
        "excluded": 0,
        "exclusions": {},
        "by_mode": {},
    }
    baseline_top1 = {m: Counter() for m in MODES}
    candidate_top1 = {m: Counter() for m in MODES}
    baseline_top5 = {m: set() for m in MODES}
    candidate_top5 = {m: set() for m in MODES}
    changes = {m: Counter() for m in MODES}
    for path in archives:
        try:
            if path.is_symlink() or path.stat().st_size > 30000:
                raise ValueError("invalid_file")
            record = json.loads(path.read_text(encoding="utf-8"))
            code = path.stem
            if (type(record) is not dict or record.get("race_code") != code
                    or record.get("model_version") != BASELINE_VERSION
                    or record.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"):
                raise ValueError("invalid_archive_identity_or_version")
            saved = datetime.fromisoformat(record["generated_at_jst"])
            deadline = datetime.fromisoformat(record["deadline_jst"])
            if saved.utcoffset() is None or deadline.utcoffset() is None or saved >= deadline:
                raise ValueError("invalid_archive_clock")
            rates = record["input_national_win_rates"]
            if type(rates) is not list or len(rates) != 6:
                raise ValueError("invalid_inputs")
            baseline = rank_modes(probabilities(rates))
            for mode in MODES:
                archived = [(x["combo"], x["p"]) for x in record["modes"][mode]["tickets"]]
                reproduced = [(x["combo"], x["p"]) for x in baseline[mode]["tickets"]]
                if archived != reproduced:
                    raise ValueError("baseline_not_reproduced")
            candidate = shadow_modes(rates)["modes"]
        except (KeyError, ValueError, TypeError, OSError, OverflowError, AssertionError) as exc:
            out["excluded"] += 1
            key = str(exc)[:70] or type(exc).__name__
            out["exclusions"][key] = out["exclusions"].get(key, 0) + 1
            continue
        out["compared"] += 1
        for mode in MODES:
            old = tuple(t["combo"] for t in baseline[mode]["tickets"])
            new = tuple(t["combo"] for t in candidate[mode]["tickets"])
            baseline_top1[mode][old[0]] += 1
            candidate_top1[mode][new[0]] += 1
            baseline_top5[mode].add(old[:5])
            candidate_top5[mode].add(new[:5])
            changes[mode]["top1_changed"] += old[0] != new[0]
            changes[mode]["first_boat_changed"] += old[0][0] != new[0][0]
            changes[mode]["top5_order_changed"] += old[:5] != new[:5]
            changes[mode]["top5_membership_changed"] += set(old[:5]) != set(new[:5])
    for mode in MODES:
        out["by_mode"][mode] = {
            **dict(changes[mode]),
            "baseline_distinct_top1": len(baseline_top1[mode]),
            "candidate_distinct_top1": len(candidate_top1[mode]),
            "baseline_distinct_top5_order": len(baseline_top5[mode]),
            "candidate_distinct_top5_order": len(candidate_top5[mode]),
            "baseline_most_common_top1": baseline_top1[mode].most_common(1),
            "candidate_most_common_top1": candidate_top1[mode].most_common(1),
        }
    out["warning"] = (
        "Diversity and rank changes are NOT accuracy improvements. "
        "No outcomes were accessed; historical frozen forecasts remain unchanged. "
        "First-boat masses are intentionally preserved. "
        "Requires preregistered independent future paired validation."
    )
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", default="20261108")
    args = parser.parse_args()
    print(json.dumps(audit_day(args.day), ensure_ascii=False, sort_keys=True))
