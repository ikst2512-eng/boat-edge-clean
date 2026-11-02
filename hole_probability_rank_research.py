"""Research-only frozen estimated-score ranking. Scores are uncalibrated, not probabilities."""
import json
from collections import defaultdict
from pathlib import Path
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from hole_upper_rank_pair_protection import propose

TOPS=(3,5,10)
POLICIES=("ticket_p","pair_sum_p","pair_max_p")
def sorted_donor(hit,balance,policy):
    if policy not in POLICIES: raise ValueError("policy")
    rows={}
    for name,source in (("hit",hit),("balance",balance)):
        for i,item in enumerate(source):
            combo=item["combo"];score=item["p"]
            if combo not in rows:rows[combo]={"p":score,"rank":i}
            else:
                rows[combo]["p"]=max(rows[combo]["p"],score)
                rows[combo]["rank"]=min(rows[combo]["rank"],i)
    pair_sum=defaultdict(float);pair_max=defaultdict(float)
    for combo,data in rows.items():
        pair=tuple(combo.split("-")[:2])
        pair_sum[pair]+=data["p"]
        pair_max[pair]=max(pair_max[pair],data["p"])
    def score(t):
        pair=tuple(t.split("-")[:2])
        return {"ticket_p":rows[t]["p"],"pair_sum_p":pair_sum[pair],
                "pair_max_p":pair_max[pair]}[policy]
    return sorted(rows,key=lambda t:(-score(t),rows[t]["rank"],t))
def analyze(codes,root):
    results={key:{"changed":0,"topn":{f"top{k}":{"before":0,"after":0,
             "gained":0,"lost":0} for k in TOPS}} for key in POLICIES}
    for code in codes:
        status,record=archived_four_modes(code,root)
        actual=compare_race(code,root)
        if status!=200 or actual.get("status")!="historical_comparison_only":
            raise ValueError("invalid_source_"+code)
        modes=record["modes"];base=[x["combo"] for x in modes["hole"]["tickets"]][:10]
        winning=actual["winning_ticket"]
        for policy in POLICIES:
            donor=sorted_donor(modes["hit"]["tickets"],modes["balance"]["tickets"],policy)
            updated=propose(base,donor,3)
            if len(updated)!=len(base) or len(set(updated))!=len(updated):
                raise ValueError("budget")
            m=results[policy];m["changed"]+=int(base!=updated)
            for k in TOPS:
                a=winning in base[:k];b=winning in updated[:k];t=m["topn"][f"top{k}"]
                t["before"]+=int(a);t["after"]+=int(b)
                t["gained"]+=int(b and not a);t["lost"]+=int(a and not b)
    for m in results.values():
        for t in m["topn"].values():
            t["net"]=t["gained"]-t["lost"]
            if t["after"]-t["before"]!=t["net"]:raise ValueError("attribution")
    return {"n":len(codes),"policies":results}
def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    c=cohort_run(root=root,limit=120)
    if c.get("status")!="historical_research_only":
        return {"status":"no_cohort","formal":False}
    d=date_blocks(c["cohort_codes"])
    if d["status"]!="date_blocked":
        return {"status":"no_date_blocks","formal":False}
    return {"status":"historical_exploratory","formal":False,
            "independent_holdout":False,"prospective_validation":False,
            "production_forecast_changed":False,"score_calibrated":False,
            "earlier":analyze(d["earlier"],root),"later":analyze(d["later"],root),
            "warning":"Previously studied dates; p is an uncalibrated model score. No prospective efficacy claim."}
if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
