"""Offline-only replay of requested mode caps against existing verified history.

Reconstructs probabilities from original saved national win rates. Results are
in-sample diagnostics, NOT proof that a new forecast existed pre-deadline.
Hole requires actual time-stamped pre-deadline odds; never substitute payout.
"""
import json
from pathlib import Path
from research_model import probabilities
from research_four_mode_roles import research_modes
from four_mode_performance import allocate

ROOT=Path(__file__).resolve().parent
BUDGET=10000
MODES=("narrow","hit","balance")

def replay(history,root=ROOT):
    if history.get("schema")!="CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1" or history.get("budget_yen")!=BUDGET:
        raise ValueError("verified_history_required")
    rows=history["races"]
    if len({r["race_code"] for r in rows})!=len(rows):
        raise ValueError("duplicate_races")
    result={m:{"hits":0,"return_yen":0,"invested_yen":0} for m in MODES}
    result["hole"]={"status":"not_scored_no_predeadline_odds","hits":None,"return_yen":None}
    for race in rows:
        code=race["race_code"]
        archive=json.loads((root/"four_mode_forecasts"/(code+".json")).read_text(encoding="utf-8"))
        if archive.get("race_code")!=code or archive.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1":
            raise ValueError("archive_mismatch")
        if "modes" in archive:
            for original_mode in ("hit","balance","hole","narrow"):
                recorded = race.get("modes",{}).get(original_mode)
                if recorded is None:
                    raise ValueError("saved_baseline_required")
                baseline = allocate(archive["modes"][original_mode]["tickets"], BUDGET)
                expected = baseline.get(race["finish"],0)*race["payout_per_100_yen"]//100
                if recorded["hit"] != (race["finish"] in baseline) or recorded["return_yen"] != expected:
                    raise ValueError("baseline_reconciliation_failed")
        rates=archive.get("input_national_win_rates")
        if not isinstance(rates,list) or len(rates)!=6:
            raise ValueError("saved_inputs_missing")
        modes=research_modes(probabilities(rates))
        if modes["hole"]["status"]!="odds_required":
            raise ValueError("odds_guard_failed")
        for m in MODES:
            combos=[t["combo"] for t in modes[m]["tickets"]]
            q,rem=divmod(BUDGET//100,len(combos))
            winner=race["finish"]
            idx=combos.index(winner) if winner in combos else -1
            stake=100*(q+(idx<rem)) if idx>=0 else 0
            result[m]["hits"]+=int(idx>=0)
            result[m]["return_yen"]+=stake*race["payout_per_100_yen"]//100
            result[m]["invested_yen"]+=BUDGET
    for m in MODES:
        x=result[m]
        x["hit_rate_pct"]=round(100*x["hits"]/len(rows),2) if rows else None
        x["roi_pct"]=round(100*x["return_yen"]/x["invested_yen"],2) if rows else None
        x["net_yen"]=x["return_yen"]-x["invested_yen"]
    return {"research_only":True,"historical_reconstruction":True,"prospectively_validated":False,
            "sample_races":len(rows),"budget_yen":BUDGET,"modes":result}

if __name__=="__main__":
    history=json.loads((ROOT/"four_mode_performance"/"history-10000.json").read_text(encoding="utf-8"))
    print(json.dumps(replay(history),ensure_ascii=False,indent=2))
