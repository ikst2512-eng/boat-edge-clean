"""Fixed, pre-result alternative 12-pick hit selections for offline research.

Do not pick a policy after looking at its evaluation sample and claim live gain.
"""
from research_model import probabilities

def candidates(rates, policy="probability"):
    rows=[("-".join(map(str,t)),p) for t,p in probabilities(rates)]
    if policy=="probability":
        picks=rows[:12]
    elif policy=="branch_diversity":
        remaining=dict(rows)
        picks=[]
        while len(picks)<12:
            firsts={x[0][0] for x in picks}
            pairs={x[0][:3] for x in picks}
            best=max(remaining,key=lambda c:(remaining[c]*(1+(0.30 if c[0] not in firsts else 0)+(0.15 if c[:3] not in pairs else 0)),
                                            -int(c[0]),-int(c[2]),-int(c[4])))
            picks.append((best,remaining.pop(best)))
    elif policy=="third_diversity":
        remaining=dict(rows)
        picks=[]
        while len(picks)<12:
            third_by_pair={(x[0][0],x[0][2]) for x in picks}
            firsts={x[0][0] for x in picks}
            best=max(remaining,key=lambda c:(remaining[c]*(1+(0.18 if (c[0],c[2]) not in third_by_pair else 0)
                                                   +(0.10 if c[0] not in firsts else 0)),
                                            -int(c[0]),-int(c[2]),-int(c[4])))
            picks.append((best,remaining.pop(best)))
    else:
        raise ValueError("unknown_policy")
    if len(picks)!=12 or len(set(c for c,p in picks))!=12:
        raise ValueError("invalid_candidate")
    return [c for c,p in picks]

def replay(history, root):
    import json
    from pathlib import Path
    from four_mode_performance import allocate
    if history.get("schema")!="CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1" or history.get("budget_yen")!=10000:
        raise ValueError("verified_10000_history_required")
    policies=("probability","branch_diversity","third_diversity")
    totals={p:{"hits":0,"return_yen":0} for p in policies}
    seen=set()
    for race in history["races"]:
        code=race["race_code"]
        if code in seen:raise ValueError("duplicate_race")
        seen.add(code)
        archive=json.loads((Path(root)/"four_mode_forecasts"/(code+".json")).read_text(encoding="utf-8"))
        if archive.get("race_code")!=code or archive.get("schema")!="CLEAN_FOUR_MODES_PREDEADLINE_V1":
            raise ValueError("archive_mismatch")
        original=allocate(archive["modes"]["hit"]["tickets"],10000)
        verified=race["modes"]["hit"]
        winner=race["finish"]
        if verified["hit"]!=(winner in original) or verified["return_yen"]!=original.get(winner,0)*race["payout_per_100_yen"]//100:
            raise ValueError("original_settlement_mismatch")
        rates=archive["input_national_win_rates"]
        for policy in policies:
            tickets=candidates(rates,policy)
            stakes=allocate(tickets,10000)
            totals[policy]["hits"]+=int(winner in stakes)
            totals[policy]["return_yen"]+=stakes.get(winner,0)*race["payout_per_100_yen"]//100
    for stat in totals.values():
        cost=len(seen)*10000
        stat["hit_rate_pct"]=round(stat["hits"]/len(seen)*100,2) if seen else None
        stat["roi_pct"]=round(stat["return_yen"]/cost*100,2) if cost else None
        stat["net_yen"]=stat["return_yen"]-cost
    return {"schema":"CLEAN_RESEARCH_HIT12_BRANCHES_V1","research_only":True,
            "prospectively_validated":False,"sample_races":len(seen),"policies":totals}

if __name__=="__main__":
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parent
    h=json.loads((root/"four_mode_performance"/"history-10000.json").read_text(encoding="utf-8"))
    print(json.dumps(replay(h,root),ensure_ascii=False,indent=2))
