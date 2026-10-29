"""Read-only prospective top-3/5/10 cohort comparison; pending != loss."""
import argparse
import json
from pathlib import Path
from evaluate_clean_prospective import evaluate

ROOT=Path(__file__).resolve().parent

def cohort(day, root=ROOT, scorer=evaluate):
    if not (len(day)==8 and day.isascii() and day.isdigit() and day.startswith("20")):
        raise ValueError("invalid day")
    paths=sorted((Path(root)/"prospective_predictions").glob(day+"????.json"))
    counts={"archives":len(paths),"evaluated":0,"awaiting_result":0,"audit_rejected":0}
    hits={"top3":0,"top5":0,"top10":0}
    rejected=[]
    for path in paths:
        try:
            outcome=scorer(path.stem,root)
            if outcome["status"]=="result_unavailable":
                counts["awaiting_result"]+=1
                continue
            if outcome["status"]!="evaluated" or outcome.get("formal") is not False or outcome.get("audited") is not True:
                raise ValueError("untrusted evaluation")
            counts["evaluated"]+=1
            for n in hits:
                hits[n]+=int(outcome[n] is True)
        except (ValueError,KeyError,TypeError,OSError) as exc:
            counts["audit_rejected"]+=1
            rejected.append({"race_code":path.stem,"reason":str(exc)[:100]})
    denominator=counts["evaluated"]
    return {"schema":"CLEAN_PROSPECTIVE_TOPN_COHORT_V1","day_jst":day,
            "formal":False,"simulated_only":True,"first_add_audit_required":True,
            "counts":counts,"hits":hits,
            "hit_rate_pct":{n:round(100*v/denominator,2) if denominator else None for n,v in hits.items()},
            "unverified_races_excluded":True,"rejected":rejected}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("day");args=p.parse_args()
    print(json.dumps(cohort(args.day),ensure_ascii=False,sort_keys=True))
