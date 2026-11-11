"""Research-only HIT Top1 alternative head, frozen original pre-race inputs only.

This is NOT a calibrated forecast or production proposal. It weakens the
1,000-result original winner-head prior, rather than fabricating wind or ST.
Does NOT read any result files or change original saved forecasts.
The prospective policy is separate from the already-pinned Top1 pair policy.
"""
import argparse
import json
import math
from collections import Counter
from pathlib import Path

from four_mode_all_mode_same_job_shadow import SIZES, candidate_modes
from research_model import WIN, probabilities

RULE = "hit_head_prior_sqrt_with_original_national_beta04_v1"
PRIOR_POWER = 0.5
BETA = 0.4
DISCOVERY_DAYS = {"20261105", "20261106", "20261107", "20261108"}


def choose(raw):
    """Original and candidate tickets; never inspect confirmed results.

    Head score = sqrt(WIN[head]+12)*exp(.4*(national_rate-head_mean)).
    For the selected head, choose highest original probability-board ticket.
    Other modes stay exactly the same. HIT stays 10 unique tickets; when the
    new ticket is absent, it replaces the last, not an extra unbudgeted ticket.
    """
    original, _ = candidate_modes(raw)  # source and V2 ranked forecast replay
    rates = raw["input_national_win_rates"]
    average = sum(rates) / len(rates)
    scores = [
        math.sqrt(WIN[index] + 12) * math.exp(BETA * (rate - average))
        for index, rate in enumerate(rates)
    ]
    if any(not math.isfinite(v) or v <= 0 for v in scores):
        raise ValueError("invalid_head_scores")
    best_head = max(range(6), key=lambda index: (scores[index], -index)) + 1
    board = probabilities(rates)
    ticket = max(
        ((combo, prob) for combo, prob in board if combo[0] == best_head),
        key=lambda pair: (pair[1], tuple(-int(i) for i in pair[0])),
    )[0]
    proposed = "-".join(map(str, ticket))
    base_hit = original["hit"]
    candidate = {mode: list(tickets) for mode, tickets in original.items()}
    if str(best_head) != base_hit[0][0]:
        if proposed in base_hit:
            candidate["hit"] = [proposed] + [x for x in base_hit if x != proposed]
        else:
            candidate["hit"] = [proposed] + base_hit[:-1]
    # This hypothesis has no permission to modify another mode.
    if any(candidate[mode] != original[mode] for mode in SIZES if mode != "hit"):
        raise ValueError("non_hit_mode_changed")
    if (len(candidate["hit"]) != SIZES["hit"]
            or len(set(candidate["hit"])) != SIZES["hit"]
            or candidate["hit"][0][0] != str(best_head)):
        raise ValueError("hit_head_candidate_invalid")
    entry = {
        "schema": "FOUR_MODE_HIT_TOP1_HEAD_PRIOR_RESEARCH_SHADOW_V1",
        "rule": RULE,
        "formal": False,
        "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "candidate_first_remote_receipt_verified": False,
        "official_beforeinfo_six_verified": False,
        "official_odds_120_verified": False,
        "race_code": raw["race_code"],
        "model_version": raw["model_version"],
        "input_national_win_rates": list(rates),
        "winning_head_score": [round(x, 9) for x in scores],
        "candidate_first_boat": best_head,
        "original_hit_top1": base_hit[0],
        "candidate_hit_top1": candidate["hit"][0],
        "hit_top1_changed": candidate["hit"][0] != base_hit[0],
        "hit_first_boat_changed": candidate["hit"][0][0] != base_hit[0][0],
        "hit_top10_membership_changed":
            set(candidate["hit"][:10]) != set(base_hit[:10]),
        "original": original,
        "candidate": candidate,
    }
    return entry


def audit_day(root, day):
    """Discovery INPUT replay only. Never score races or read outcomes."""
    if day not in DISCOVERY_DAYS:
        raise ValueError("not_discovery_input_date")
    folder = Path(root) / "four_mode_forecasts"
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("unsafe_or_missing_original_archive")
    files = sorted(folder.glob(day + "*.json"))
    if not files:
        raise ValueError("empty_discovery_input_set")
    reasons = Counter()
    new_heads = Counter()
    old_heads = Counter()
    changed = 0
    changed_membership = 0
    for path in files:
        if (path.is_symlink() or not path.is_file() or path.stat().st_size > 30000
                or not path.stem.isdecimal() or len(path.stem) != 12
                or path.stem[:8] != day):
            raise ValueError("unsafe_forecast_archive")
        raw = json.loads(path.read_bytes())
        if raw.get("race_code") != path.stem:
            raise ValueError("archive_race_code_mismatch")
        shadow = choose(raw)
        old_heads[shadow["original_hit_top1"][0]] += 1
        new_heads[shadow["candidate_hit_top1"][0]] += 1
        changed += int(shadow["hit_first_boat_changed"])
        changed_membership += int(shadow["hit_top10_membership_changed"])
    return {
        "schema": "HIT_HEAD_PRIOR_DISCOVERY_INPUT_ONLY_V1",
        "status": "historical_input_replay_no_outcome_access",
        "day": day,
        "original_forecasts": len(files),
        "original_top1_heads": dict(sorted(old_heads.items())),
        "candidate_top1_heads": dict(sorted(new_heads.items())),
        "candidate_head_changes": changed,
        "hit_top10_membership_changes": changed_membership,
        "non_hit_modes_unchanged": True,
        "results_read": False,
        "formal": False,
        "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "warning": "Input-sensitivity only; not an accuracy/ROI estimate, "
                   "nor a future-first-receipt or official-T12 certification.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--day", choices=sorted(DISCOVERY_DAYS), required=True)
    p.add_argument("--root", type=Path, default=Path("."))
    args = p.parse_args()
    print(json.dumps(audit_day(args.root, args.day), sort_keys=True,
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
