"""Separate day-by-day observational validation; never blend a discovery day into holdout."""
import argparse
import json
from compare_topn_signal70 import compare

def report(days, evaluator=compare):
    if not days or len(set(days))!=len(days):
        raise ValueError("unique days required")
    if any(not isinstance(d,str) or len(d)!=8 or not d.isascii() or not d.isdigit() or not d.startswith("20") for d in days):
        raise ValueError("invalid day")
    rows=[]
    for day in days:
        data=evaluator(day)
        if data.get("schema")!="CLEAN_TOPN_SIGNAL70_RESEARCH_V1" or data.get("day_jst")!=day or data.get("signal_is_empirical_confidence") is not False:
            raise ValueError("invalid source report")
        rows.append({"day_jst":day,"role":"discovery" if day=="20261029" else ("earlier_exploratory" if day<"20261029" else "later_holdout"),
                     "archived":data["archived"],"groups":data["groups"]})
    holdouts=[r for r in rows if r["role"]=="later_holdout"]
    return {"schema":"CLEAN_SIGNAL70_DAYWISE_V1","policy_reference_day":"20261029",
            "threshold":0.70,"calibrated_confidence":False,"formal":False,
            "later_holdout_days":len(holdouts),"days":rows}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("days",nargs="+");args=p.parse_args()
    print(json.dumps(report(args.days),ensure_ascii=False,sort_keys=True))
