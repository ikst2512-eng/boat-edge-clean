"""Result-blind diagnostic of Top1 head changes; strictly historical INPUTS.

Reads only four_mode_forecasts on discovery dates Nov 5-8. It never opens any
confirmed_results or computes hit rates. It does NOT change the pinned Top1
selector, infer first remote candidate receipt, or establish future efficacy.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

from four_mode_all_mode_same_job_shadow import (
    SIZES, candidate_modes, top1_pair_candidate,
)

DISCOVERY_DAYS = {
    "20261105": 106,
    "20261106": 130,
    "20261107": 122,
    "20261108": 116,
}
RACE_CODE = re.compile(r"20[0-9]{6}(?:0[1-9]|1[0-9]|2[0-4])(?:0[1-9]|1[0-2])\Z")


def position_delta(original, candidate):
    """Return changed finishing places in one three-boat prediction."""
    if (not isinstance(original, str) or not isinstance(candidate, str)
            or not re.fullmatch(r"[1-6]-[1-6]-[1-6]", original)
            or not re.fullmatch(r"[1-6]-[1-6]-[1-6]", candidate)
            or len(set(original.split("-"))) != 3
            or len(set(candidate.split("-"))) != 3):
        raise ValueError("invalid_top1_combo")
    return tuple(a != b for a, b in zip(original.split("-"), candidate.split("-")))


def audit(root, day):
    if day not in DISCOVERY_DAYS:
        raise ValueError("not_frozen_discovery_date")
    folder = Path(root) / "four_mode_forecasts"
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("no_safe_forecast_archive")
    files = sorted(folder.glob(day + "*.json"))
    expected_min = DISCOVERY_DAYS[day]
    if len(files) < expected_min:
        raise ValueError("incomplete_discovery_forecast_inventory")
    return audit_files(files, day, expected_minimum=expected_min)


def audit_files(files, day, expected_minimum=1):
    """Injectable, fail-closed input list for tests; no outcome API or files."""
    if day not in DISCOVERY_DAYS or type(expected_minimum) is not int or expected_minimum < 1:
        raise ValueError("invalid_discovery_input")
    if type(files) is not list or len(files) < expected_minimum:
        raise ValueError("incomplete_discovery_forecast_inventory")
    if day != "20261108" and len(files) != DISCOVERY_DAYS[day] and expected_minimum != 1:
        raise ValueError("historical_inventory_drift")
    modes = {mode: {
        "changed_exact_top1": 0,
        "changed_first_boat": 0,
        "changed_second_boat": 0,
        "changed_third_boat": 0,
        "swaps_same_first_boat": 0,
        "swaps_same_first_second": 0,
        "different_first_boat_in_original_top2": 0,
        "original_top1_heads": Counter(),
        "candidate_top1_heads": Counter(),
        "original_top1_tickets": Counter(),
        "candidate_top1_tickets": Counter(),
    } for mode in SIZES}
    seen = set()
    for path in files:
        path = Path(path)
        code = path.stem
        if (path.is_symlink() or not path.is_file() or path.stat().st_size > 30000
                or not RACE_CODE.fullmatch(code) or not code.startswith(day)
                or code in seen):
            raise ValueError("unsafe_duplicate_or_invalid_original")
        seen.add(code)
        raw = json.loads(path.read_bytes())
        if type(raw) is not dict or raw.get("race_code") != code:
            raise ValueError("original_race_code_mismatch")
        baseline, _ = candidate_modes(raw)  # validates original WITHOUT results
        candidate = top1_pair_candidate(raw, baseline)
        for mode in SIZES:
            old, new = baseline[mode], candidate[mode]
            if (len(old) != SIZES[mode] or len(new) != SIZES[mode]
                    or set(old[:2]) != set(new[:2]) or old[2:] != new[2:]
                    or any(set(old[:n]) != set(new[:n]) for n in (3, 5, 10))):
                raise ValueError("protected_rank_membership_drift")
            a, b = old[0], new[0]
            h, s, t = position_delta(a, b)
            m = modes[mode]
            changed = a != b
            m["changed_exact_top1"] += int(changed)
            m["changed_first_boat"] += int(h)
            m["changed_second_boat"] += int(s)
            m["changed_third_boat"] += int(t)
            m["swaps_same_first_boat"] += int(changed and not h)
            m["swaps_same_first_second"] += int(changed and not h and not s)
            m["different_first_boat_in_original_top2"] += int(old[0][0] != old[1][0])
            m["original_top1_heads"][a[0]] += 1
            m["candidate_top1_heads"][b[0]] += 1
            m["original_top1_tickets"][a] += 1
            m["candidate_top1_tickets"][b] += 1
    summary = {}
    for mode, m in modes.items():
        for key in ("original_top1_tickets", "candidate_top1_tickets"):
            counts = m.pop(key)
            m[key.replace("_tickets", "_distinct_tickets")] = len(counts)
            m[key.replace("_tickets", "_most_common_ticket_count")] = max(counts.values(), default=0)
        for key in ("original_top1_heads", "candidate_top1_heads"):
            m[key] = dict(sorted(m[key].items()))
        if m["changed_first_boat"] > m["changed_exact_top1"]:
            raise ValueError("impossible_head_changes")
        summary[mode] = m
    return {
        "schema": "FOUR_MODE_TOP1_HISTORICAL_HEAD_EXPOSURE_V1",
        "day": day,
        "original_v2_races": len(seen),
        "status": "discovery_input_only_no_outcome_read",
        "result_files_read": False,
        "candidate_first_remote_receipt_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "modes": summary,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--day", required=True, choices=tuple(DISCOVERY_DAYS))
    p.add_argument("--root", default=".")
    args = p.parse_args()
    print(json.dumps(audit(args.root, args.day), sort_keys=True,
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
