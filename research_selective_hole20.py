"""Retrospective selective participation at FIXED, predeclared confidence thresholds.

Odds-free 20-ticket, two-head sensitivity only. Not the real odds-aware
hole strategy; model probabilities are uncalibrated. Do not choose the
best threshold using these same outcomes and call it prospective ROI.
"""
import json
from pathlib import Path
from research_model import probabilities
from research_compare_hole20_heads_odds_free import tickets_under_heads
from four_mode_performance import allocate

ROOT=Path(__file__).resolve().parent
# Predetermined absolute scores; NEVER fit thresholds on race outcomes.
THRESHOLDS=(0.30,0.40,0.50,0.60,0.70)
BUDGET=10000

def confidence(rates):
    board=probabilities(rates)
    heads={i:sum(p for t,p in board if t[0]==i) for i in range(1,7)}
    ranked=sorted(heads,key=lambda i:(-heads[i],i))
    return sum(heads[i] for i in ranked[:2])

def compare(history,root=ROOT):
    if history.get("schema")!="CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1" or history.get("budget_yen")!=BUDGET:
        raise ValueError("verified_10000_history_required")
    stats={str(t):{"purchased":0,"hits":0,"returned_yen":0} for t in THRESHOLDS}
    baseline={"purchased":0,"hits":0,"returned_yen":0}
    seen=set()
    for race in history["races"]:
        code=race["race_code"]
        if code in seen:raise ValueError("duplicate_race")
        seen.add(code)
        archive=json.loads((Path(root)/"four_mode_forecasts"/(code+".json")).read_text(encoding="utf-8"))
        if archive.get("race_code")!=code or archive.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1":
            raise ValueError("archive_mismatch")
        winner=race["finish"]
        official=allocate(archive["modes"]["hole"]["tickets"],BUDGET)
        prior=race["modes"]["hole"]
        if prior["hit"]!=(winner in official) or prior["return_yen"]!=official.get(winner,0)*race["payout_per_100_yen"]//100:
            raise ValueError("official_archive_reconciliation_failed")
        rates=archive["input_national_win_rates"]
        score=confidence(rates)
        picks=allocate(tickets_under_heads(rates,2),BUDGET)
        payout=picks.get(winner,0)*race["payout_per_100_yen"]//100
        for key,record in [(None,baseline)]+[(t,stats[str(t)]) for t in THRESHOLDS if score>=t]:
            record["purchased"]+=1
            record["hits"]+=int(winner in picks)
            record["returned_yen"]+=payout
    for record in (baseline,*stats.values()):
        n=record["purchased"]; cost=n*BUDGET
        record["spent_yen"]=cost
        record["net_yen"]=record["returned_yen"]-cost
        record["hit_rate_pct"]=round(100*record["hits"]/n,2) if n else None
        record["roi_pct"]=round(100*record["returned_yen"]/cost,2) if n else None
        record["purchase_rate_pct"]=round(100*n/len(seen),2) if seen else None
    return {"schema":"CLEAN_RESEARCH_SELECTIVE_HOLE20_V1",
            "selection_signal":"top_two_first_place_probability_mass_uncalibrated",
            "odds_free":True,"research_only":True,"prospectively_validated":False,
            "sample_races":len(seen),"budget_yen":BUDGET,
            "all_races":baseline,"thresholds":stats}

if __name__=="__main__":
    h=json.loads((ROOT/"four_mode_performance"/"history-10000.json").read_text(encoding="utf-8"))
    print(json.dumps(compare(h),ensure_ascii=False,indent=2))
