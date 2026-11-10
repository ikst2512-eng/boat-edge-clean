"""Research-only audit of WITHIN-RACE four-mode overlap and exact shadow tickets.

The current selector intentionally derives all four modes from one joint 120
board. This audit shows rather than hides that overlap. It is not a forced
non-overlap optimizer. No results, payouts, official data, network or production
forecast storage are accessed.
"""
from collections import Counter
from datetime import datetime, timedelta
import json
from pathlib import Path
import re

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_position_sensitive_shadow import BASELINE_VERSION, shadow_modes

SCHEMA = "POSITION_SENSITIVE_SAME_RACE_FOUR_MODE_OVERLAP_AUDIT_V1"
MODES = ("narrow", "hit", "balance", "hole")
BUDGETS = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
PAIRS = tuple((MODES[i], MODES[j]) for i in range(4) for j in range(i + 1, 4))
VALID_CODE = re.compile(r"20[0-9]{10}\Z")


def _tickets(modes):
    if type(modes) is not dict or set(modes) != set(MODES):
        raise ValueError("missing_or_extra_mode")
    found = {}
    for mode in MODES:
        tickets = modes[mode].get("tickets") if type(modes[mode]) is dict else None
        if type(tickets) is not list or len(tickets) != BUDGETS[mode]:
            raise ValueError("missing_or_wrong_ticket_budget")
        pairs = []
        for row in tickets:
            if type(row) is not dict or type(row.get("combo")) is not str:
                raise ValueError("bad_ticket_row")
            combo = row["combo"]
            parts = combo.split("-")
            if (len(parts) != 3 or
                    any(not part.isdigit() or len(part) != 1 for part in parts)
                    or set(parts) - set("123456") or len(set(parts)) != 3):
                raise ValueError("bad_trifecta")
            pairs.append(combo)
        if len(set(pairs)) != len(pairs):
            raise ValueError("duplicate_mode_ticket")
        found[mode] = pairs
    return found


def _per_race(original, candidate):
    a, b = _tickets(original), _tickets(candidate)
    def measure(modes):
        return {
            "top1_by_mode": {name: modes[name][0] for name in MODES},
            "distinct_top1_mode_tickets": len({modes[name][0] for name in MODES}),
            "narrow_is_subset_of_hit": set(modes["narrow"]).issubset(modes["hit"]),
            "pairs": {
                x + "__" + y: {
                    "top1_identical": modes[x][0] == modes[y][0],
                    "shared_tickets": len(set(modes[x]) & set(modes[y])),
                    "overlap_fraction_of_smaller_mode": (
                        len(set(modes[x]) & set(modes[y])) /
                        min(BUDGETS[x], BUDGETS[y])),
                } for x, y in PAIRS
            }
        }
    return {
        "original": measure(a),
        "frozen_candidate": measure(b),
        "original_tickets": a,
        "frozen_candidate_tickets": b,
        "forced_diversification_applied": False,
    }


def audit_same_race_overlap(day, root, *, limit=600):
    """Result-blind, exact stored V2 replay; no sample-only denominators."""
    if type(day) is not str or not re.fullmatch(r"20[0-9]{6}", day):
        raise ValueError("invalid_day")
    if type(limit) is not int or not 1 <= limit <= 600:
        raise ValueError("invalid_limit")
    directory = Path(root) / "four_mode_forecasts"
    files = sorted(directory.glob(day + "[0-9][0-9][0-9][0-9].json"))
    if not files or len(files) > limit:
        raise ValueError("missing_or_excess_day_originals")
    counts = {
        version: {
            "distinct_top1_histogram": {str(i): 0 for i in range(1, 5)},
            "narrow_subset_hit_races": 0,
            "mode_pairs": {
                x + "__" + y: {"top1_identical_races": 0,
                               "shared_ticket_total": 0,
                               "mean_shared_ticket_count": None}
                for x, y in PAIRS},
        } for version in ("original", "frozen_candidate")
    }
    per_race = []
    for file in files:
        if file.is_symlink() or not 0 < file.stat().st_size <= 30000:
            raise ValueError("unsafe_original_file")
        raw = json.loads(file.read_bytes())
        if (type(raw) is not dict
                or not VALID_CODE.fullmatch(file.stem)
                or raw.get("race_code") != file.stem
                or raw.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"
                or raw.get("model_version") != BASELINE_VERSION
                or raw.get("validated") is not False
                or raw.get("target_rates_not_proven") is not True):
            raise ValueError("invalid_original_identity")
        generated = datetime.fromisoformat(raw["generated_at_jst"])
        deadline = datetime.fromisoformat(raw["deadline_jst"])
        if (generated.utcoffset() != timedelta(hours=9)
                or deadline.utcoffset() != timedelta(hours=9)
                or not generated < deadline):
            raise ValueError("invalid_stored_clock")
        rates = raw["input_national_win_rates"]
        original = rank_modes(probabilities(rates))
        for mode in MODES:
            if raw["modes"][mode]["tickets"] != original[mode]["tickets"]:
                raise ValueError("stored_original_replay_mismatch")
        candidate = shadow_modes(rates)["modes"]
        observed = _per_race(original, candidate)
        per_race.append({
            "race_code": file.stem,
            "stored_original_generated_at_jst": raw["generated_at_jst"],
            "stored_original_before_T_minus_12_self_declared":
                generated < deadline - timedelta(minutes=12),
            **observed,
        })
        for ver in counts:
            c = counts[ver]
            v = observed[ver]
            c["distinct_top1_histogram"][str(v["distinct_top1_mode_tickets"])] += 1
            c["narrow_subset_hit_races"] += int(v["narrow_is_subset_of_hit"])
            for key, row in v["pairs"].items():
                c["mode_pairs"][key]["top1_identical_races"] += int(
                    row["top1_identical"])
                c["mode_pairs"][key]["shared_ticket_total"] += row["shared_tickets"]
    for ver in counts:
        for entry in counts[ver]["mode_pairs"].values():
            entry["mean_shared_ticket_count"] = round(
                entry["shared_ticket_total"] / len(per_race), 3)
    return {
        "schema": SCHEMA, "day_jst": day,
        "status": "all_saved_day_same_race_cross_mode_overlap_research_only",
        "original_records": len(files), "exact_v2_replays": len(per_race),
        "within_race_overlap": counts,
        "by_race_full_tickets": per_race,
        "original_forecast_git_first_remote_acceptance_verified": False,
        "official_beforeinfo_exhibition_odds120_verified": False,
        "new_candidate_first_remote_acceptance_verified": False,
        "source_has_only_legacy_six_rate_selector": True,
        "independently_scored_results": 0,
        "actual_hit_rate_measured": False,
        "forced_ticket_diversification": False,
        "formal": False, "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "Narrow is structurally always a subset of Hit in rank_modes: "
            "both baseline and #1698 fixed selector share the same 120 board. "
            "A new forecast model, official-source feature integration, and "
            "prospective validation are required to meaningfully distinguish "
            "modes; suppressing duplicates alone is NOT a valid accuracy fix."
        ),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = audit_same_race_overlap(args.day, Path(args.root))
    target = Path(args.output)
    if target.exists() or target.is_symlink() or target.parent.is_symlink():
        raise ValueError("refuse_overwrite_or_symlink_output")
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2,
                                 sort_keys=True) + "\n", encoding="utf-8")
    counts = out["within_race_overlap"]
    print("SAME_RACE_FOUR_MODE_OVERLAP_RESEARCH=" + json.dumps({
        "records": out["original_records"],
        "original_narrow_subset_hit":
            counts["original"]["narrow_subset_hit_races"],
        "candidate_narrow_subset_hit":
            counts["frozen_candidate"]["narrow_subset_hit_races"],
        "original_top1_identical_narrow_hit":
            counts["original"]["mode_pairs"]["narrow__hit"]["top1_identical_races"],
        "candidate_top1_identical_narrow_hit":
            counts["frozen_candidate"]["mode_pairs"]["narrow__hit"]["top1_identical_races"],
        "four_mode_top1_hist_original":
            counts["original"]["distinct_top1_histogram"],
        "four_mode_top1_hist_candidate":
            counts["frozen_candidate"]["distinct_top1_histogram"],
        "formal": False,
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
