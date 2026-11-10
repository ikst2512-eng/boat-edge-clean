"""Read-only conditional first-place diversification on archived hit Top10.
Thresholds are exploratory, not tuned for production. No holdout claim.
"""
import json
import re
from collections import defaultdict
from pathlib import Path
from four_mode_frozen_diagnostic import compare_race

ROOT=Path(__file__).resolve().parent
POLICIES=((0.5,0.15),(1.0,0.15),(0.5,0.30),(1.0,0.30))

def reorder(tickets,bonus):
    remaining=list(tickets[:10])
    if len(remaining)!=10 or len({x["combo"] for x in remaining})!=10:
        raise ValueError("invalid ten")
    selected=[]
    while remaining:
        firsts={x["combo"][0] for x in selected}
        best=max(remaining,key=lambda x:(x["p"]*(1+bonus*(x["combo"][0] not in firsts)),x["p"],x["combo"]))
        selected.append(best)
        remaining.remove(best)
    return [x["combo"] for x in selected]

def audit(root=ROOT):
    root=Path(root)
    grouped=defaultdict(lambda: defaultdict(lambda:{"n":0,"applied":0,"base3":0,"candidate3":0,"base5":0,"candidate5":0,"base10":0,"candidate10":0,"gained3":0,"lost3":0}))
    excluded=defaultdict(int)
    for path in sorted((root/"four_mode_forecasts").glob("*.json")):
        if not re.fullmatch(r"20[0-9]{10}",path.stem): continue
        record=compare_race(path.stem,root)
        if record.get("status")!="historical_comparison_only":
            excluded[record.get("status","unavailable")]+=1
            continue
        try:
            if path.is_symlink() or path.stat().st_size>30000: raise ValueError("unsafe")
            obj=json.loads(path.read_text(encoding="utf-8"))
            if obj.get("race_code")!=path.stem: raise ValueError("identity")
            rates=obj["input_national_win_rates"]
            if type(rates) is not list or len(rates)!=6 or any(type(v) not in (float,int) or not 0<=v<=10 for v in rates):
                raise ValueError("rates")
            ranked=sorted(rates,reverse=True)
            gap=ranked[0]-ranked[1]
            tickets=obj["modes"]["hit"]["tickets"]
            baseline=[x["combo"] for x in tickets[:10]]
            winner=record["winning_ticket"]
            for threshold,bonus in POLICIES:
                applied=gap<=threshold
                candidate=reorder(tickets,bonus) if applied else baseline
                if set(candidate)!=set(baseline): raise ValueError("membership")
                key=f"gap_le_{threshold}_bonus_{bonus}"
                row=grouped[(obj["model_version"],path.stem[:8])][key]
                row["n"]+=1
                row["applied"]+=int(applied)
                for n in (3,5,10):
                    row[f"base{n}"]+=int(winner in baseline[:n])
                    row[f"candidate{n}"]+=int(winner in candidate[:n])
                row["gained3"]+=int(winner in candidate[:3] and winner not in baseline[:3])
                row["lost3"]+=int(winner in baseline[:3] and winner not in candidate[:3])
        except (KeyError,ValueError,TypeError,OSError,AttributeError):
            excluded["invalid_record"]+=1
    groups={}
    for (version,day),policies in sorted(grouped.items()):
        groups.setdefault(version,{})[day]=policies
    return {"status":"exploratory_conditional_only","formal":False,"independent_holdout":False,
            "groups":groups,"excluded":dict(excluded),"warning":"Prior-inspected history; no production promotion."}

if __name__=="__main__":
    print("CONDITIONAL_DIVERSITY="+json.dumps(audit(),sort_keys=True))
