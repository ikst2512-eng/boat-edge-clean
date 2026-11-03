"""Research-only top-10 pair selection from frozen hit/balance forecasts.

Does not change the precommitted Nov 4+ prospective selection algorithm.
Historical cohorts were already inspected; no untouched holdout exists here.
"""
import json
from collections import Counter
from pathlib import Path
from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from hole_pair_diversification_research import first_second
from hole_third_choice_research import variants,national_rates

POLICIES=("baseline","third_national_rate","pair_max_score","pair_donor_consensus")
TOPS=(3,5,10)


def propose(archive,rates,policy):
    if policy not in ("pair_max_score","pair_donor_consensus"):
        raise ValueError("unknown_pair_policy")
    base=[item["combo"] for item in archive["modes"]["hole"]["tickets"][:10]]
    if len(base)!=10 or len(set(base))!=10:
        raise ValueError("invalid_baseline")
    original_pairs={first_second(t) for t in base}
    heads={pair[0] for pair in original_pairs}
    candidates={}
    for mode in ("hit","balance"):
        for idx,row in enumerate(archive["modes"][mode]["tickets"]):
            t=row["combo"];pair=first_second(t)
            if pair in original_pairs or pair[0] not in heads:
                continue
            item=candidates.setdefault(pair,{"tickets":{},"sources":set(),
                                             "best_score":float("-inf"),"best_rank":100})
            item["sources"].add(mode)
            item["best_score"]=max(item["best_score"],row["p"])
            item["best_rank"]=min(item["best_rank"],idx)
            item["tickets"][t]=max(item["tickets"].get(t,float("-inf")),row["p"])
    if len(candidates)<2:return base
    if policy=="pair_max_score":
        ranking=sorted(candidates,key=lambda p:(
            -candidates[p]["best_score"],candidates[p]["best_rank"],p))
    else:
        ranking=sorted(candidates,key=lambda p:(
            -len(candidates[p]["sources"]),candidates[p]["best_rank"],
            -candidates[p]["best_score"],p))
    chosen_pairs=ranking[:2]
    picks=[]
    for pair in chosen_pairs:
        choices=candidates[pair]["tickets"]
        if rates is not None:
            t=min(choices,key=lambda x:(
                -rates[int(x.split("-")[2])-1],-choices[x],x))
        else:
            t=min(choices,key=lambda x:(-choices[x],x))
        picks.append(t)
    counts=Counter(first_second(t) for t in base)
    to_remove=[]
    for i in range(9,4,-1):
        pair=first_second(base[i])
        if counts[pair]>1:
            counts[pair]-=1;to_remove.append(i)
            if len(to_remove)==2:break
    if len(to_remove)!=2:return base
    selected=base[:]
    for i in sorted(to_remove,reverse=True):selected.pop(i)
    selected[5:5]=picks
    if (selected[:5]!=base[:5] or len(selected)!=10 or
            len(set(selected))!=10 or
            not original_pairs.issubset({first_second(t) for t in selected})):
        raise ValueError("pair_selection_invariant")
    return selected


def inspect(codes,root):
    totals={p:{f"top{k}":{"hits":0,"gained":0,"lost":0}
               for k in TOPS} for p in POLICIES}
    changed=Counter();missing=Counter();rows=[];paired=Counter();by_date={}
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:missing["invalid_archive"]+=1;continue
        rates=national_rates(code,root)
        existing=variants(archive,rates)
        picks={"baseline":existing["baseline"],
               "third_national_rate":existing["third_national_rate"]}
        picks.update({p:propose(archive,rates,p) for p in POLICIES[2:]})
        base=picks["baseline"]
        if any(len(v)!=10 or len(set(v))!=10 or v[:5]!=base[:5]
               for v in picks.values()):
            raise ValueError("invalid_top5_or_budget")
        # All selectors ran before the confirmed result was opened.
        result=compare_race(code,root)
        if result.get("status")!="historical_comparison_only":
            missing["unconfirmed_result"]+=1;continue
        winner=result["winning_ticket"]
        flags={p:{f"top{k}":winner in picks[p][:k] for k in TOPS}
               for p in POLICIES}
        for p in POLICIES:
            changed[p]+=int(picks[p]!=base)
            for k in TOPS:
                key=f"top{k}";before=flags["baseline"][key];after=flags[p][key]
                metric=totals[p][key]
                metric["hits"]+=int(after)
                metric["gained"]+=int(after and not before)
                metric["lost"]+=int(before and not after)
        date=code[:8]
        d=by_date.setdefault(date,{"races":0,"pair_max_score_net":0,
                                  "pair_donor_consensus_net":0})
        d["races"]+=1
        for p in POLICIES[2:]:
            a=flags[p]["top10"];b=flags["third_national_rate"]["top10"]
            paired[(p,"only_new")]+=int(a and not b)
            paired[(p,"only_locked")]+=int(b and not a)
            d[p+"_net"]+=int(a)-int(b)
        rows.append({"race_code":code,"flags":flags})
    for p in POLICIES:
        for k in TOPS:
            m=totals[p][f"top{k}"]
            m["net"]=m["gained"]-m["lost"]
            if m["hits"]-totals["baseline"][f"top{k}"]["hits"]!=m["net"]:
                raise ValueError("invalid_attribution")
            if k<10 and (m["gained"] or m["lost"]):
                raise ValueError("top5_changed")
    comparison={}
    for p in POLICIES[2:]:
        win=paired[(p,"only_new")];loss=paired[(p,"only_locked")]
        if win-loss!=totals[p]["top10"]["hits"]-totals["third_national_rate"]["top10"]["hits"]:
            raise ValueError("paired_mismatch")
        comparison[p]={"only_new":win,"only_locked":loss,"net":win-loss}
    return {"comparable":len(rows),"unavailable":dict(missing),
            "changed":dict(changed),"topn":totals,"paired_vs_locked":comparison,
            "by_date":dict(sorted(by_date.items()))}


def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"no_historical_cohort","formal":False}
    old=sorted(c for c in cohort["cohort_codes"] if c[:8]<"20261103")
    block=date_blocks(old)
    recent=sorted(p.stem for p in (root/"four_mode_forecasts").glob(
        "20261103????.json") if not p.is_symlink())
    return {"schema":"HOLE_PAIR_PRIORITY_RESEARCH_V1",
            "status":"retrospective_exploratory_only",
            "formal":False,"independent_holdout":False,
            "prospective_validation":False,
            "independent_first_receipt_verified":False,
            "production_forecast_changed":False,"locked_selector_changed":False,
            "groups":{"historical_earlier_reused":inspect(block["earlier"],root),
                      "historical_later_reused":inspect(block["later"],root),
                      "nov03_previously_inspected":inspect(recent,root)},
            "warning":"The prior race outcomes have repeatedly been inspected. "
                      "Pair policy comparisons are descriptive, not an untouched holdout."}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
