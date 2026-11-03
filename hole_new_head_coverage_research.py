"""Research-only exploration: allocate two Top10 slots to missing 1st-head coverage.

All candidate selection uses frozen hole/hit/balance tickets and national rates
before confirmed outcomes are read. Retrospective cohorts already inspected.
No changes to production, or the locked prospective Top10 strategy.
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

POLICIES=("baseline","locked_two_pairs","one_new_head","two_new_heads")
TOPS=(3,5,10)


def new_head_variants(archive,rates=None):
    base=[t["combo"] for t in archive["modes"]["hole"]["tickets"][:10]]
    if len(base)!=10 or len(set(base))!=10:
        raise ValueError("invalid_base")
    old_pairs={first_second(t) for t in base}
    old_heads={p[0] for p in old_pairs}
    eligible={}
    for mode in ("hit","balance"):
        for rank,row in enumerate(archive["modes"][mode]["tickets"]):
            ticket=row["combo"]
            pair=first_second(ticket)
            if pair in old_pairs:
                continue
            item=eligible.setdefault(pair,{"ranks":{},"score":0,"tickets":{}})
            item["ranks"].setdefault(mode,rank)
            item["score"]=max(item["score"],row["p"])
            item["tickets"][ticket]=max(item["tickets"].get(ticket,0),row["p"])
    def priority(pair):
        entry=eligible[pair]
        return (-len(entry["ranks"]),min(entry["ranks"].values()),
                -entry["score"],pair)
    old=sorted((p for p in eligible if p[0] in old_heads),key=priority)
    fresh=sorted((p for p in eligible if p[0] not in old_heads),key=priority)
    def pick_ticket(pair):
        record=eligible[pair]["tickets"]
        if rates is None:
            return min(record,key=lambda t:(-record[t],t))
        return min(record,key=lambda t:(-rates[int(t.split("-")[2])-1],
                                        -record[t],t))
    def allocate(pairs):
        if len(pairs)!=2 or len(set(pairs))!=2:
            return base[:]
        counts=Counter(first_second(t) for t in base)
        removable=[]
        for i in range(9,4,-1):
            pair=first_second(base[i])
            if counts[pair]>1:
                counts[pair]-=1
                removable.append(i)
                if len(removable)==2:break
        if len(removable)!=2:return base[:]
        new=base[:]
        for i in sorted(removable,reverse=True):
            new.pop(i)
        new[5:5]=[pick_ticket(p) for p in pairs]
        if (len(new)!=10 or len(set(new))!=10 or new[:5]!=base[:5]
                or not old_pairs.issubset({first_second(t) for t in new})):
            raise ValueError("head_candidate_invariant")
        return new
    return {
        "one_new_head":allocate([fresh[0],old[0]]) if fresh and old else base[:],
        "two_new_heads":allocate(fresh[:2]) if len(fresh)>=2 else base[:],
    }


def inspect(codes,root):
    metrics={p:{f"top{k}":{"hits":0,"gained":0,"lost":0} for k in TOPS}
             for p in POLICIES}
    missing=Counter();reason=Counter();changed=Counter();pairwise=Counter()
    day={};examples=[]
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            missing["invalid_archive"]+=1;continue
        rates=national_rates(code,root)
        original=variants(archive,rates)
        picks={"baseline":original["baseline"],
               "locked_two_pairs":original["third_national_rate"],
               **new_head_variants(archive,rates)}
        base=picks["baseline"];old_pairs={first_second(t) for t in base}
        for p in POLICIES:
            t=picks[p]
            if (len(t)!=10 or len(set(t))!=10 or t[:5]!=base[:5]
                    or not old_pairs.issubset({first_second(x) for x in t})):
                raise ValueError("top10_invariant_broken")
        # Candidate decisions are fully finalized before result access.
        outcome=compare_race(code,root)
        if outcome.get("status")!="historical_comparison_only":
            missing["unconfirmed_result"]+=1;continue
        winner=outcome["winning_ticket"]
        win_pair=first_second(winner)
        flags={p:{f"top{k}":winner in picks[p][:k] for k in TOPS}
               for p in POLICIES}
        old_heads={t.split("-")[0] for t in base}
        if win_pair[0] not in old_heads:
            reason["baseline_head_absent"]+=1
            if any(first_second(t)[0]==win_pair[0] for t in picks["one_new_head"]):
                reason["one_new_head_covered"]+=1
            if any(first_second(t)[0]==win_pair[0] for t in picks["two_new_heads"]):
                reason["two_new_heads_covered"]+=1
        elif win_pair not in old_pairs:
            reason["baseline_second_pair_absent"]+=1
        for p in POLICIES:
            changed[p]+=int(picks[p]!=base)
            for k in TOPS:
                key=f"top{k}";current=flags[p][key];before=flags["baseline"][key]
                metric=metrics[p][key]
                metric["hits"]+=int(current)
                metric["gained"]+=int(current and not before)
                metric["lost"]+=int(before and not current)
        daily=day.setdefault(code[:8],{"races":0,"one_new_head_net":0,
                                      "two_new_heads_net":0})
        daily["races"]+=1
        for p in ("one_new_head","two_new_heads"):
            a=flags[p]["top10"];b=flags["locked_two_pairs"]["top10"]
            pairwise[(p,"gained")]+=int(a and not b)
            pairwise[(p,"lost")]+=int(b and not a)
            daily[p+"_net"]+=int(a)-int(b)
            if a!=b and len(examples)<24:
                examples.append({"race_code":code,"policy":p,
                                 "winner":winner,"gained":a,
                                 "baseline_head_absent":win_pair[0] not in old_heads})
    for p in POLICIES:
        for k in TOPS:
            metric=metrics[p][f"top{k}"]
            metric["net"]=metric["gained"]-metric["lost"]
            if metric["hits"]-metrics["baseline"][f"top{k}"]["hits"]!=metric["net"]:
                raise ValueError("invalid_attribution")
            if k<=5 and (metric["gained"] or metric["lost"]):
                raise ValueError("top5_shift")
    comparisons={}
    for p in ("one_new_head","two_new_heads"):
        gained=pairwise[(p,"gained")];lost=pairwise[(p,"lost")]
        net=metrics[p]["top10"]["hits"]-metrics["locked_two_pairs"]["top10"]["hits"]
        if gained-lost!=net:
            raise ValueError("paired_counts_inconsistent")
        comparisons[p]={"gained":gained,"lost":lost,"net":net}
    return {"comparable":sum(v["races"] for v in day.values()),
            "excluded":dict(missing),"baseline_miss_reason":dict(reason),
            "changed_from_baseline":dict(changed),"topn":metrics,
            "paired_vs_locked":comparisons,"by_date":dict(sorted(day.items())),
            "disagreements":examples}


def run(root=None):
    root=Path(root) if root is not None else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"historical_cohort_unavailable","formal":False}
    older=sorted(c for c in cohort["cohort_codes"] if c[:8]<"20261103")
    blocks=date_blocks(older)
    nov03=sorted(p.stem for p in (root/"four_mode_forecasts").glob(
        "20261103????.json") if not p.is_symlink())
    return {
        "schema":"HOLE_NEW_HEAD_COVERAGE_RESEARCH_V1",
        "status":"previously_inspected_retrospective_only",
        "formal":False,"independent_holdout":False,
        "prospective_validation":False,
        "independent_first_receipt_verified":False,
        "locked_selector_changed":False,"production_forecast_changed":False,
        "groups":{"earlier_reused":inspect(blocks["earlier"],root),
                  "later_reused":inspect(blocks["later"],root),
                  "nov03_already_inspected":inspect(nov03,root)},
        "warning":"Historical research repeatedly examined, not a clean holdout. "
                  "Candidate-head coverage is not evidence of independent prospective gain."
    }


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
