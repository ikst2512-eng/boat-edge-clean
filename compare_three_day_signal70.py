"""Read-only, payout-gated three-day 70-signal comparison (uncalibrated)."""
import json
from compare_topn_signal70 import compare
from evaluate_clean_prospective_cohort import cohort
DAYS=("20261029","20261030","20261031")
def report(days=DAYS,comparison=compare,all_cohort=cohort):
    totals={name:{"evaluated":0,"pending":0,"verified":0,"hits":{f"top{n}":0 for n in (3,5,10)},"returns":{f"top{n}":0 for n in (3,5,10)}} for name in ("signal_70_plus","below_70")}
    daily=[]
    for day in days:
        data=comparison(day)
        full=all_cohort(day)
        gs=data["groups"]
        if sum(g["evaluated"] for g in gs.values())!=full["counts"]["evaluated"] or sum(g["awaiting_result"] for g in gs.values())!=full["counts"]["awaiting_result"] or sum(g["rejected"] for g in gs.values())!=full["counts"]["audit_rejected"]:
            raise ValueError("strict_vs_signal_cohort_mismatch")
        for name,g in gs.items():
            t=totals[name]
            t["evaluated"]+=g["evaluated"];t["pending"]+=g["awaiting_result"];t["verified"]+=g["payout_verified"]
            for n in (3,5,10):
                k=f"top{n}";t["hits"][k]+=g["hits"][k];t["returns"][k]+=g["returns_yen"][k]
        daily.append({"day":day,"evaluated":full["counts"]["evaluated"],"pending":full["counts"]["awaiting_result"],"payout_verified":sum(g["payout_verified"] for g in gs.values())})
    for t in totals.values():
        if t["verified"]>t["evaluated"]:raise ValueError("bad_payout_coverage")
        t["hit_rate_pct"]={k:round(100*v/t["evaluated"],2) if t["evaluated"] else None for k,v in t["hits"].items()}
        t["roi_pct"]={k:round(100*v/(t["verified"]*5000),2) if t["verified"] else None for k,v in t["returns"].items()}
    overall={"evaluated":sum(g["evaluated"] for g in totals.values()),"pending":sum(g["pending"] for g in totals.values()),"verified":sum(g["verified"] for g in totals.values())}
    overall["hits"]={k:sum(g["hits"][k] for g in totals.values()) for k in ("top3","top5","top10")}
    overall["hit_rate_pct"]={k:round(100*v/overall["evaluated"],2) if overall["evaluated"] else None for k,v in overall["hits"].items()}
    overall["roi_pct"]={k:round(100*sum(g["returns"][k] for g in totals.values())/(overall["verified"]*5000),2) if overall["verified"] else None for k in overall["hits"]}
    return {"schema":"CLEAN_THREE_DAY_SIGNAL70_OBSERVATION_V1","days":daily,"bands":totals,"all":overall,"formal":False,"signal_calibrated":False}
if __name__=="__main__":print(json.dumps(report(),sort_keys=True,ensure_ascii=False))
