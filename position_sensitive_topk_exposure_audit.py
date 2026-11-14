"""Read-only outcome-BLIND Top1/3/5/10 turnover audit for Draft #1698.

This diagnostic is deliberately OUTSIDE the preregistered selector's pinned
source blob. It never opens result, payout, odds or calibration inputs.
Ticket replacement is an EXPOSURE, not a gained/lost winning ticket.
"""
from collections import Counter
from datetime import datetime
import argparse
import json
from pathlib import Path
import re

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_position_sensitive_shadow import (
    BASELINE_VERSION, MODES, ROOT, audit_day, shadow_modes
)

TOPS = (1, 3, 5, 10)
BUDGETS = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}


def _pair(ticket):
    return tuple(ticket.split("-")[:2])


def compare_rankings(baseline, candidate):
    """Paired, same-race rank exposure. No confirmed finish is required."""
    if set(baseline) != set(BUDGETS) or set(candidate) != set(BUDGETS):
        raise ValueError("missing_mode")
    out = {}
    for mode, count in BUDGETS.items():
        old, new = baseline[mode], candidate[mode]
        if (len(old) != count or len(new) != count or
                len(set(old)) != count or len(set(new)) != count):
            raise ValueError("invalid_mode_budget_or_duplicate")
        for item in old + new:
            parts = item.split("-")
            if (len(parts) != 3 or
                    sorted(parts) != sorted(set(parts)) or
                    any(p not in "123456" or len(p) != 1 for p in parts)):
                raise ValueError("invalid_trifecta")
        oldtop, newtop = old[0].split("-"), new[0].split("-")
        row = {
            "top1_changed": old[0] != new[0],
            "top1_first_changed": oldtop[0] != newtop[0],
            "top1_second_changed": oldtop[1] != newtop[1],
            "top1_third_changed": oldtop[2] != newtop[2],
            "top1_first_second_pair_changed": oldtop[:2] != newtop[:2],
            "topn": {},
        }
        for n in TOPS:
            if n > count:
                row["topn"][str(n)] = {
                    "applicable": False,
                    "reason": "ticket_budget_below_requested_topn",
                    "mode_ticket_budget": count,
                }
                continue
            o, c = old[:n], new[:n]
            oldset, newset = set(o), set(c)
            retained = len(oldset & newset)
            row["topn"][str(n)] = {
                "applicable": True,
                "ordered_changed": o != c,
                "membership_changed": oldset != newset,
                "retained": retained,
                "displaced_tickets_not_outcomes": n - retained,
                "old_top1_dropped": old[0] not in newset,
                "candidate_top1_not_in_old_topn": new[0] not in oldset,
                "some_old_first_second_pair_dropped": bool(
                    {_pair(x) for x in o} - {_pair(x) for x in c}),
            }
        out[mode] = row
    return out


def audit_topk_day(day, root=ROOT):
    """Audit only original forecast JSON; no read of result directories."""
    if not re.fullmatch(r"20[0-9]{6}", day):
        raise ValueError("invalid_day")
    directory = Path(root) / "four_mode_forecasts"
    paths = sorted(directory.glob(day + "[0-9][0-9][0-9][0-9].json")) if directory.is_dir() else []
    out = {
        "status": "historical_result_blind_topk_exposure",
        "research_only": True, "formal": False,
        "first_remote_receipt_verified": False,
        "model_improvement_proven": False,
        "production_forecast_changed": False,
        "forward_holdout_scored": 0,
        "day_jst": day,
        "archived_files": len(paths), "compared": 0, "excluded": 0,
        "exclusions": {}, "by_mode": {},
    }
    for mode in MODES:
        out["by_mode"][mode] = {
            "top1_changed": 0, "top1_first_changed": 0,
            "top1_second_changed": 0, "top1_third_changed": 0,
            "top1_first_second_pair_changed": 0,
            "topn": {
                str(n): ({"applicable": False,
                          "reason": "ticket_budget_below_requested_topn",
                          "mode_ticket_budget": BUDGETS[mode]} if n > BUDGETS[mode] else {
                    "applicable": True,
                    "ordered_changed_races": 0,
                    "membership_changed_races": 0,
                    "total_displaced_ticket_slots": 0,
                    "old_top1_dropped_races": 0,
                    "candidate_top1_not_in_old_topn_races": 0,
                    "some_old_first_second_pair_dropped_races": 0,
                    "retained_tickets_histogram": {str(k): 0 for k in range(n + 1)},
                }) for n in TOPS
            },
        }
    for path in paths:
        try:
            if path.is_symlink() or path.stat().st_size > 30000:
                raise ValueError("untrusted_archive_file")
            original = json.loads(path.read_text(encoding="utf-8"))
            if (type(original) is not dict or original.get("race_code") != path.stem
                    or original.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"
                    or original.get("model_version") != BASELINE_VERSION
                    or original.get("target_rates_not_proven") is not True):
                raise ValueError("invalid_original_identity")
            saved = datetime.fromisoformat(original["generated_at_jst"])
            deadline = datetime.fromisoformat(original["deadline_jst"])
            if saved.utcoffset() is None or deadline.utcoffset() is None or saved >= deadline:
                raise ValueError("invalid_archive_clock")
            rates = original["input_national_win_rates"]
            old_full = rank_modes(probabilities(rates))
            old = {}
            for mode in MODES:
                archived = original["modes"][mode]["tickets"]
                computed = old_full[mode]["tickets"]
                if [(x["combo"], x["p"]) for x in archived] != [
                        (x["combo"], x["p"]) for x in computed]:
                    raise ValueError("original_ticket_mismatch")
                old[mode] = [x["combo"] for x in computed]
            new_full = shadow_modes(rates)["modes"]
            new = {m: [x["combo"] for x in new_full[m]["tickets"]] for m in MODES}
            paired = compare_rankings(old, new)
        except (KeyError, TypeError, ValueError, OSError, OverflowError, AssertionError) as exc:
            out["excluded"] += 1
            reason = str(exc)[:70] or type(exc).__name__
            out["exclusions"][reason] = out["exclusions"].get(reason, 0) + 1
            continue
        out["compared"] += 1
        for mode, row in paired.items():
            agg = out["by_mode"][mode]
            for key in ("top1_changed", "top1_first_changed",
                        "top1_second_changed", "top1_third_changed",
                        "top1_first_second_pair_changed"):
                agg[key] += int(row[key])
            for n in TOPS:
                if n > BUDGETS[mode]:
                    continue
                metric = row["topn"][str(n)]
                stat = agg["topn"][str(n)]
                for stat_key, metric_key in (
                    ("ordered_changed_races", "ordered_changed"),
                    ("membership_changed_races", "membership_changed"),
                    ("old_top1_dropped_races", "old_top1_dropped"),
                    ("candidate_top1_not_in_old_topn_races", "candidate_top1_not_in_old_topn"),
                    ("some_old_first_second_pair_dropped_races",
                     "some_old_first_second_pair_dropped"),
                ):
                    stat[stat_key] += int(metric[metric_key])
                stat["total_displaced_ticket_slots"] += metric["displaced_tickets_not_outcomes"]
                stat["retained_tickets_histogram"][str(metric["retained"])] += 1
    for mode in MODES:
        for n in TOPS:
            if n > BUDGETS[mode]:
                continue
            stat = out["by_mode"][mode]["topn"][str(n)]
            stat["mean_displaced_ticket_slots_per_race"] = (
                round(stat["total_displaced_ticket_slots"] / out["compared"], 3)
                if out["compared"] else None)
            if sum(stat["retained_tickets_histogram"].values()) != out["compared"]:
                raise ValueError("exposure_partition_failed")
    out["warning"] = (
        "These values count ticket turnover and possible TopK regression exposure, "
        "NOT hits, gained hits, lost hits, or accuracy. No results/payouts read. "
        "TopK non-inferiority cannot be concluded before independent, preregistered "
        "future same-race outcomes and verified first remote receipts. "
        "Never update the frozen selector or production from these diagnostics."
    )
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default="20261108")
    args = ap.parse_args()
    print(json.dumps(audit_topk_day(args.day), ensure_ascii=False, sort_keys=True))
