"""Research-only fixed 10,000-yen staking comparison on proof-gated history.

Candidate weights are fixed in source before evaluation. Never modify forecasts
or count a same-sample result as prospective evidence.
"""
import json
from pathlib import Path
from four_mode_performance import allocate, MODES

ROOT = Path(__file__).resolve().parent
BUDGET = 10000
WEIGHTS = {"baseline": None, "top3_double": (3, 2), "top5_double": (5, 2)}

def tickets_of(archive, mode):
    return archive["modes"][mode]["tickets"]

def weighted_stakes(tickets, top_n, multiplier, budget=BUDGET):
    base = allocate(tickets, budget)
    combos = list(base)
    # Reserve one 100-yen unit per ticket to retain coverage.
    units = budget // 100 - len(combos)
    weights = [multiplier if i < top_n else 1 for i in range(len(combos))]
    weight_sum = sum(weights)
    addition = [units * w // weight_sum for w in weights]
    remaining = units - sum(addition)
    # Deterministic largest-remainder apportionment; ties by saved ticket order.
    priorities = sorted(range(len(combos)), key=lambda i: (-(units * weights[i] % weight_sum), i))
    for i in priorities[:remaining]:
        addition[i] += 1
    stakes = {c: 100 * (1 + addition[i]) for i, c in enumerate(combos)}
    if sum(stakes.values()) != budget or min(stakes.values()) < 100:
        raise ValueError("stake_allocation_invalid")
    return stakes

def compare(history, root=ROOT, mode="hit"):
    if history.get("schema") != "CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1" or history.get("budget_yen") != BUDGET:
        raise ValueError("verified_10000_history_required")
    if mode not in MODES:
        raise ValueError("unknown_mode")
    rows = history["races"]
    if len({r["race_code"] for r in rows}) != len(rows):
        raise ValueError("duplicate_races")
    totals = {name: {"hits": 0, "invested_yen": 0, "return_yen": 0, "profitable_races": 0}
              for name in WEIGHTS}
    for row in rows:
        code, winner = row["race_code"], row["finish"]
        archive = json.loads((root / "four_mode_forecasts" / (code + ".json")).read_text(encoding="utf-8"))
        if archive.get("race_code") != code:
            raise ValueError("archive_mismatch")
        tickets = tickets_of(archive, mode)
        reference = row["modes"][mode]
        baseline = allocate(tickets, BUDGET)
        if reference["hit"] != (winner in baseline):
            raise ValueError("history_hit_mismatch")
        if baseline.get(winner, 0) * row["payout_per_100_yen"] // 100 != reference["return_yen"]:
            raise ValueError("history_payout_mismatch")
        for name, params in WEIGHTS.items():
            stakes = baseline if params is None else weighted_stakes(tickets, *params)
            returned = stakes.get(winner, 0) * row["payout_per_100_yen"] // 100
            result = totals[name]
            result["hits"] += int(winner in stakes)
            result["invested_yen"] += BUDGET
            result["return_yen"] += returned
            result["profitable_races"] += int(returned > BUDGET)
    for stats in totals.values():
        n = len(rows)
        stats["hit_rate_pct"] = round(100 * stats["hits"] / n, 2) if n else None
        stats["roi_pct"] = round(100 * stats["return_yen"] / stats["invested_yen"], 2) if n else None
        stats["net_yen"] = stats["return_yen"] - stats["invested_yen"]
    return {"schema": "CLEAN_RESEARCH_STAKING_COMPARE_V1", "research_only": True,
            "prospectively_validated": False, "mode": mode, "budget_yen": BUDGET,
            "sample_races": len(rows), "policies": totals}

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=MODES, default="hit")
    args = p.parse_args()
    path = ROOT / "four_mode_performance" / "history-10000.json"
    print(json.dumps(compare(json.loads(path.read_text(encoding="utf-8")), mode=args.mode),
                     ensure_ascii=False, indent=2, sort_keys=True))
