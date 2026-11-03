"""Explore donor-consensus ranking for third boats; outcome-blind, research only.

The frozen Nov 4+ choice selector is NOT modified. Retrospective groups are
repeatedly inspected and are not independent validation.
"""
import json
from collections import Counter
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from hole_pair_diversification_research import first_second
from hole_third_choice_research import variants, national_rates

TOPS=(3,5,10)
POLICIES=("baseline","donor_order","max_ticket_score","third_national_rate",
          "donor_consensus","hit_rank_first")


def rank_candidates(archive, chosen, method):
    """Replace only the two newly diversified third choices, never Top5.

    Data: ticket ranks and p values in the same frozen hit/balance forecast.
    No settled result, odds or future data are used to choose a candidate.
    """
    if method not in ("donor_consensus","hit_rank_first"):
        raise ValueError("unknown_research_method")
    base=chosen["baseline"]
    selected=chosen["donor_order"]
    added=[t for t in selected if t not in base]
    if selected==base:
        return base[:]
    if len(base)!=10 or len(selected)!=10 or len(added)!=2 or (
            first_second(added[0])==first_second(added[1])):
        raise ValueError("unexpected_diversified_pairs")
    donors={}
    for mode in ("hit","balance"):
        for rank,row in enumerate(archive["modes"][mode]["tickets"]):
            ticket=row["combo"]
            p=row["p"]
            info=donors.setdefault(ticket,{"hit":None,"balance":None,
                                          "max_p":p})
            if info[mode] is None or rank<info[mode]:
                info[mode]=rank
            info["max_p"]=max(info["max_p"],p)
    replacements=[]
    for original in added:
        pair=first_second(original)
        eligible=[t for t in donors
                  if first_second(t)==pair and t not in base]
        if not eligible:
            eligible=[original]
        def sort_key(t):
            info=donors.get(t,{"hit":None,"balance":None,"max_p":0})
            hit=info["hit"]
            balance=info["balance"]
            if method=="donor_consensus":
                return (-(int(hit is not None)+int(balance is not None)),
                        (hit if hit is not None else 100)+
                        (balance if balance is not None else 100),
                        -info["max_p"],t)
            return (hit is None,hit if hit is not None else 100,
                    balance if balance is not None else 100,-info["max_p"],t)
        replacements.append(min(eligible,key=sort_key))
    updated=[t for t in selected if t not in added]
    updated[5:5]=replacements
    if (len(updated)!=10 or len(set(updated))!=10 or
            updated[:5]!=base[:5] or
            not {first_second(t) for t in base}.issubset(
                {first_second(t) for t in updated})):
        raise ValueError("research_invariant_failed")
    return updated


def select(archive,rates=None):
    # The original locked selector and its three experimental variants remain
    # immutable; novel methods are evaluated in a separate research namespace.
    locked=variants(archive,rates)
    return {**locked,**{name:rank_candidates(archive,locked,name)
                       for name in POLICIES[4:]}}


def inspect(codes,root):
    hits={name:{f"top{k}":{"hits":0,"gained":0,"lost":0,"net":0}
                for k in TOPS} for name in POLICIES}
    changes=Counter();unavailable=Counter();rows=[]
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            unavailable["invalid_archive"]+=1;continue
        # Predict all tickets BEFORE inspecting the result.
        picked=select(archive,national_rates(code,root))
        base=picked["baseline"]
        if set(picked)!=set(POLICIES) or any(
                len(picked[name])!=10 or len(set(picked[name]))!=10 or
                picked[name][:5]!=base[:5] for name in POLICIES):
            raise ValueError("invalid_candidate_selection")
        outcome=compare_race(code,root)
        if outcome.get("status")!="historical_comparison_only":
            unavailable["unconfirmed_result"]+=1;continue
        winner=outcome["winning_ticket"]
        flags={}
        for name in POLICIES:
            tickets=picked[name]
            changes[name]+=int(tickets!=base)
            flags[name]={f"top{k}":winner in tickets[:k] for k in TOPS}
            for k in TOPS:
                key=f"top{k}"
                current=flags[name][key]
                original=winner in base[:k]
                d=hits[name][key]
                d["hits"]+=int(current)
                d["gained"]+=int(current and not original)
                d["lost"]+=int(original and not current)
        rows.append({"race_code":code,"flags":flags})
    for name in POLICIES:
        for k in TOPS:
            d=hits[name][f"top{k}"]
            d["net"]=d["gained"]-d["lost"]
            if d["net"]!=d["hits"]-hits["baseline"][f"top{k}"]["hits"]:
                raise ValueError("topk_attribution_invalid")
            if k in (3,5) and (d["gained"] or d["lost"]):
                raise ValueError("protected_top5_changed")
    return {"comparable":len(rows),"unavailable":dict(unavailable),
            "changed":dict(changes),"topn":hits,"rows":rows}


def run(root=None):
    root=Path(root) if root is not None else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"no_historical_cohort","formal":False}
    old=sorted(c for c in cohort["cohort_codes"] if c[:8]<"20261103")
    blocks=date_blocks(old)
    nov03=sorted(p.stem for p in (root/"four_mode_forecasts").glob(
        "20261103????.json") if not p.is_symlink())
    return {"schema":"HOLE_THIRD_DONOR_RANKING_RESEARCH_V1",
            "status":"retrospective_exploratory_only",
            "formal":False,"independent_holdout":False,
            "prospective_validation":False,
            "independent_first_receipt_verified":False,
            "production_forecast_changed":False,"locked_selector_changed":False,
            "not_a_promotion_gate":True,
            "historical_date_split_status":blocks["status"],
            "historical_date_cutoff":blocks.get("cutoff_last_earlier_date"),
            "groups":{
                "historical_earlier_reused":inspect(blocks["earlier"],root),
                "historical_later_reused":inspect(blocks["later"],root),
                "nov03_previously_inspected":inspect(nov03,root)},
            "warning":"Exploratory donor rank policies on previously studied races. "
                      "Date blocks do not constitute untouched holdout. "
                      "Historical improvements cannot establish live accuracy."}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
