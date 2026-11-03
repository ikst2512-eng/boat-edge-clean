"""Research-only 1st-2nd pair availability and feature provenance audit.

This is retrospective coverage analysis on already inspected race outcomes.
It does not attribute failures to weather, exhibition, or course statistics
without those values being present in the frozen prediction artifact.
"""
import json
from collections import Counter
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run


def pair(ticket):
    return tuple(ticket.split("-")[:2])


def provenance(code, root):
    """Report evidence actually embedded in the frozen four-mode artifact."""
    path=Path(root)/"four_mode_forecasts"/(code+".json")
    if path.is_symlink() or not path.is_file() or path.stat().st_size>30000:
        raise ValueError("untrusted_archive_source")
    source=json.loads(path.read_text(encoding="utf-8"))
    before=source.get("beforeinfo")
    rates=source.get("input_national_win_rates")
    if before not in ("optional_not_in_snapshot", None):
        before_state="present_unverified"
    else:
        before_state="not_in_snapshot"
    return {
        "beforeinfo":before_state,
        "six_national_rates_present":(
            isinstance(rates,list) and len(rates)==6),
        "raw_exhibition_present":any(
            key in source for key in (
                "exhibition","exhibition_times","display_times",
                "tenji","tenji_data")),
        "raw_course_statistics_present":any(
            key in source for key in (
                "course_statistics","course_winning_rates",
                "course_stats","waku_stats")),
        "raw_entry_present":any(
            key in source for key in ("entry","actual_entry","course_entry",
                                      "beforeinfo_entry")),
        "source_hashes_present":isinstance(source.get("source_sha256"),dict),
    }


def inspect(codes, root):
    categories=Counter();feature_availability=Counter()
    donor_rank_bins=Counter();examples=[];included=[]
    by_day={}
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            categories["invalid_archive"]+=1
            continue
        outcome=compare_race(code,root)
        if outcome.get("status")!="historical_comparison_only":
            categories["unconfirmed_result"]+=1
            continue
        win=outcome["winning_ticket"]
        baseline=[x["combo"] for x in archive["modes"]["hole"]["tickets"][:10]]
        if len(baseline)!=10:
            categories["invalid_top10_size"]+=1
            continue
        source=provenance(code,root)
        included.append(code)
        day=by_day.setdefault(code[:8],Counter())
        categories["comparable"]+=1;day["comparable"]+=1
        for name,value in source.items():
            feature_availability[name+"="+str(value)]+=1
        first=win.split("-")[0]
        target=pair(win)
        if win in baseline:
            categories["top10_hit"]+=1;day["top10_hit"]+=1
            continue
        if first not in {t.split("-")[0] for t in baseline}:
            categories["head_missing"]+=1;day["head_missing"]+=1
            continue
        if target in {pair(t) for t in baseline}:
            categories["third_missing"]+=1;day["third_missing"]+=1
            continue
        categories["pair_missing"]+=1;day["pair_missing"]+=1
        modes={}
        for mode in ("hole","hit","balance"):
            tickets=[t["combo"] for t in archive["modes"][mode]["tickets"]]
            matches=[i+1 for i,t in enumerate(tickets) if pair(t)==target]
            modes[mode]={"first_rank":min(matches) if matches else None,
                         "ticket_count_for_pair":len(matches),
                         "exact_ticket_present":win in tickets}
        hole_tail=modes["hole"]["first_rank"]
        in_hole_tail=hole_tail is not None and hole_tail>10
        in_hit=modes["hit"]["first_rank"] is not None
        in_balance=modes["balance"]["first_rank"] is not None
        if in_hole_tail:
            label="hole_tail_pair"
        elif in_hit and in_balance:
            label="both_donor_modes_only"
        elif in_hit:
            label="hit_donor_only"
        elif in_balance:
            label="balance_donor_only"
        else:
            label="absent_all_frozen_modes"
        categories[label]+=1;day[label]+=1
        if in_hit or in_balance:
            ranks=[modes[m]["first_rank"] for m in ("hit","balance")
                   if modes[m]["first_rank"] is not None]
            first_rank=min(ranks)
            if first_rank<=5:bucket="donor_rank_1_5"
            elif first_rank<=10:bucket="donor_rank_6_10"
            else:bucket="donor_rank_11_plus"
            donor_rank_bins[bucket]+=1
        if len(examples)<30:
            examples.append({"race_code":code,"winning_pair":"-".join(target),
                             "source_bucket":label,"donors":modes,
                             "source_features":source})
    if categories["comparable"] != sum(categories[k] for k in (
            "top10_hit","head_missing","third_missing","pair_missing")):
        raise ValueError("miss_category_reconciliation")
    if categories["pair_missing"] != sum(categories[k] for k in (
            "hole_tail_pair","both_donor_modes_only","hit_donor_only",
            "balance_donor_only","absent_all_frozen_modes")):
        raise ValueError("pair_source_reconciliation")
    return {
        "comparable":categories["comparable"],
        "excluded":{"invalid_archive":categories["invalid_archive"],
                    "unconfirmed_result":categories["unconfirmed_result"],
                    "invalid_top10_size":categories["invalid_top10_size"]},
        "miss_classes":{key:categories[key] for key in (
            "top10_hit","head_missing","third_missing","pair_missing")},
        "missing_pair_location":{key:categories[key] for key in (
            "hole_tail_pair","both_donor_modes_only","hit_donor_only",
            "balance_donor_only","absent_all_frozen_modes")},
        "donor_first_pair_rank":dict(donor_rank_bins),
        "source_feature_coverage":dict(sorted(feature_availability.items())),
        "by_day":{k:dict(v) for k,v in sorted(by_day.items())},
        "examples":examples,
        "race_codes":included,
    }


def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    historical=cohort_run(root=root,limit=120)
    if historical.get("status")!="historical_research_only":
        return {"status":"historical_cohort_unavailable","formal":False}
    older=sorted(code for code in historical["cohort_codes"]
                 if code[:8]<"20261103")
    nov03=sorted(p.stem for p in (root/"four_mode_forecasts").glob(
        "20261103????.json") if not p.is_symlink())
    return {
        "schema":"HOLE_SECOND_PAIR_SOURCE_COVERAGE_V1",
        "status":"retrospective_reused_cohorts_only",
        "formal":False,"independent_holdout":False,
        "prospective_validation":False,
        "independent_first_receipt_verified":False,
        "production_forecast_changed":False,
        "locked_selector_changed":False,
        "groups":{"historical_reused":inspect(older,root),
                  "nov03_already_inspected":inspect(nov03,root)},
        "warning":"Source presence is not causation. A forecast artifact with "
                  "no exhibition or actual-entry data cannot establish that "
                  "missing these inputs caused a 1st-2nd pair forecast miss. "
                  "Outcome analysis is retrospective, not independent validation."
    }


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
