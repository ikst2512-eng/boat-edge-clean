"""Research-only two-ticket bundle of same new first-second pair; outcomes used only after proposal."""
import json
from collections import Counter
from pathlib import Path
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from hole_upper_rank_pair_protection import propose

TOPS=(3,5,10)
def bundle(hole,donor,rank=3,width=2):
    base=list(hole[:10])
    if len(base)<rank or width not in (1,2):return base
    pairs=[tuple(t.split("-")[:2]) for t in base]
    heads={p[0] for p in pairs}; counts=Counter(pairs)
    candidates={}
    for t in donor:
        pair=tuple(t.split("-")[:2])
        if t not in base and pair[0] in heads and pair not in counts:
            candidates.setdefault(pair,[])
            if t not in candidates[pair]:candidates[pair].append(t)
    selected=next((items[:width] for items in candidates.values() if len(items)>=width),None)
    if not selected:return base
    removable=[]
    for i in range(len(base)-1,rank-2,-1):
        pair=pairs[i]
        if counts[pair]>1:
            removable.append(i);counts[pair]-=1
            if len(removable)==width:break
    if len(removable)<width:return base
    output=base[:]
    for i in sorted(removable,reverse=True):output.pop(i)
    for j,t in enumerate(selected):output.insert(rank-1+j,t)
    if len(output)!=len(base) or len(set(output))!=len(output):raise ValueError("budget")
    if not set(pairs).issubset({tuple(t.split("-")[:2]) for t in output}):
        raise ValueError("old_pair_lost")
    return output

def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    c=cohort_run(root=root,limit=120)
    if c.get("status")!="historical_research_only":return {"status":"no_cohort","formal":False}
    blocks=date_blocks(c["cohort_codes"])
    if blocks["status"]!="date_blocked":return {"status":"no_dates","formal":False}
    output={}
    for label,codes in (("earlier",blocks["earlier"]),("later",blocks["later"])):
        stats={name:{"changed":0,"topn":{f"top{k}":{"before":0,"after":0,"gained":0,"lost":0} for k in TOPS}}
               for name in ("single_rank3","bundle2_rank3")}
        for code in codes:
            status,a=archived_four_modes(code,root);r=compare_race(code,root)
            if status!=200 or r.get("status")!="historical_comparison_only":raise ValueError(code)
            m=a["modes"]; base=[t["combo"] for t in m["hole"]["tickets"]][:10]
            donor=list(dict.fromkeys([t["combo"] for t in m["hit"]["tickets"]+m["balance"]["tickets"]]))
            variants={"single_rank3":propose(base,donor,3),"bundle2_rank3":bundle(base,donor,3,2)}
            for key,tickets in variants.items():
                s=stats[key];s["changed"]+=int(tickets!=base)
                for k in TOPS:
                    b=r["winning_ticket"] in base[:k];n=r["winning_ticket"] in tickets[:k]
                    q=s["topn"][f"top{k}"];q["before"]+=int(b);q["after"]+=int(n)
                    q["gained"]+=int(n and not b);q["lost"]+=int(b and not n)
        for s in stats.values():
            for v in s["topn"].values():
                v["net"]=v["gained"]-v["lost"]
                if v["after"]-v["before"]!=v["net"]:raise ValueError("audit")
        output[label]={"n":len(codes),"strategies":stats}
    return {"status":"historical_exploratory","formal":False,"independent_holdout":False,
            "prospective_validation":False,"production_forecast_changed":False,
            "earlier":output["earlier"],"later":output["later"],
            "warning":"Already researched race cohort; not independent validation."}
if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
