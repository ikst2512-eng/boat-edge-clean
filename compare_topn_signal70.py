"""Observational top-N split by UNCALIBRATED top-two-head model mass.

Not an empirical 70% probability, not validated purchase recommendation.
Only independently audited prospective forecasts and confirmed results score.
"""
import json
from pathlib import Path
from evaluate_clean_prospective import evaluate
from research_model import probabilities
from evaluate_clean_prospective_cohort import verified_payout

ROOT=Path(__file__).resolve().parent

def head_mass(rates):
    board=probabilities(rates)
    mass={i:sum(p for t,p in board if t[0]==i) for i in range(1,7)}
    return sum(sorted(mass.values(),reverse=True)[:2])

def compare(day,root=ROOT,scorer=evaluate,signal=head_mass):
    if not isinstance(day,str) or len(day)!=8 or not day.isascii() or not day.isdigit() or not day.startswith("20"):
        raise ValueError("invalid day")
    paths=sorted((Path(root)/"prospective_predictions").glob(day+"????.json"))
    groups={g:{"evaluated":0,"awaiting_result":0,"rejected":0,"payout_verified":0,
               "hits":{f"top{n}":0 for n in (3,5,10)},
               "returns_yen":{f"top{n}":0 for n in (3,5,10)}} for g in ("signal_70_plus","below_70")}
    for path in paths:
        group=None
        try:
            saved=json.loads(path.read_text(encoding="utf-8"))
            value=signal(saved["national_win_rates"])
            if not isinstance(value,(int,float)) or not 0<=value<=1:raise ValueError("invalid signal")
            group="signal_70_plus" if value>=0.70 else "below_70"
            g=groups[group]
            outcome=scorer(path.stem,root)
            if outcome["status"]=="result_unavailable":
                g["awaiting_result"]+=1;continue
            if outcome["status"]!="evaluated" or outcome.get("audited") is not True or outcome.get("formal") is not False:
                raise ValueError("untrusted scoring")
            rank=outcome.get("rank")
            if rank is not None and (type(rank) is not int or not 1 <= rank <= 10):
                raise ValueError("invalid winning rank")
            for n in (3,5,10):
                key=f"top{n}"
                if type(outcome.get(key)) is not bool or outcome[key] is not (rank is not None and rank<=n):
                    raise ValueError("inconsistent top-n scorer outcome")
            g["evaluated"]+=1
            for n in (3,5,10):
                g["hits"][f"top{n}"]+=int(outcome[f"top{n}"] is True)
            proof=verified_payout(path.stem,root)
            if proof and proof[0]==outcome.get("winning_ticket"):
                g["payout_verified"]+=1
                rank=outcome.get("rank")
                for n in (3,5,10):
                    unit=(5000//n//100)*100
                    extra=(5000-unit*n)//100
                    if type(rank) is int and 1<=rank<=n:
                        g["returns_yen"][f"top{n}"]+=(unit+(100 if rank<=extra else 0))*proof[1]//100
        except (ValueError,KeyError,TypeError,OSError):
            if group is None:group="below_70"
            groups[group]["rejected"]+=1
    for g in groups.values():
        g["payout_coverage_pct"]=round(100*g["payout_verified"]/g["evaluated"],2) if g["evaluated"] else None
        g["roi_denominator"]="payout_verified_only_not_all_evaluated_races"
        g["hit_rate_pct"]={k:round(100*v/g["evaluated"],2) if g["evaluated"] else None for k,v in g["hits"].items()}
        g["roi_pct"]={k:round(100*v/(g["payout_verified"]*5000),2) if g["payout_verified"] else None for k,v in g["returns_yen"].items()}
    return {"schema":"CLEAN_TOPN_SIGNAL70_RESEARCH_V1","day_jst":day,"formal":False,
            "signal_definition":"UNCALIBRATED sum of two highest 1st-place lane model masses",
            "signal_is_empirical_confidence":False,"budget_yen_per_race":5000,
            "archived":len(paths),"groups":groups}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("day");args=p.parse_args()
    print(json.dumps(compare(args.day),ensure_ascii=False,sort_keys=True))
