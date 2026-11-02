"""Out-of-cohort audit: strictly exclude the 120 previously researched race IDs.

This is a frozen retrospective holdout, NOT an independently timestamped,
prospective validation. Selection is result-blind and source ranking frozen.
"""
import json
import re
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as historical_cohort
from hole_upper_rank_pair_protection import propose

ROOT = Path(__file__).resolve().parent
TOPS = (3, 5, 10)
SCENARIOS = ("hit_rank3", "balance_rank3", "hit_balance_rank3",
             "hit_rank5", "balance_rank5", "hit_balance_rank5")


def holdout_codes(root, training, limit=240):
    root = Path(root)
    forecasts, results = root / "four_mode_forecasts", root / "confirmed_results"
    if limit < 1 or len(training) != len(set(training)):
        raise ValueError("invalid_selection")
    available = sorted(
        p.stem for p in forecasts.glob("*.json")
        if re.fullmatch(r"20[0-9]{10}", p.stem)
        and not p.is_symlink()
        and (results / p.name).is_file()
        and p.stem not in set(training)
    )
    # Deterministic, untouched by finishing order.
    return available[:limit]


def run(root=ROOT, limit=240):
    root = Path(root)
    research = historical_cohort(root=root, limit=120)
    if research.get("status") != "historical_research_only":
        return {"status": "training_unavailable", "formal": False}
    training = research["cohort_codes"]
    held = holdout_codes(root, training, limit)
    rows = []
    unavailable = []
    totals = {
        name: {"changed": 0, "topn": {
            f"top{k}": {"baseline_hits": 0, "candidate_hits": 0, "gained": 0, "lost": 0}
            for k in TOPS}} for name in SCENARIOS
    }
    for code in held:
        status, archive = archived_four_modes(code, root)
        record = compare_race(code, root)
        if status != 200 or record.get("status") != "historical_comparison_only":
            unavailable.append({"race_code": code, "archive_status": status,
                                "comparison_status": record.get("status")})
            continue
        modes = {name: [t["combo"] for t in archive["modes"][name]["tickets"]]
                 for name in ("hole", "hit", "balance")}
        base = modes["hole"][:10]
        donors = {"hit": modes["hit"], "balance": modes["balance"],
                  "hit_balance": list(dict.fromkeys(modes["hit"] + modes["balance"]))}
        winning = record["winning_ticket"]
        scenarios = {}
        for source, donor in donors.items():
            for rank in (3, 5):
                name = f"{source}_rank{rank}"
                modified = propose(base, donor, rank)
                if len(modified) != len(base) or len(modified) != len(set(modified)):
                    raise ValueError("ticket_budget_violation")
                totals[name]["changed"] += int(modified != base)
                scenario = {"changed": modified != base, "topn": {}}
                for k in TOPS:
                    before, after = winning in base[:k], winning in modified[:k]
                    t = totals[name]["topn"][f"top{k}"]
                    t["baseline_hits"] += int(before)
                    t["candidate_hits"] += int(after)
                    t["gained"] += int(after and not before)
                    t["lost"] += int(before and not after)
                    scenario["topn"][f"top{k}"] = {
                        "baseline": before, "candidate": after}
                scenarios[name] = scenario
        rows.append({"race_code": code, "scenarios": scenarios})
    evaluated = len(rows)
    for item in totals.values():
        for t in item["topn"].values():
            if t["candidate_hits"] - t["baseline_hits"] != t["gained"] - t["lost"]:
                raise ValueError("invalid_attribution")
            t["net"] = t["gained"] - t["lost"]
            t["baseline_pct"] = round(100 * t["baseline_hits"] / evaluated, 2) if evaluated else None
            t["candidate_pct"] = round(100 * t["candidate_hits"] / evaluated, 2) if evaluated else None
    return {
        "schema": "HOLE_OUT_OF_COHORT_V1",
        "status": "evaluated_retrospective_holdout" if evaluated else "no_eligible_holdout",
        "formal": False, "simulated_only": True, "prospective_validation": False,
        "remote_first_seen_verified": False, "production_forecast_changed": False,
        "training_codes_count": len(training), "training_codes": training,
        "heldout_requested": len(held), "heldout_comparable": evaluated,
        "heldout_codes": [r["race_code"] for r in rows],
        "unavailable": unavailable, "scenarios": totals, "race_audit": rows,
        "warning": "Disjoint race IDs only; may share dates/venues. Retrospective cohort, not prospective proof."
    }


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
