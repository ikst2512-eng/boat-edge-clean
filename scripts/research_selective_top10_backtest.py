"""Read-only out-of-time study of selective Top10 bets; never modifies forecasts.

Evaluate simple concentration from *stored pre-race rates*, with no result leakage:
historical discovery up to 2026-10-29, holdout >= 2026-10-30.
These model probabilities are NOT calibrated confidence.
"""
import json
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_model import probabilities
ROOT=Path(__file__).resolve().parents[1]

def study(root=ROOT):
    groups={"discovery":[],"holdout":[]}
    rejected=0
    for path in sorted((root/"research_snapshots").glob("*.json")):
        try:
            p=json.loads(path.read_text())
            qpath=root/"confirmed_results"/path.name
            if not qpath.exists(): continue
            q=json.loads(qpath.read_text())
            code=path.stem
            if p.get("race_code")!=code or q.get("race_code")!=code or p.get("status")!="research" or q.get("status")!="confirmed": continue
            generated=datetime.fromisoformat(p["generated_at"])
            cutoff=datetime.fromisoformat(p["cutoff_jst"])
            deadline=datetime.fromisoformat(p["source_deadline_jst"])
            if (generated.tzinfo is None or cutoff.tzinfo is None or deadline.tzinfo is None
                    or not generated < cutoff < deadline): 
                rejected+=1
                continue
            finish=q["finish_order"]
            if (not isinstance(finish,list) or len(finish)<3
                    or any(type(n) is not int or n not in range(1,7) for n in finish[:3])
                    or len(set(finish[:3]))!=3):
                rejected+=1
                continue
            rates=p["national_win_rates"]
            ranked=probabilities(rates)
            expected=["-".join(map(str,t)) for t,_ in ranked[:10]]
            if p["predictions"]!=expected: continue
            top10_mass=sum(v for _,v in ranked[:10])
            winning="-".join(map(str,q["finish_order"][:3]))
            groups["discovery" if code[:8]<="20261029" else "holdout"].append((top10_mass, int(winning in expected), code))
        except (ValueError, KeyError, TypeError, OSError, ZeroDivisionError, AttributeError):
            rejected+=1
    output={"rejected":rejected,"discovery_n":len(groups["discovery"]),"holdout_n":len(groups["holdout"])}
    # Fixed thresholds chosen for inspection; never optimize a cutoff on holdout.
    for label, entries in groups.items():
        output[label]={"all":{"n":len(entries),"hits":sum(v for _,v,_ in entries)}}
        for threshold in (0.35, 0.4, 0.45, 0.5, 0.55, 0.6):
            chosen=[v for mass,v,_ in entries if mass>=threshold]
            output[label][str(threshold)]={"n":len(chosen),"hits":sum(chosen),"hit_rate_pct":round(100*sum(chosen)/len(chosen),2) if chosen else None}
    return output

if __name__=="__main__":
    print(json.dumps(study(),ensure_ascii=False,indent=2))
