"""Exploratory conservative donor guard against national-rate-only third choices.

Rule is fixed in this research module, is not promoted to the precommitted
Nov 4+ selector, and MUST NOT be evaluated as an independent holdout.
"""
import json
from collections import Counter
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from hole_pair_diversification_research import first_second
from hole_third_choice_research import national_rates
from hole_third_donor_ranking_research import select,paired_outcomes

TOPS=(3,5,10)
METHODS=("baseline","third_national_rate","donor_consensus","consensus_guard")
GUARD_MAX_DONOR_RANK=2
GUARD_MAX_RATE_ADVANTAGE=2.0


def guarded(archive,rates,picks):
    """Choose donor-consensus third only when two frozen signals agree strongly.

    Protect all Top5 slots and the same two added first-second pairs.
    If national rates are unavailable, preserve the locked selector's result.
    """
    national=picks["third_national_rate"]
    consensus=picks["donor_consensus"]
    base=picks["baseline"]
    if national==consensus or rates is None:
        return national[:]
    candidates=national[:]
    for i,ticket in enumerate(national):
        if i<5 or ticket in base:
            continue
        pair=first_second(ticket)
        other=next((t for t in consensus[5:] if first_second(t)==pair),None)
        if not other or other==ticket:
            continue
        # National win rate is not the 3rd-place probability. The guard asks
        # if both frozen donor modes strongly ranked the same full ticket.
        ranks={}
        for mode in ("hit","balance"):
            ranks[mode]=next((rank for rank,row in
                              enumerate(archive["modes"][mode]["tickets"],start=1)
                              if row["combo"]==other),None)
        third_national=rates[int(ticket.split("-")[2])-1]
        third_consensus=rates[int(other.split("-")[2])-1]
        if (all(rank is not None and rank<=GUARD_MAX_DONOR_RANK
                for rank in ranks.values()) and
                third_national-third_consensus<=GUARD_MAX_RATE_ADVANTAGE):
            candidates[i]=other
    if (len(candidates)!=10 or len(set(candidates))!=10 or
            candidates[:5]!=base[:5] or
            {first_second(t) for t in candidates}!={first_second(t) for t in national}):
        raise ValueError("guard_changed_top5_or_pair_coverage")
    return candidates


def inspect(codes,root):
    totals={m:{f"top{k}":{"hits":0,"gained":0,"lost":0,"net":0}
               for k in TOPS} for m in METHODS}
    rows=[];skips=Counter();changes=0
    for code in codes:
        state,archive=archived_four_modes(code,root)
        if state!=200:
            skips["invalid_archive"]+=1;continue
        rates=national_rates(code,root)
        frozen=select(archive,rates)
        choices={m:frozen[m] for m in METHODS if m!="consensus_guard"}
        choices["consensus_guard"]=guarded(archive,rates,frozen)
        if any(len(t)!=10 or len(set(t))!=10 or t[:5]!=choices["baseline"][:5]
               for t in choices.values()):
            raise ValueError("invalid_research_tickets")
        # Absolutely no settled result is passed into any selector.
        result=compare_race(code,root)
        if result.get("status")!="historical_comparison_only":
            skips["unconfirmed_result"]+=1;continue
        winner=result["winning_ticket"]
        flags={m:{f"top{k}":winner in choices[m][:k] for k in TOPS}
               for m in METHODS}
        changes+=int(choices["consensus_guard"]!=choices["third_national_rate"])
        for m in METHODS:
            for k in TOPS:
                key=f"top{k}";current=flags[m][key];before=flags["baseline"][key]
                total=totals[m][key]
                total["hits"]+=int(current)
                total["gained"]+=int(current and not before)
                total["lost"]+=int(before and not current)
        rows.append({"race_code":code,"flags":flags})
    for m in METHODS:
        for k in TOPS:
            d=totals[m][f"top{k}"]
            d["net"]=d["gained"]-d["lost"]
            if d["hits"]-totals["baseline"][f"top{k}"]["hits"]!=d["net"]:
                raise ValueError("bad_attribution")
            if k<10 and (d["gained"] or d["lost"]):
                raise ValueError("top5_changed")
    paired=paired_outcomes(rows,"consensus_guard","third_national_rate",10)
    if paired["net"]!=(
        totals["consensus_guard"]["top10"]["hits"]-
        totals["third_national_rate"]["top10"]["hits"]):
        raise ValueError("paired_reconciliation")
    return {"comparable":len(rows),"unavailable":dict(skips),
            "guard_changed_races":changes,"topn":totals,
            "paired_guard_vs_national":paired}


def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"no_historical_cohort","formal":False}
    old=sorted(c for c in cohort["cohort_codes"] if c[:8]<"20261103")
    blocks=date_blocks(old)
    recent=sorted(p.stem for p in (root/"four_mode_forecasts").glob(
        "20261103????.json") if not p.is_symlink())
    return {"schema":"HOLE_CONSENSUS_GUARD_EXPLORATORY_V1",
            "status":"previously_inspected_research_only",
            "guard":{"max_donor_rank":GUARD_MAX_DONOR_RANK,
                     "max_rate_advantage":GUARD_MAX_RATE_ADVANTAGE},
            "formal":False,"independent_holdout":False,
            "prospective_validation":False,
            "independent_first_receipt_verified":False,
            "production_forecast_changed":False,
            "locked_selector_changed":False,
            "groups":{"historical_earlier_reused":inspect(blocks["earlier"],root),
                      "historical_later_reused":inspect(blocks["later"],root),
                      "nov03_previously_inspected":inspect(recent,root)},
            "warning":"Exploratory rule built after inspecting historical outcomes. "
                      "Not precommitted for Nov 4 or proof of improvement."}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
