"""Research only: compare donor orderings without using results for ticket selection."""
import json
from pathlib import Path
from collections import Counter
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from hole_upper_rank_pair_protection import propose

TOPS=(3,5,10)
STRATEGIES=("hit_first","balance_first","pair_agreement")
def donor_order(hit,balance,strategy):
    if strategy=="hit_first": return list(dict.fromkeys(hit+balance))
    if strategy=="balance_first": return list(dict.fromkeys(balance+hit))
    if strategy!="pair_agreement": raise ValueError("unknown_strategy")
    # Agreement uses only pre-existing frozen tickets, never finishing order.
    def pair(t): return tuple(t.split("-")[:2])
    h={pair(t) for t in hit}; b={pair(t) for t in balance}
    indexed=list(dict.fromkeys(hit+balance))
    return sorted(indexed,key=lambda t:(-int(pair(t) in h and pair(t) in b),
                                        -int(t in hit and t in balance),
                                        min(hit.index(t) if t in hit else 999,
                                            balance.index(t) if t in balance else 999),
                                        indexed.index(t)))
def evaluate(codes,root):
    metrics={s:{f"top{k}":{"before":0,"after":0,"gained":0,"lost":0} for k in TOPS}
             for s in STRATEGIES}
    changed=Counter()
    for code in codes:
        status,archive=archived_four_modes(code,root)
        actual=compare_race(code,root)
        if status!=200 or actual.get("status")!="historical_comparison_only":
            raise ValueError("invalid_archived_comparison_"+code)
        m={name:[x["combo"] for x in archive["modes"][name]["tickets"]]
           for name in ("hole","hit","balance")}
        base=m["hole"][:10]; winner=actual["winning_ticket"]
        for s in STRATEGIES:
            alt=propose(base,donor_order(m["hit"],m["balance"],s),3)
            if len(alt)!=len(base) or len(alt)!=len(set(alt)):
                raise ValueError("ticket_budget")
            changed[s]+=int(alt!=base)
            for k in TOPS:
                x=metrics[s][f"top{k}"]; a=winner in base[:k];b=winner in alt[:k]
                x["before"]+=int(a);x["after"]+=int(b)
                x["gained"]+=int(b and not a);x["lost"]+=int(a and not b)
    for s in STRATEGIES:
        for k in TOPS:
            x=metrics[s][f"top{k}"]
            x["net"]=x["gained"]-x["lost"]
            assert x["after"]-x["before"]==x["net"]
    return {"count":len(codes),"changed":dict(changed),"topn":metrics}
def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    c=cohort_run(root=root,limit=120)
    if c.get("status")!="historical_research_only":
        return {"status":"no_cohort","formal":False}
    blocks=date_blocks(c["cohort_codes"])
    if blocks["status"]!="date_blocked":
        return {"status":"no_date_split","formal":False}
    return {"status":"exploratory_historical_only","formal":False,
            "independent_holdout":False,"prospective_validation":False,
            "production_forecast_changed":False,
            "earlier":evaluate(blocks["earlier"],root),
            "later":evaluate(blocks["later"],root),
            "warning":"All candidates fixed before reading results but 120-race cohort previously studied. Not independent proof."}
if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
