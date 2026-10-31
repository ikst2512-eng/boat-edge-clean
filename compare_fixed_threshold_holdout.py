"""Read-only fixed-threshold comparison. Discovery and next-day holdout stay separate."""
import json
from pathlib import Path
from compare_topn_signal70 import head_mass
from evaluate_clean_prospective import evaluate
from evaluate_clean_prospective_cohort import verified_payout

THRESHOLDS=(0.70,0.75,0.80)
ROOT=Path(__file__).resolve().parent

def report(days=("20261029","20261030"),root=ROOT,scorer=evaluate,signal=head_mass,payout=verified_payout):
    if tuple(days)!=("20261029","20261030"):
        raise ValueError("fixed discovery and holdout dates required")
    output=[]
    for day in days:
        rows={str(int(t*100)):{"selected":0,"hits":{f"top{n}":0 for n in (3,5,10)},
             "payout_verified":0,"return_yen":{f"top{n}":0 for n in (3,5,10)}} for t in THRESHOLDS}
        examined=pending=rejected=0
        all_hits={f'top{n}':0 for n in (3,5,10)}
        for path in sorted((Path(root)/"prospective_predictions").glob(day+"????.json")):
            try:
                record=json.loads(path.read_text(encoding="utf-8"))
                score=signal(record["national_win_rates"])
                if type(score) not in (int,float) or not 0<=score<=1:
                    raise ValueError("invalid signal")
                result=scorer(path.stem,root)
                if result["status"]=="result_unavailable":
                    pending+=1
                    continue
                rank=result.get("rank")
                if result.get("status")!="evaluated" or result.get("audited") is not True or result.get("formal") is not False or (rank is not None and (type(rank) is not int or not 1<=rank<=10)):
                    raise ValueError("untrusted result")
                if any(type(result.get(f"top{n}")) is not bool or result[f"top{n}"] is not (rank is not None and rank<=n) for n in (3,5,10)):
                    raise ValueError("contradictory result")
                examined+=1
                for n in (3,5,10):
                    all_hits[f'top{n}']+=int(rank is not None and rank<=n)
                proof=payout(path.stem,root)
                trusted=proof is not None and proof[0]==result.get("winning_ticket")
                for t in THRESHOLDS:
                    if score<t: continue
                    row=rows[str(int(t*100))]
                    row["selected"]+=1
                    for n in (3,5,10):
                        row["hits"][f"top{n}"]+=int(rank is not None and rank<=n)
                    if trusted:
                        row["payout_verified"]+=1
                        for n in (3,5,10):
                            unit=(5000//n//100)*100
                            extra=(5000-unit*n)//100
                            if rank is not None and rank<=n:
                                row["return_yen"][f"top{n}"]+=(unit+(100 if rank<=extra else 0))*proof[1]//100
            except (ValueError,KeyError,TypeError,OSError):
                rejected+=1
        for row in rows.values():
            row["hit_rate_pct"]={k:round(100*v/row["selected"],2) if row["selected"] else None for k,v in row["hits"].items()}
            row["selected_pct"]=round(100*row["selected"]/examined,2) if examined else None
            row["lift_pp"]={key:round(100*row["hits"][key]/row["selected"]-100*all_hits[key]/examined,2) if row["selected"] and examined else None for key in all_hits}
            row["roi_pct"]={k:round(100*v/(row["payout_verified"]*5000),2) if row["payout_verified"] else None for k,v in row["return_yen"].items()}
        output.append({"day":day,"role":"discovery" if day=="20261029" else "later_holdout",
                       "evaluated":examined,"pending":pending,"rejected":rejected,"all_hit_rate_pct":{key:round(100*value/examined,2) if examined else None for key,value in all_hits.items()},"thresholds":rows})
    return {"schema":"CLEAN_FIXED_THRESHOLD_HOLDOUT_V1","formal":False,"signal_calibrated":False,
            "thresholds_fixed":[70,75,80],"days":output,"budget_yen_per_race":5000,
            "not_a_betting_recommendation":True}

if __name__=="__main__":
    print(json.dumps(report(),ensure_ascii=False,sort_keys=True))
