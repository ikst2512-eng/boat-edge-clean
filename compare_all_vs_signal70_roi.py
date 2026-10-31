"""Compare all eligible races with a fixed, uncalibrated 70-signal selection."""
import json
from aggregate_prospective_topn import summary
from compare_topn_signal70 import compare

DAYS=("20261029","20261030","20261031")

def run(days=DAYS):
    baseline=summary(list(days))
    selected={"evaluated":0,"payout_verified":0,"awaiting_result":0,"rejected":0,
              "hits":{f"top{n}":0 for n in (3,5,10)},
              "returns_yen":{f"top{n}":0 for n in (3,5,10)}}
    per_day=[]
    for day in days:
        groups=compare(day)["groups"]
        chosen=groups["signal_70_plus"]
        other=groups["below_70"]
        aggregate_day=next(d for d in baseline["days"] if d["day_jst"]==day)
        for key in ("evaluated","awaiting_result","rejected"):
            if chosen[key]+other[key] != aggregate_day["counts"][{"rejected":"audit_rejected"}.get(key,key)]:
                raise ValueError("audit cohort mismatch: "+day+" "+key)
        for key in ("evaluated","payout_verified","awaiting_result","rejected"):
            selected[key]+=chosen[key]
        for k in selected["hits"]:
            selected["hits"][k]+=chosen["hits"][k]
            selected["returns_yen"][k]+=chosen["returns_yen"][k]
        per_day.append({"date":day,"eligible":chosen["evaluated"],"all_evaluated":aggregate_day["counts"]["evaluated"],
                        "payout_verified":chosen["payout_verified"],"top10_hits":chosen["hits"]["top10"]})
    for n in (3,5,10):
        key=f"top{n}"
        selected.setdefault("hit_rate_pct",{})[key]=(round(100*selected["hits"][key]/selected["evaluated"],2)
            if selected["evaluated"] else None)
        selected.setdefault("roi_pct",{})[key]=(round(100*selected["returns_yen"][key]/
            (selected["payout_verified"]*5000),2) if selected["payout_verified"] else None)
    return {"schema":"CLEAN_ALL_VS_SIGNAL70_VERIFIED_ROI_V1","days":per_day,
            "baseline":{"evaluated":baseline["counts"]["evaluated"],
                "payout_verified":baseline["roi"]["top10"]["races"],
                "hits":baseline["hits"],"hit_rate_pct":baseline["hit_rate_pct"],
                "roi_pct":{k:v["roi_pct"] for k,v in baseline["roi"].items()}},
            "signal_70_plus":selected,
            "warning":"Research-only retrospective simulation; 70 is an uncalibrated signal, not 70% confidence; no selection-policy promotion."}

if __name__=="__main__":
    print(json.dumps(run(),sort_keys=True))
