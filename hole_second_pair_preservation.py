"""Outcome-blind research: preserve existing pair coverage when adding a second-place pair."""
import json
from pathlib import Path
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run

ROOT=Path(__file__).resolve().parent
TOPS=(3,5,10)

def preserve_pair_coverage(hole, donor, max_tickets=10, protect_top=3):
    """Swap a donor into a lower-ranked slot whose 1-2 pair remains covered.

    Does not consult results. Protect early ranks; keep number of tickets fixed.
    Avoid sacrificing the *only* representative of an existing first/second pair.
    """
    base=list(hole[:max_tickets])
    if not (0 <= protect_top < len(base)):
        return base
    pairs=[tuple(combo.split("-")[:2]) for combo in base]
    heads={p[0] for p in pairs}
    existing=set(base)
    selected=next((ticket for ticket in donor if ticket not in existing
                   and ticket.split("-")[0] in heads
                   and tuple(ticket.split("-")[:2]) not in pairs), None)
    if selected is None:
        return base
    replacement=next((i for i in range(len(base)-1, protect_top-1, -1)
                      if pairs.count(pairs[i]) >= 2), None)
    if replacement is None:
        return base
    base[replacement]=selected
    return base

def run(root=ROOT,limit=120):
    root=Path(root)
    cohort=cohort_run(root=root,limit=limit)
    if cohort.get("status")!="historical_research_only":
        return {"status":"no_paired_archives","formal":False}
    rows=[]
    for code in cohort["cohort_codes"]:
        result=compare_race(code,root)
        if result.get("status")!="historical_comparison_only":
            continue
        status,archive=archived_four_modes(code,root)
        if status!=200:
            raise ValueError("invalid archive")
        modes={name:[x["combo"] for x in archive["modes"][name]["tickets"]]
               for name in ("hole","hit","balance")}
        baseline=modes["hole"][:10]
        donors={"hit":modes["hit"],"balance":modes["balance"],
                "hit_balance":list(dict.fromkeys(modes["hit"]+modes["balance"]))}
        winner=result["winning_ticket"]
        comparisons={}
        for source,donor in donors.items():
            for protect in (0,3,5):
                key=f"{source}_protect{protect}"
                picks=preserve_pair_coverage(baseline,donor,protect_top=protect)
                if len(picks)!=len(baseline) or len(set(picks))!=len(picks):
                    raise ValueError("budget or uniqueness failure")
                before_pairs={tuple(x.split("-")[:2]) for x in baseline}
                after_pairs={tuple(x.split("-")[:2]) for x in picks}
                if not before_pairs.issubset(after_pairs):
                    raise ValueError("pair coverage regression")
                comparisons[key]={"changed":picks!=baseline,
                                  "added":[p for p in picks if p not in baseline],
                                  "removed":[p for p in baseline if p not in picks],
                                  "gained":[f"top{k}" for k in TOPS if winner in picks[:k] and winner not in baseline[:k]],
                                  "lost":[f"top{k}" for k in TOPS if winner not in picks[:k] and winner in baseline[:k]]}
        rows.append({"race_code":code,"winner":winner,"scenarios":comparisons})
    keys=[f"{source}_protect{protect}" for source in ("hit","balance","hit_balance") for protect in (0,3,5)]
    summary={}
    for key in keys:
        summary[key]={"changed":sum(int(r["scenarios"][key]["changed"]) for r in rows),
                      "topn":{f"top{k}":{"gained":sum(f"top{k}" in r["scenarios"][key]["gained"] for r in rows),
                                        "lost":sum(f"top{k}" in r["scenarios"][key]["lost"] for r in rows)}
                              for k in TOPS}}
    return {"status":"historical_research_only","formal":False,"simulated_only":True,
            "production_forecast_changed":False,"remote_first_seen_verified":False,
            "comparable":len(rows),"scenarios":summary,"race_audit":rows,
            "warning":"Historical in-sample comparison only; not prospective proof. Pair protection does not guarantee protection of individual winning tickets."}
if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
