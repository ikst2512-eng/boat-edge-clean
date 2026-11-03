"""Compare two new 1st/2nd pairs vs two 3rd choices for one new pair.

Historical exploration only. Freeze candidates without confirmed results,
protect hole Top5 and original pairs, use exactly 10 tickets.
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

POLICIES=("baseline","two_pairs_one_third","one_pair_two_thirds")
TOPS=(3,5,10)


def one_pair_two_thirds(archive,rates):
    base=[x["combo"] for x in archive["modes"]["hole"]["tickets"][:10]]
    if len(base)!=10 or len(set(base))!=10:
        raise ValueError("invalid_hole_top10")
    previous={first_second(t) for t in base}
    heads={x[0] for x in previous}
    donors={}
    for name in ("hit","balance"):
        for rank,row in enumerate(archive["modes"][name]["tickets"]):
            t=row["combo"];p=first_second(t)
            if p in previous or p[0] not in heads:
                continue
            d=donors.setdefault(p,{"tickets":{},"best_rank":rank})
            d["best_rank"]=min(rank,d["best_rank"])
            d["tickets"][t]=max(row["p"],d["tickets"].get(t,0))
    eligible=[p for p in donors if len(donors[p]["tickets"])>=2]
    if not eligible:
        return base
    # One extra pair, two third choices, using source forecast ranks only.
    selected_pair=min(eligible,key=lambda p:(donors[p]["best_rank"],p))
    third_scores=donors[selected_pair]["tickets"]
    def sort_key(t):
        national=(rates[int(t.split("-")[2])-1] if rates is not None else None)
        if national is not None:
            return (-national,-third_scores[t],t)
        return (-third_scores[t],t)
    added=sorted(third_scores,key=sort_key)[:2]
    counts=Counter(first_second(t) for t in base)
    removed=[]
    for i in range(9,4,-1):
        p=first_second(base[i])
        if counts[p]>1:
            removed.append(i)
            counts[p]-=1
            if len(removed)==2:
                break
    if len(removed)!=2:
        return base
    candidate=base[:]
    for i in sorted(removed,reverse=True):
        candidate.pop(i)
    candidate[5:5]=added
    if (len(candidate)!=10 or len(set(candidate))!=10 or
            candidate[:5]!=base[:5] or
            not previous.issubset({first_second(t) for t in candidate})):
        raise ValueError("pair_budget_invariant")
    return candidate


def inspect(codes,root):
    topn={p:{f"top{k}":{"hits":0,"gained":0,"lost":0} for k in TOPS}
          for p in POLICIES}
    paired=Counter();skips=Counter();day={};changes=Counter();pair_changes=Counter()
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            skips["invalid_archive"]+=1;continue
        rates=national_rates(code,root)
        prior=variants(archive,rates)
        picks={"baseline":prior["baseline"],
               "two_pairs_one_third":prior["third_national_rate"],
               "one_pair_two_thirds":one_pair_two_thirds(archive,rates)}
        original_pairs={first_second(t) for t in picks["baseline"]}
        for ticket_list in picks.values():
            if (len(ticket_list)!=10 or len(set(ticket_list))!=10 or
                    ticket_list[:5]!=picks["baseline"][:5] or
                    not original_pairs.issubset({first_second(t) for t in ticket_list})):
                raise ValueError("top5_pair_or_budget_modified")
        # No results used to select tickets.
        result=compare_race(code,root)
        if result.get("status")!="historical_comparison_only":
            skips["unconfirmed_result"]+=1;continue
        winner=result["winning_ticket"]
        flags={p:{f"top{k}":winner in picks[p][:k] for k in TOPS}
               for p in POLICIES}
        for p in POLICIES:
            changes[p]+=int(picks[p]!=picks["baseline"])
            pair_changes[p]+=len({first_second(t) for t in picks[p]}-original_pairs)
            for k in TOPS:
                metric=topn[p][f"top{k}"]
                before=flags["baseline"][f"top{k}"]
                after=flags[p][f"top{k}"]
                metric["hits"]+=int(after)
                metric["gained"]+=int(after and not before)
                metric["lost"]+=int(before and not after)
        new=flags["one_pair_two_thirds"]["top10"]
        locked=flags["two_pairs_one_third"]["top10"]
        paired["one_only"]+=int(new and not locked)
        paired["two_only"]+=int(locked and not new)
        record=day.setdefault(code[:8],{"races":0,"one_only":0,"two_only":0})
        record["races"]+=1
        record["one_only"]+=int(new and not locked)
        record["two_only"]+=int(locked and not new)
    for p in POLICIES:
        for k in TOPS:
            value=topn[p][f"top{k}"]
            value["net"]=value["gained"]-value["lost"]
            if value["hits"]-topn["baseline"][f"top{k}"]["hits"]!=value["net"]:
                raise ValueError("topk_reconciliation_failed")
            if k<=5 and (value["gained"] or value["lost"]):
                raise ValueError("top5_hit_shift")
    net=paired["one_only"]-paired["two_only"]
    if net!=topn["one_pair_two_thirds"]["top10"]["hits"]-topn["two_pairs_one_third"]["top10"]["hits"]:
        raise ValueError("pairwise_reconciliation_failed")
    return {"comparable":sum(v["races"] for v in day.values()),
            "unavailable":dict(skips),"changed_from_baseline":dict(changes),
            "new_pairs_added_total":dict(pair_changes),
            "topn":topn,
            "one_pair_vs_two_pairs":{"only_one_pair":paired["one_only"],
                                    "only_two_pairs":paired["two_only"],
                                    "net":net},
            "by_date":dict(sorted(day.items()))}


def run(root=None):
    root=Path(root) if root is not None else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"no_cohort","formal":False}
    codes=sorted(c for c in cohort["cohort_codes"] if c[:8]<"20261103")
    blocks=date_blocks(codes)
    nov03=sorted(p.stem for p in (root/"four_mode_forecasts").glob(
        "20261103????.json") if not p.is_symlink())
    return {"schema":"HOLE_PAIR_THIRD_BUDGET_RESEARCH_V1",
            "status":"previously_inspected_retrospective_only",
            "formal":False,"independent_holdout":False,
            "prospective_validation":False,
            "independent_first_receipt_verified":False,
            "locked_selector_changed":False,"production_forecast_changed":False,
            "groups":{"historical_earlier_reused":inspect(blocks["earlier"],root),
                      "historical_later_reused":inspect(blocks["later"],root),
                      "nov03_previously_inspected":inspect(nov03,root)},
            "warning":"Prior outcomes have already informed multiple research designs. "
                      "This is not untouched validation or a live promotion gate."}

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
