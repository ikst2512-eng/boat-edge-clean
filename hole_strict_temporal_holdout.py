"""Strictly later-date hole-mode historical holdout. Never a prospective claim."""
import json
from pathlib import Path
from four_mode_historical_cohort import run as training_run
from hole_out_of_cohort_validation import holdout_codes
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from hole_upper_rank_pair_protection import propose

TOPS = (3, 5, 10)
SCENARIOS = ("hit_rank3", "balance_rank3", "hit_balance_rank3",
             "hit_rank5", "balance_rank5", "hit_balance_rank5")

def later_date_codes(root, training, limit=240):
    """Disjoint dates, not merely disjoint race IDs; no outcome-based selection."""
    if not training:
        return []
    boundary = max(code[:8] for code in training)
    training_dates = {code[:8] for code in training}
    return [code for code in holdout_codes(root, training, limit=100000)
            if code[:8] > boundary and code[:8] not in training_dates][:limit]

def run(root=None, limit=240):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    training = training_run(root=root, limit=120)
    if training.get("status") != "historical_research_only":
        return {"status": "training_unavailable", "formal": False}
    codes = training["cohort_codes"]
    later = later_date_codes(root, codes, limit)
    counts = {name: {"changed":0, "topn":{f"top{k}":{"baseline_hits":0,
              "candidate_hits":0,"gained":0,"lost":0} for k in TOPS}}
              for name in SCENARIOS}
    evaluated = []
    unavailable = []
    for code in later:
        status, archive = archived_four_modes(code, root)
        if status != 200:
            unavailable.append(code)
            continue
        modes = {name:[t["combo"] for t in archive["modes"][name]["tickets"]]
                 for name in ("hole","hit","balance")}
        base = modes["hole"][:10]
        donor = {"hit":modes["hit"],"balance":modes["balance"],
                 "hit_balance":list(dict.fromkeys(modes["hit"]+modes["balance"]))}
        # Freeze all six alternatives before observing the result.
        prepared = {}
        for source, tickets in donor.items():
            for rank in (3,5):
                key = f"{source}_rank{rank}"
                candidate = propose(base,tickets,rank)
                if len(candidate)!=len(base) or len(candidate)!=len(set(candidate)):
                    raise ValueError("invalid_ticket_budget")
                prepared[key] = candidate
        row = compare_race(code, root)
        if row.get("status") != "historical_comparison_only":
            unavailable.append(code)
            continue
        winner = row["winning_ticket"]
        for key, candidate in prepared.items():
                counts[key]["changed"] += int(candidate!=base)
                for k in TOPS:
                    old = winner in base[:k]
                    new = winner in candidate[:k]
                    bucket=counts[key]["topn"][f"top{k}"]
                    bucket["baseline_hits"] += int(old)
                    bucket["candidate_hits"] += int(new)
                    bucket["gained"] += int(new and not old)
                    bucket["lost"] += int(old and not new)
        evaluated.append(code)
    n=len(evaluated)
    for scenario in counts.values():
        for metric in scenario["topn"].values():
            metric["net"]=metric["gained"]-metric["lost"]
            if metric["candidate_hits"]-metric["baseline_hits"]!=metric["net"]:
                raise ValueError("invalid_attribution")
            metric["baseline_pct"]=round(100*metric["baseline_hits"]/n,2) if n else None
            metric["candidate_pct"]=round(100*metric["candidate_hits"]/n,2) if n else None
    if evaluated and not all(x[:8]>max(c[:8] for c in codes) for x in evaluated):
        raise ValueError("temporal_leakage")
    return {"schema":"HOLE_STRICT_TEMPORAL_HOLDOUT_V1",
            "status":"evaluated_later_date_retrospective" if n else "no_eligible_later_date_holdout",
            "formal":False,"prospective_validation":False,
            "production_forecast_changed":False,
            "training_count":len(codes),"training_max_date":max(x[:8] for x in codes),
            "heldout_comparable":n,"heldout_codes":evaluated,
            "unavailable":unavailable,"scenarios":counts,
            "warning":"Later calendar dates only; retrospective, not independent predeadline proof."}

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
