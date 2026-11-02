"""Per-race attribution of archived hole second-pair counterfactuals (research only)."""
import json
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run
from hole_second_pair_counterfactual import propose, TOPS, SOURCES

ROOT = Path(__file__).resolve().parent


def audit(root=ROOT, limit=120):
    root = Path(root)
    cohort = cohort_run(root=root, limit=limit)
    if cohort.get("status") != "historical_research_only":
        return {"status": "no_paired_archives", "formal": False}
    rows = []
    for code in cohort["cohort_codes"]:
        result = compare_race(code, root)
        if result.get("status") != "historical_comparison_only":
            continue
        status, archive = archived_four_modes(code, root)
        if status != 200:
            raise ValueError("invalid_archive")
        modes = {name: [item["combo"] for item in archive["modes"][name]["tickets"]]
                 for name in ("hole", "hit", "balance")}
        base = modes["hole"][:10]
        winner = result["winning_ticket"]
        donors = {"hit": modes["hit"], "balance": modes["balance"],
                  "hit_balance": list(dict.fromkeys(modes["hit"] + modes["balance"]))}
        scenarios = {}
        for source in SOURCES:
            for rank in TOPS:
                picks = propose(modes["hole"], donors[source], rank)
                key = f"{source}_rank{rank}"
                added = [item for item in picks if item not in base]
                removed = [item for item in base if item not in picks]
                if len(added) != len(removed) or len(picks) != len(base):
                    raise ValueError("ticket_budget_violation")
                before = {f"top{k}": winner in base[:k] for k in TOPS}
                after = {f"top{k}": winner in picks[:k] for k in TOPS}
                scenarios[key] = {"added": added, "removed": removed,
                    "gained": [f"top{k}" for k in TOPS if after[f"top{k}"] and not before[f"top{k}"]],
                    "lost": [f"top{k}" for k in TOPS if before[f"top{k}"] and not after[f"top{k}"]]}
        rows.append({"race_code": code, "winning_ticket": winner,
                     "baseline_diagnostic": result["modes"]["hole"]["coverage_diagnostic"],
                     "scenarios": scenarios})
    summary = {}
    for key in [f"{source}_rank{rank}" for source in SOURCES for rank in TOPS]:
        summary[key] = {
            "gains": {f"top{k}": [r["race_code"] for r in rows if f"top{k}" in r["scenarios"][key]["gained"]] for k in TOPS},
            "losses": {f"top{k}": [r["race_code"] for r in rows if f"top{k}" in r["scenarios"][key]["lost"]] for k in TOPS},
            "changed": [r["race_code"] for r in rows if r["scenarios"][key]["added"]]}
        for k in TOPS:
            n = f"top{k}"
            if len(summary[key]["gains"][n]) - len(summary[key]["losses"][n]) != sum(
                    int(n in r["scenarios"][key]["gained"]) - int(n in r["scenarios"][key]["lost"]) for r in rows):
                raise ValueError("attribution_error")
    return {"status": "historical_research_only", "formal": False,
            "simulated_only": True, "production_forecast_changed": False,
            "remote_first_seen_verified": False,
            "comparable": len(rows), "summary": summary, "race_audit": rows,
            "warning": "In-sample counterfactual, not prospectively validated. Results were not used to select donor tickets."}


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, sort_keys=True))
