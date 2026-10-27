"""Exploratory same-cohort parameter comparison, NOT out-of-sample accuracy.

Uses only frozen CLEAN research inputs and post-race confirmed finish orders.
No model is promoted from in-sample results.
"""
import json
from pathlib import Path
from research_model import probabilities

ROOT=Path(__file__).resolve().parent
BETAS=(0.0,0.2,0.4,0.6,0.8,1.0,1.4)

def evaluate(day="20261027",root=ROOT):
    paired=[]
    for prediction in sorted((root/"research_snapshots").glob(day+"*.json")):
        result=root/"confirmed_results"/prediction.name
        if not result.is_file():continue
        p=json.loads(prediction.read_text(encoding="utf-8"))
        r=json.loads(result.read_text(encoding="utf-8"))
        if p.get("race_code")!=prediction.stem or r.get("race_code")!=prediction.stem or p.get("status")!="research" or p.get("validated") is not False or r.get("status")!="confirmed":
            raise ValueError("invalid paired race "+prediction.stem)
        original=["-".join(map(str,t)) for t,_ in probabilities(p["national_win_rates"],beta=0.4)[:10]]
        if p.get("predictions")!=original:
            raise ValueError("not reproducible "+prediction.stem)
        winner="-".join(map(str,r["finish_order"]))
        paired.append((p["national_win_rates"],winner))
    if not paired:raise ValueError("no paired races")
    summary=[]
    for beta in BETAS:
        totals={3:0,5:0,10:0}
        for rates,winner in paired:
            ten=["-".join(map(str,t)) for t,_ in probabilities(rates,beta=beta)[:10]]
            for k in totals:
                totals[k]+=winner in ten[:k]
        summary.append({"beta":beta,"top3":totals[3],"top5":totals[5],"top10":totals[10],
                       "top3_pct":round(totals[3]/len(paired)*100,2),
                       "top5_pct":round(totals[5]/len(paired)*100,2),
                       "top10_pct":round(totals[10]/len(paired)*100,2)})
    return {"date":day,"n":len(paired),"baseline_beta":0.4,"results":summary,
            "interpretation":"IN-SAMPLE exploratory comparison on a single dated cohort. Do not select/promote model without forward out-of-sample validation."}

if __name__=="__main__":
    report=evaluate()
    print(json.dumps(report,ensure_ascii=False))
    Path("parameter_comparison_20261027.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
