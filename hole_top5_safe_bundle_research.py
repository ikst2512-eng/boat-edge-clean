"""Research-only pair/third bundle protecting the first five frozen hole tickets.

This is a conservative Top10 exploration, not a Top5 improvement strategy.
Results are loaded only after candidates are determined. No formal first-receipt proof.
"""
import json
import hashlib
from collections import Counter
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from four_mode_historical_cohort import run as cohort_run
from hole_chronological_exploratory import date_blocks
from hole_pair_third_bundle_research import bundle

TOPS=(3,5,10)
POLICIES=("baseline","bundle_rank3","bundle_protect_top5")


def proposals(archive):
    modes=archive["modes"]
    base=[item["combo"] for item in modes["hole"]["tickets"][:10]]
    donor=list(dict.fromkeys(
        item["combo"] for item in
        modes["hit"]["tickets"]+modes["balance"]["tickets"]))
    rank3=bundle(base,donor,3,2)
    safe=bundle(base,donor,6,2)
    if safe[:5]!=base[:5]:
        raise ValueError("top5_prefix_changed")
    original_pairs={tuple(x.split("-")[:2]) for x in base}
    for name,candidate in (("bundle_rank3",rank3),("bundle_protect_top5",safe)):
        if len(candidate)!=len(base) or len(set(candidate))!=len(candidate):
            raise ValueError("invalid_budget_"+name)
        if not original_pairs.issubset({tuple(x.split("-")[:2]) for x in candidate}):
            raise ValueError("pair_coverage_removed_"+name)
    return {"baseline":base,"bundle_rank3":rank3,"bundle_protect_top5":safe}


def compare(codes,root):
    totals={name:{f"top{k}":{"hits":0,"gained":0,"lost":0} for k in TOPS}
            for name in POLICIES}
    changed=Counter();unavailable=[];rows=[]
    for code in codes:
        status,archive=archived_four_modes(code,root)
        if status!=200:
            unavailable.append({"race_code":code,"reason":"archive_unavailable"})
            continue
        # No finishing-order information is given to proposal selection.
        picks=proposals(archive)
        outcome=compare_race(code,root)
        if outcome.get("status")!="historical_comparison_only":
            unavailable.append({"race_code":code,"reason":"confirmed_result_unavailable"})
            continue
        win=outcome["winning_ticket"]
        flags={name:{f"top{k}":win in tickets[:k] for k in TOPS}
               for name,tickets in picks.items()}
        for name in POLICIES:
            changed[name]+=int(picks[name]!=picks["baseline"])
            for k in TOPS:
                key=f"top{k}";bucket=totals[name][key]
                baseline=flags["baseline"][key];candidate=flags[name][key]
                bucket["hits"]+=int(candidate)
                bucket["gained"]+=int(candidate and not baseline)
                bucket["lost"]+=int(baseline and not candidate)
        if flags["bundle_protect_top5"]["top5"]!=flags["baseline"]["top5"]:
            raise ValueError("top5_performance_not_preserved")
        rows.append({"race_code":code,"flags":flags})
    for name in POLICIES:
        for k in TOPS:
            key=f"top{k}";bucket=totals[name][key]
            bucket["net"]=bucket["gained"]-bucket["lost"]
            if bucket["hits"]-totals["baseline"][key]["hits"]!=bucket["net"]:
                raise ValueError("attribution_mismatch")
    return {"compared":len(rows),"missing":unavailable,
            "changed":dict(changed),"topn":totals,"rows":rows}


def run(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    cohort=cohort_run(root=root,limit=120)
    if cohort.get("status")!="historical_research_only":
        return {"status":"historical_cohort_unavailable","formal":False}
    blocks=date_blocks(cohort["cohort_codes"])
    if blocks["status"]!="date_blocked":
        return {"status":"historical_dates_unavailable","formal":False}
    archives=root/"four_mode_forecasts"
    newer=sorted(path.stem for path in archives.glob("20261103????.json") if not path.is_symlink())
    date_counts=dict(sorted(Counter(code[:8] for code in cohort["cohort_codes"]).items()))
    cohort_fingerprint=hashlib.sha256("\\n".join(sorted(cohort["cohort_codes"])).encode("utf-8")).hexdigest()
    results={"earlier_reused":compare(blocks["earlier"],root),
             "later_reused":compare(blocks["later"],root),
             "new_date_20261103":compare(newer,root)}
    return {"schema":"HOLE_TOP5_SAFE_BUNDLE_V1",
            "status":"research_only","formal":False,
            "independent_holdout":False,"prospective_validation":False,
            "independent_first_receipt_verified":False,
            "production_forecast_changed":False,
            "top5_prefix_unchanged_by_design":True,
            "historical_cohort_fingerprint":cohort_fingerprint,
            "historical_date_counts":date_counts,
            "historical_sample_not_guaranteed_stable":True,
            "groups":results,
            "warning":"Old 120 races repeatedly used and dynamic cohort selection may drift as new data arrive; do not equate block sizes with earlier runs. 20261103 is newer but has no independently verified first receipt and is a small evolving result cohort. No production promotion."}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
