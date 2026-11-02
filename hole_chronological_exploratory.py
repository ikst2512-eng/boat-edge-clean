"""Exploratory date-blocked replay on existing researched 120 races; not an independent holdout."""
import json
from collections import Counter
from pathlib import Path
from four_mode_historical_cohort import run as cohort_run
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from hole_upper_rank_pair_protection import propose

TOPS=(3,5,10)
SOURCES=("hit","balance","hit_balance")
RANKS=(3,5)
def date_blocks(codes):
    dates=sorted(set(c[:8] for c in codes))
    if len(dates)<2:
        return {"status":"insufficient_distinct_dates","earlier":[],"later":[],
                "all_dates":dates}
    pivot=(len(dates)+1)//2
    before=set(dates[:pivot])
    earlier=[c for c in codes if c[:8] in before]
    later=[c for c in codes if c[:8] not in before]
    if not earlier or not later or max(c[:8] for c in earlier)>=min(c[:8] for c in later):
        raise ValueError("date_split_leakage")
    return {"status":"date_blocked","earlier":earlier,"later":later,
            "all_dates":dates,"cutoff_last_earlier_date":dates[pivot-1]}

def assess(codes,root):
    scenarios={f"{source}_rank{rank}":{"changed":0,
          "topn":{f"top{k}":{"baseline_hits":0,"candidate_hits":0,"gained":0,"lost":0}
                   for k in TOPS}} for source in SOURCES for rank in RANKS}
    evaluated=[]
    rejected=[]
    for code in codes:
        s,archive=archived_four_modes(code,root)
        outcome=compare_race(code,root)
        if s!=200 or outcome.get("status")!="historical_comparison_only":
            rejected.append(code);continue
        modes={m:[t["combo"] for t in archive["modes"][m]["tickets"]]
               for m in ("hole","hit","balance")}
        base=modes["hole"][:10]
        donors={"hit":modes["hit"],"balance":modes["balance"],
                "hit_balance":list(dict.fromkeys(modes["hit"]+modes["balance"]))}
        winner=outcome["winning_ticket"]
        for source in SOURCES:
            for rank in RANKS:
                name=f"{source}_rank{rank}"
                candidate=propose(base,donors[source],rank)
                if len(candidate)!=len(base) or len(set(candidate))!=len(candidate):
                    raise ValueError("invalid_budget")
                item=scenarios[name]
                item["changed"]+=int(candidate!=base)
                for k in TOPS:
                    bucket=item["topn"][f"top{k}"]
                    old=winner in base[:k];new=winner in candidate[:k]
                    bucket["baseline_hits"]+=int(old)
                    bucket["candidate_hits"]+=int(new)
                    bucket["gained"]+=int(new and not old)
                    bucket["lost"]+=int(old and not new)
        evaluated.append(code)
    for item in scenarios.values():
        for bucket in item["topn"].values():
            bucket["net"]=bucket["gained"]-bucket["lost"]
            if bucket["candidate_hits"]-bucket["baseline_hits"]!=bucket["net"]:
                raise ValueError("attribution_mismatch")
    return {"comparable":len(evaluated),"unavailable":rejected,"scenarios":scenarios}

def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"no_cohort","formal":False}
    codes=cohort["cohort_codes"]
    blocks=date_blocks(codes)
    return {"schema":"HOLE_CHRONOLOGICAL_EXPLORATORY_V1",
            "status":blocks["status"],"formal":False,"independent_holdout":False,
            "prospective_validation":False,"production_forecast_changed":False,
            "prior_research_reused":True,"original_cohort_count":len(codes),
            "dates":dict(sorted(Counter(x[:8] for x in codes).items())),
            "date_split":{k:v for k,v in blocks.items() if k not in ("earlier","later")},
            "earlier":assess(blocks["earlier"],root),
            "later":assess(blocks["later"],root),
            "warning":"Same previously analyzed races; exploratory diagnostic only. Never use as independent validation or a production promotion gate."}
if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
