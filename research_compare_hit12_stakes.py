"""Compare fixed 12-ticket ¥10,000 staking without changing coverage.
Research-only, in-sample, and no production predictions are edited.
"""
import json
from pathlib import Path
from four_mode_performance import allocate
ROOT=Path(__file__).resolve().parent
POLICIES={"equal":None,"top3_double":3,"top5_double":5}
def weights(tickets,n):
    combos=[v["combo"] for v in tickets]
    units=100-len(combos)
    w=[2 if i<n else 1 for i in range(len(combos))]
    den=sum(w)
    part=[units*x//den for x in w]
    remainder=units-sum(part)
    order=sorted(range(len(w)),key=lambda i:(-(units*w[i]%den),i))
    for i in order[:remainder]:part[i]+=1
    return {combo:100*(1+part[i]) for i,combo in enumerate(combos)}
def compare(history,root=ROOT):
    if history.get("schema")!="CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1" or history.get("budget_yen")!=10000:
        raise ValueError("verified_10000_history_required")
    totals={k:{"hits":0,"return_yen":0} for k in POLICIES}
    seen=set()
    for race in history["races"]:
        code=race["race_code"]
        if code in seen:raise ValueError("duplicate_race")
        seen.add(code)
        archive=json.loads((root/"four_mode_forecasts"/(code+".json")).read_text(encoding="utf-8"))
        if archive.get("race_code")!=code:raise ValueError("archive_mismatch")
        picks=archive["modes"]["hit"]["tickets"][:12]
        base=allocate(picks,10000)
        for name,n in POLICIES.items():
            stakes=base if n is None else weights(picks,n)
            winner=race["finish"]
            totals[name]["hits"]+=int(winner in stakes)
            totals[name]["return_yen"]+=stakes.get(winner,0)*race["payout_per_100_yen"]//100
    for data in totals.values():
        investment=len(seen)*10000
        data["hit_rate_pct"]=round(100*data["hits"]/len(seen),2) if seen else None
        data["roi_pct"]=round(100*data["return_yen"]/investment,2) if seen else None
        data["net_yen"]=data["return_yen"]-investment
    return {"research_only":True,"prospectively_validated":False,"sample_races":len(seen),
            "ticket_cap":12,"budget_yen":10000,"policies":totals}
if __name__=="__main__":
    history=json.loads((ROOT/"four_mode_performance"/"history-10000.json").read_text(encoding="utf-8"))
    print(json.dumps(compare(history),ensure_ascii=False,indent=2))
