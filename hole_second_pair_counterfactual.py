"""Read-only, outcome-blind counterfactual for hole-mode second-place coverage.

Only archived forecasts inform selection; results are used AFTER candidates freeze.
This is historical research, not a published prediction or formal hit-rate test.
"""
import json
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run

ROOT = Path(__file__).resolve().parent
TOPS = (3, 5, 10)
SOURCES = ("hit", "balance", "hit_balance")


def propose(hole, donor, insertion_rank=3, max_tickets=10):
    """Change one pick at a fixed rank, preserving ticket budget and unique combos.

    Selection has no access to finish order. A new second-place candidate must
    share a hole-mode first-place candidate and introduce a missing (first,second)
    pair. Only pre-existing donor combos qualify, preserving actual third-place
    choices rather than generating hindsight tickets.
    """
    if insertion_rank not in TOPS:
        raise ValueError("invalid insertion rank")
    baseline = list(hole[:max_tickets])
    if len(baseline) < insertion_rank:
        return baseline
    existing = set(baseline)
    head_second = {(x.split("-")[0], x.split("-")[1]) for x in baseline}
    heads = {x.split("-")[0] for x in baseline}
    selected = next((x for x in donor
                     if x not in existing
                     and x.split("-")[0] in heads
                     and tuple(x.split("-")[:2]) not in head_second), None)
    if selected is None:
        return baseline
    # Keep the total number of bets unchanged: an insertion displaces the tail.
    return (baseline[:insertion_rank-1] + [selected] +
            baseline[insertion_rank-1:-1])


def run(root=ROOT, limit=120):
    root = Path(root)
    cohort = cohort_run(root=root, limit=limit)
    if cohort.get("status") != "historical_research_only":
        return {"status": "no_paired_archives", "formal": False}
    codes = cohort["cohort_codes"]
    stats = {"baseline": {"hits": {f"top{k}": 0 for k in TOPS}},
             **{f"{src}_rank{rank}": {
                 "hits": {f"top{k}": 0 for k in TOPS},
                 "added_second_pair": 0, "changed": 0,
                 "gained": {f"top{k}": 0 for k in TOPS},
                 "lost": {f"top{k}": 0 for k in TOPS}}
                 for src in SOURCES for rank in TOPS}}
    comparable = 0
    pair_gap = 0
    pair_gap_gains = {k: 0 for k in stats if k != "baseline"}
    for code in codes:
        record = compare_race(code, root)
        if record.get("status") != "historical_comparison_only":
            continue
        status, archive = archived_four_modes(code, root)
        if status != 200:
            raise ValueError("archive_not_stable")
        modes = {mode: [row["combo"] for row in archive["modes"][mode]["tickets"]]
                 for mode in ("hole", "hit", "balance")}
        winning = record["winning_ticket"]
        baseline = modes["hole"][:10]
        comparable += 1
        is_gap = record["modes"]["hole"]["coverage_diagnostic"] == "winner_second_pair_absent"
        pair_gap += int(is_gap)
        for k in TOPS:
            stats["baseline"]["hits"][f"top{k}"] += int(winning in baseline[:k])
        donors = {"hit": modes["hit"], "balance": modes["balance"],
                  "hit_balance": list(dict.fromkeys(modes["hit"] + modes["balance"]))}
        for src, donor in donors.items():
            for rank in TOPS:
                key = f"{src}_rank{rank}"
                proposal = propose(modes["hole"], donor, rank)
                changed = proposal != baseline
                stats[key]["changed"] += int(changed)
                if changed:
                    pair = tuple(proposal[rank-1].split("-")[:2])
                    stats[key]["added_second_pair"] += int(
                        pair not in {tuple(x.split("-")[:2]) for x in baseline})
                if is_gap and winning in proposal[:10]:
                    pair_gap_gains[key] += 1
                for k in TOPS:
                    b, p = winning in baseline[:k], winning in proposal[:k]
                    stats[key]["hits"][f"top{k}"] += int(p)
                    stats[key]["gained"][f"top{k}"] += int(p and not b)
                    stats[key]["lost"][f"top{k}"] += int(b and not p)
    for key, item in stats.items():
        item["pct"] = {k: round(100*v/comparable, 2) if comparable else None
                       for k, v in item["hits"].items()}
        if key != "baseline":
            item["delta_hits"] = {k: item["hits"][k] - stats["baseline"]["hits"][k]
                                  for k in item["hits"]}
            item["delta_percentage_points"] = {
                k: round(100*v/comparable, 2) if comparable else None
                for k,v in item["delta_hits"].items()}
    return {"schema": "HOLE_SECOND_PAIR_COUNTERFACTUAL_V1",
            "status": "historical_research_only",
            "formal": False, "simulated_only": True,
            "model_improvement_proven": False, "production_forecast_changed": False,
            "remote_first_seen_verified": False,
            "requested": len(codes), "comparable": comparable,
            "baseline_hole_pair_gap": pair_gap,
            "pair_gap_top10_recovered": pair_gap_gains,
            "scenarios": stats,
            "warning": "In-sample hypothetical substitutions; historical time labels do not establish independent predeadline publication. No deployment or prospective accuracy claim."}


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
