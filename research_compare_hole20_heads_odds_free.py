"""Odds-free sensitivity analysis of 20 trifecta tickets under 1/2/3 heads.

NOT the odds-aware hole model. No betting recommendation or prospective proof.
All variants select tickets from archived pre-race input rates only.
One-head + 20 tickets is exhaustive: 1 first-place boat has exactly 20
possible second/third combinations, so first-place capture equals trifecta hit.
For two/three heads, 20 tickets is partial coverage and can miss combinations.
"""
import json
from pathlib import Path
from research_model import probabilities
from four_mode_performance import allocate

ROOT=Path(__file__).resolve().parent

def tickets_under_heads(rates, heads, limit=20):
    if type(heads) is not int or heads not in (1,2,3):
        raise ValueError("heads_must_be_1_to_3")
    if type(limit) is not int or limit!=20:
        raise ValueError("fixed_20_ticket_comparison_only")
    board=probabilities(rates)
    mass={i:sum(p for t,p in board if t[0]==i) for i in range(1,7)}
    allowed=set(sorted(mass,key=lambda i:(-mass[i],i))[:heads])
    choices=["-".join(map(str,t)) for t,p in board if t[0] in allowed][:limit]
    if len(choices)!=limit or len(set(choices))!=limit:
        raise ValueError("incomplete_candidate")
    return choices

def compare(history,root=ROOT):
    if history.get("schema")!="CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1" or history.get("budget_yen")!=10000:
        raise ValueError("verified_history_required")
    metrics={str(n):{"hits":0,"return_yen":0,"head_captured":0} for n in (1,2,3)}
    seen=set()
    for race in history["races"]:
        code=race["race_code"]
        if code in seen:raise ValueError("duplicate_race")
        seen.add(code)
        archive=json.loads((Path(root)/"four_mode_forecasts"/(code+".json")).read_text(encoding="utf-8"))
        if archive.get("race_code")!=code or archive.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1":
            raise ValueError("archive_mismatch")
        winner=race["finish"]
        # Reconcile the original full saved hole forecast with independent verified payoff.
        original=allocate(archive["modes"]["hole"]["tickets"],10000)
        verified=race["modes"]["hole"]
        if verified["hit"]!=(winner in original) or verified["return_yen"]!=original.get(winner,0)*race["payout_per_100_yen"]//100:
            raise ValueError("original_hole_settlement_mismatch")
        rates=archive["input_national_win_rates"]
        for n in (1,2,3):
            combos=tickets_under_heads(rates,n)
            stakes=allocate(combos,10000)
            # Head inclusion across the entire first-place candidate pool, not only tickets.
            board=probabilities(rates)
            mass={i:sum(p for t,p in board if t[0]==i) for i in range(1,7)}
            allowed=set(sorted(mass,key=lambda i:(-mass[i],i))[:n])
            metrics[str(n)]["head_captured"]+=int(int(winner[0]) in allowed)
            metrics[str(n)]["hits"]+=int(winner in stakes)
            metrics[str(n)]["return_yen"]+=stakes.get(winner,0)*race["payout_per_100_yen"]//100
    cost=len(seen)*10000
    for v in metrics.values():
        v["hit_rate_pct"]=round(100*v["hits"]/len(seen),2) if seen else None
        v["roi_pct"]=round(100*v["return_yen"]/cost,2) if cost else None
        v["net_yen"]=v["return_yen"]-cost
    return {"schema":"CLEAN_RESEARCH_ODDS_FREE_HOLE20_HEADS_V1","research_only":True,
            "odds_based_hole_evaluated":False,"prospectively_validated":False,
            "ticket_count":20,"sample_races":len(seen),"yen_per_race":10000,
            "head_variants":metrics}

if __name__=="__main__":
    h=json.loads((ROOT/"four_mode_performance"/"history-10000.json").read_text(encoding="utf-8"))
    print(json.dumps(compare(h),ensure_ascii=False,indent=2))
