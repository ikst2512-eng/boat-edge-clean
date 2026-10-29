"""Read-only prospective top-3/5/10 cohort comparison; pending != loss."""
import argparse
import json
from pathlib import Path
from evaluate_clean_prospective import evaluate

ROOT=Path(__file__).resolve().parent

def verified_payout(code, root):
    path=Path(root)/"four_mode_performance"/"verified_races"/(code+".json")
    if path.is_symlink() or not path.is_file() or path.stat().st_size>20000:
        return None
    try:
        record=json.loads(path.read_text(encoding="utf-8"))
        payout=record.get("official_payout_yen_per_100")
        if (record.get("schema")!="CLEAN_VERIFIED_FOUR_MODE_RACE_V1" or
            record.get("race_code")!=code or record.get("verified") is not True or
            record.get("simulated_only") is not True or type(payout) is not int or payout<100):
            return None
        return record["official_finish"],payout
    except (ValueError,KeyError,TypeError,OSError):
        return None

def cohort(day, root=ROOT, scorer=evaluate):
    if not (len(day)==8 and day.isascii() and day.isdigit() and day.startswith("20")):
        raise ValueError("invalid day")
    paths=sorted((Path(root)/"prospective_predictions").glob(day+"????.json"))
    counts={"archives":len(paths),"evaluated":0,"awaiting_result":0,"audit_rejected":0}
    hits={"top3":0,"top5":0,"top10":0}
    rejected=[]
    awaiting_result_codes=[]
    payout_unavailable=0
    roi={key:{"races":0,"invested_yen":0,"return_yen":0} for key in hits}
    for path in paths:
        try:
            outcome=scorer(path.stem,root)
            if outcome["status"]=="result_unavailable":
                counts["awaiting_result"]+=1
                awaiting_result_codes.append(path.stem)
                continue
            if outcome["status"]!="evaluated" or outcome.get("formal") is not False or outcome.get("audited") is not True:
                raise ValueError("untrusted evaluation")
            counts["evaluated"]+=1
            for n in hits:
                hits[n]+=int(outcome[n] is True)
            evidence=verified_payout(path.stem,root)
            if evidence is None or evidence[0]!=outcome.get("winning_ticket"):
                payout_unavailable+=1
            else:
                price=evidence[1]
                for number,key in ((3,"top3"),(5,"top5"),(10,"top10")):
                    unit=(5000//number//100)*100
                    bonus=(5000-unit*number)//100
                    rank=outcome.get("rank")
                    stake=unit+(100 if rank is not None and rank<=bonus else 0)
                    roi[key]["races"]+=1
                    roi[key]["invested_yen"]+=5000
                    if rank is not None and rank<=number:
                        roi[key]["return_yen"]+=stake*price//100
        except (ValueError,KeyError,TypeError,OSError) as exc:
            counts["audit_rejected"]+=1
            rejected.append({"race_code":path.stem,"reason":str(exc)[:100]})
    denominator=counts["evaluated"]
    return {"schema":"CLEAN_PROSPECTIVE_TOPN_COHORT_V1","day_jst":day,
            "formal":False,"simulated_only":True,"first_add_audit_required":True,
            "counts":counts,"hits":hits,
            "hit_rate_pct":{n:round(100*v/denominator,2) if denominator else None for n,v in hits.items()},
            "unverified_races_excluded":True,"rejected":rejected,
            "awaiting_result_race_codes":awaiting_result_codes,
            "payout_unavailable":payout_unavailable,"simulated_budget_yen":5000,
            "roi":{k:{**v,"roi_pct":round(100*v["return_yen"]/v["invested_yen"],2) if v["invested_yen"] else None} for k,v in roi.items()}}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("day");args=p.parse_args()
    print(json.dumps(cohort(args.day),ensure_ascii=False,sort_keys=True))
