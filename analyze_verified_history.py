"""Read-only diagnostics on proof-gated, verified four-mode race history.

Never use pending races, alter archived forecasts, or tune from the same
sample and describe it as out-of-sample improvement.
"""
import json
from collections import Counter
from pathlib import Path
from four_mode_performance import MODES

ROOT = Path(__file__).resolve().parent
BANDS = ((0, 1000, "under_1000"), (1000, 3000, "1000_to_2999"),
         (3000, 10000, "3000_to_9999"), (10000, float("inf"), "10000_plus"))

def combo_of(ticket):
    return ticket.get("combo") if isinstance(ticket, dict) else ticket

def diagnose(history, root=ROOT):
    races = history["races"]
    if history.get("schema") != "CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1":
        raise ValueError("not_verified_history")
    if len({r["race_code"] for r in races}) != len(races):
        raise ValueError("duplicate_race")
    reports = {}
    for mode in MODES:
        ranks = Counter()
        misses = Counter()
        bands = {label: {"races": 0, "hits": 0, "invested_yen": 0, "return_yen": 0}
                 for _, _, label in BANDS}
        winners = []
        profitable_hits = 0
        nonprofitable_hits = 0
        winning_stakes = Counter()
        miss_examples = {"first_missing": [], "second_or_third_missing": [], "third_only_missing": []}
        missing_by_first_boat = Counter()
        missing_third_boats = Counter()
        for race in races:
            code = race["race_code"]
            archive = json.loads((root / "four_mode_forecasts" / (code + ".json")).read_text(encoding="utf-8"))
            if archive["race_code"] != code:
                raise ValueError("archive_mismatch")
            tickets = [combo_of(t) for t in archive["modes"][mode]["tickets"]]
            if len(tickets) != len(set(tickets)):
                raise ValueError("duplicate_ticket")
            winner = race["finish"]
            # Stored forecast tickets are ordered; no post-result re-sorting.
            rank = tickets.index(winner) + 1 if winner in tickets else None
            outcome = race["modes"][mode]
            if outcome["hit"] != (rank is not None):
                raise ValueError("history_and_archive_disagree")
            if rank is not None:
                ranks[str(rank)] += 1
                if outcome["return_yen"] > outcome["invested_yen"]:
                    profitable_hits += 1
                else:
                    nonprofitable_hits += 1
                stake = outcome.get("winning_stake_yen")
                if stake is not None:
                    if type(stake) is not int or stake < 100 or stake % 100:
                        raise ValueError("invalid_winning_stake")
                    winning_stakes[str(stake)] += 1
                winners.append({"race_code": code, "rank": rank, "return_yen": outcome["return_yen"]})
            else:
                parts = winner.split("-")
                first = any(t.startswith(parts[0] + "-") for t in tickets)
                first_two = any(t.startswith(parts[0] + "-" + parts[1] + "-") for t in tickets)
                reason = "third_only_missing" if first_two else "second_or_third_missing" if first else "first_missing"
                misses[reason] += 1
                missing_by_first_boat[parts[0]] += 1
                if first_two:
                    missing_third_boats[parts[2]] += 1
                miss_examples[reason].append({"race_code": code, "actual_finish": winner,
                    "correct_first_in_tickets": first, "correct_first_two_in_tickets": first_two})
            payout = race["payout_per_100_yen"]
            label = next(label for low, high, label in BANDS if low <= payout < high)
            bucket = bands[label]
            bucket["races"] += 1
            bucket["hits"] += int(outcome["hit"])
            bucket["invested_yen"] += outcome["invested_yen"]
            bucket["return_yen"] += outcome["return_yen"]
        for bucket in bands.values():
            cost = bucket["invested_yen"]
            bucket["roi_pct"] = round(100 * bucket["return_yen"] / cost, 2) if cost else None
        gross = sum(x["return_yen"] for x in winners)
        largest = sorted(winners, key=lambda x: x["return_yen"], reverse=True)[:3]
        reports[mode] = {
            "hit_rank_counts": dict(sorted(ranks.items(), key=lambda x: int(x[0]))),
            "profitable_hits": profitable_hits,
            "nonprofitable_hits": nonprofitable_hits,
            "winning_stake_counts": dict(sorted(winning_stakes.items(), key=lambda x: int(x[0]))),
            "miss_types": dict(misses),
            "miss_examples": {reason: rows[:10] for reason, rows in miss_examples.items()},
            "missed_winner_first_boats": dict(sorted(missing_by_first_boat.items())),
            "third_only_missing_boats": dict(sorted(missing_third_boats.items())),
            "payout_bands": bands,
            "largest_three_hits": largest,
            "top_three_return_share_pct": round(100 * sum(x["return_yen"] for x in largest) / gross, 2) if gross else None,
        }
    return {"schema": "CLEAN_VERIFIED_FOUR_MODE_DIAGNOSTICS_V1",
            "simulated_only": True, "sample_races": len(races),
            "budget_yen": history["budget_yen"], "modes": reports}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget-yen", type=int, default=5000, choices=range(5000, 10001, 100))
    args = parser.parse_args()
    path = ROOT / "four_mode_performance" / ("history-" + str(args.budget_yen) + ".json")
    report = diagnose(json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
