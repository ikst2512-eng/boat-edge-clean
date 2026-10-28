"""Two parallel research ledgers from the SAME original predeadline forecasts.

Never modifies published predictions. Purchase candidate is an observational,
odds-free experiment and not financial advice, a bet, or production prediction.
"""
import json
from pathlib import Path
from research_model import probabilities
from four_mode_performance import allocate

ROOT=Path(__file__).resolve().parent
MINIMUM_CONFIDENCE=0.70
THRESHOLDS=(MINIMUM_CONFIDENCE,)

def report(root=ROOT):
    root=Path(root)
    h=json.loads((root/"four_mode_performance"/"history-10000.json").read_text(encoding="utf-8"))
    if h.get("schema")!="CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1" or h.get("budget_yen")!=10000:
        raise ValueError("unverified_history")
    ledgers={"all":{"races":0,"hits":0,"investment_yen":0,"return_yen":0},
             **{f"confidence_{int(t*100)}":{"races":0,"hits":0,"investment_yen":0,"return_yen":0} for t in THRESHOLDS}}
    seen=set()
    for r in h["races"]:
        code=r["race_code"]
        if code in seen:raise ValueError("duplicate_race")
        seen.add(code)
        archive=json.loads((root/"four_mode_forecasts"/(code+".json")).read_text(encoding="utf-8"))
        if archive.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1" or archive.get("race_code")!=code:
            raise ValueError("archive_mismatch")
        finish=r["finish"]
        saved=allocate(archive["modes"]["hole"]["tickets"],10000)
        if (r["modes"]["hole"]["hit"]!=(finish in saved) or
            r["modes"]["hole"]["return_yen"]!=saved.get(finish,0)*r["payout_per_100_yen"]//100):
            raise ValueError("settlement_mismatch")
        board=probabilities(archive["input_national_win_rates"])
        mass={i:sum(p for t,p in board if t[0]==i) for i in range(1,7)}
        heads=sorted(mass,key=lambda i:(-mass[i],i))[:2]
        signal=sum(mass[i] for i in heads)
        picks=["-".join(map(str,t)) for t,p in board if t[0] in heads][:20]
        stakes=allocate(picks,10000)
        payout=stakes.get(finish,0)*r["payout_per_100_yen"]//100
        labels=["all"]+[f"confidence_{int(t*100)}" for t in THRESHOLDS if signal>=t]
        for label in labels:
            v=ledgers[label]
            v["races"]+=1
            v["hits"]+=int(finish in stakes)
            v["investment_yen"]+=10000
            v["return_yen"]+=payout
    for v in ledgers.values():
        v["profit_yen"]=v["return_yen"]-v["investment_yen"]
        v["hit_rate_pct"]=round(100*v["hits"]/v["races"],2) if v["races"] else None
        v["roi_pct"]=round(100*v["return_yen"]/v["investment_yen"],2) if v["investment_yen"] else None
        v["participation_pct"]=round(100*v["races"]/len(seen),2) if seen else None
    selected=ledgers["confidence_70"]
    all_races=ledgers["all"]
    skipped={"races":all_races["races"]-selected["races"],
             "hits":all_races["hits"]-selected["hits"],
             "hypothetical_return_yen":all_races["return_yen"]-selected["return_yen"],
             "actual_investment_yen":0}
    if skipped["races"]<0 or skipped["hits"]<0 or skipped["hits"]>skipped["races"]:
        raise ValueError("invalid_skip_counts")
    return {"schema":"CLEAN_DUAL_RESEARCH_V1","sample_races":len(seen),
            "prediction_publication_policy":"all_races_unfiltered",
            "selection_is_observational":True,"odds_free":True,
            "prospectively_validated":False,"investment_is_simulated":True,
            "budget_per_selected_race_yen":10000,
            "minimum_confidence":MINIMUM_CONFIDENCE,
            "below_minimum_policy":"skip_selection_keep_forecast",
            "ledgers":ledgers,
            "skipped_below_70":skipped}
