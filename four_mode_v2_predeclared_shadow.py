"""Read-only V2 shadow comparison with a frozen, predeclared candidate.

Protocol V1: a <=0.5 national-win-rate gap enables a 0.30
first-place novelty bonus *within the existing hit Top10*. This rule was
informed by inspected V1 history; it is not an independent V1 holdout.
No forecast or result files are written or modified.
"""
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race

ROOT = Path(__file__).resolve().parent
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
PROTOCOL = "V2_FIRST_HEAD_GAP_0_5_BONUS_0_30_SHADOW_V1"
COUNT_POLICY = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
TOPS = (3, 5, 10)


def candidate_order(tickets, rates):
    """Result-blind, fixed-membership, deterministic shadow ordering."""
    if (type(rates) is not list or len(rates) != 6 or
            any(type(v) not in (int, float) or not math.isfinite(v) or
                v < 0 or v > 10 for v in rates)):
        raise ValueError("invalid_rates")
    if len(tickets) != 10:
        raise ValueError("invalid_ticket_count")
    if (len({row["combo"] for row in tickets}) != 10 or
            any(type(row["p"]) not in (int, float) or
                not math.isfinite(row["p"]) or row["p"] < 0 for row in tickets)):
        raise ValueError("invalid_tickets")
    originals = [row["combo"] for row in tickets]
    gap = sorted(rates, reverse=True)[0] - sorted(rates, reverse=True)[1]
    if gap > 0.5:
        return originals, False
    remaining = list(tickets)
    chosen = []
    while remaining:
        previous = {item["combo"][0] for item in chosen}
        best = max(remaining, key=lambda x: (
            x["p"] * (1 + 0.30 * (x["combo"][0] not in previous)),
            x["p"], x["combo"]))
        chosen.append(best)
        remaining.remove(best)
    return [row["combo"] for row in chosen], True


def evaluate(root=ROOT):
    root = Path(root)
    directory = root / "four_mode_forecasts"
    groups = defaultdict(lambda: {
        "forecast_files": 0, "comparable": 0, "pending_results": 0,
        "applied": 0, "baseline": {f"top{n}": 0 for n in TOPS},
        "candidate": {f"top{n}": 0 for n in TOPS},
        "gained_top3": 0, "lost_top3": 0})
    excluded = defaultdict(int)
    if not directory.is_dir():
        return {"status": "no_forecast_directory", "protocol": PROTOCOL,
                "formal": False, "groups": {}}
    for path in sorted(directory.glob("*.json")):
        if not re.fullmatch(r"20[0-9]{10}", path.stem):
            continue
        if path.is_symlink() or path.stat().st_size > 30000:
            excluded["unsafe_file"] += 1
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            excluded["invalid_json"] += 1
            continue
        if raw.get("model_version") != VERSION:
            continue
        date = path.stem[:8]
        row = groups[date]
        row["forecast_files"] += 1
        status, archive = archived_four_modes(path.stem, root)
        if status != 200 or archive.get("model_version") != VERSION:
            excluded["invalid_v2_archive"] += 1
            continue
        if any(len(archive["modes"][m]["tickets"]) != c
               for m, c in COUNT_POLICY.items()):
            excluded["invalid_v2_count_policy"] += 1
            continue
        try:
            candidate, enabled = candidate_order(
                archive["modes"]["hit"]["tickets"],
                raw["input_national_win_rates"])
        except (KeyError, ValueError, TypeError):
            excluded["invalid_shadow_inputs"] += 1
            continue
        compared = compare_race(path.stem, root)
        if compared.get("status") != "historical_comparison_only":
            row["pending_results"] += 1
            continue
        winning = compared["winning_ticket"]
        baseline = [item["combo"] for item in archive["modes"]["hit"]["tickets"]]
        if set(candidate) != set(baseline):
            excluded["membership_changed"] += 1
            continue
        row["comparable"] += 1
        row["applied"] += int(enabled)
        for n in TOPS:
            row["baseline"][f"top{n}"] += int(winning in baseline[:n])
            row["candidate"][f"top{n}"] += int(winning in candidate[:n])
        row["gained_top3"] += int(winning in candidate[:3] and winning not in baseline[:3])
        row["lost_top3"] += int(winning in baseline[:3] and winning not in candidate[:3])
    output = dict(sorted(groups.items()))
    total = sum(v["comparable"] for v in output.values())
    return {"status": "v2_shadow_comparison" if total else "no_comparable_v2_yet",
            "protocol": PROTOCOL, "model_version": VERSION, "formal": False,
            "independent_remote_first_seen_verified": False,
            "v2_forecasts_seen": sum(v["forecast_files"] for v in output.values()),
            "v2_comparable": total, "groups": output, "excluded": dict(excluded),
            "warning": "No official accuracy, no independent holdout, no claim of actual improvement."}


if __name__ == "__main__":
    print("V2_PREDECLARED_SHADOW=" + json.dumps(evaluate(), sort_keys=True))
