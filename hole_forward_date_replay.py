"""Forward-date hole-mode replay, separately from the repeatedly studied 120 races.

Result is read only after each frozen candidate has been proposed.
File timestamps are not independent first-receipt proof.
"""
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race, classify_ticket_miss
from hole_pair_third_bundle_research import bundle
from hole_upper_rank_pair_protection import propose

CUTOFF="20261103"
TOPS=(3,5,10)
MODES=("baseline","single","bundle2")


def ticket_variants(archive):
    rows=archive["modes"]
    base=[x["combo"] for x in rows["hole"]["tickets"][:10]]
    hit=[x["combo"] for x in rows["hit"]["tickets"]]
    balance=[x["combo"] for x in rows["balance"]["tickets"]]
    donors=list(dict.fromkeys(hit+balance))
    output={"baseline":base,"single":propose(base,hit,3),
            "bundle2":bundle(base,donors,3,2)}
    for name,tickets in output.items():
        if len(tickets)!=len(base) or len(tickets)!=len(set(tickets)):
            raise ValueError("invalid_ticket_budget_"+name)
    return output


def analyze(root,date=CUTOFF):
    root=Path(root)
    if date<CUTOFF or len(date)!=8 or not date.isdigit():
        raise ValueError("earlier_date_cannot_be_new_period")
    archives=root/"four_mode_forecasts"
    if not archives.is_dir():return {"status":"no_archives","formal":False}
    files=sorted(archives.glob(date+"????.json"))
    counts={key:{f"top{k}":0 for k in TOPS} for key in MODES}
    diffs={key:{f"top{k}":{"gained":0,"lost":0} for k in TOPS}
           for key in ("single","bundle2")}
    changes=Counter()
    diag=Counter()
    excluded=Counter()
    rows=[]
    for path in files:
        if path.is_symlink():
            excluded["symlink"]+=1;continue
        code=path.stem
        state,archive=archived_four_modes(code,root)
        if state!=200:
            excluded["invalid_archive"]+=1;continue
        generated=datetime.fromisoformat(archive["generated_at_jst"])
        deadline=datetime.fromisoformat(archive["deadline_jst"])
        if generated.utcoffset()!=timedelta(hours=9) or deadline.utcoffset()!=timedelta(hours=9) or generated>=deadline:
            excluded["invalid_local_chronology"]+=1;continue
        # Candidates are determined only from the frozen forecast source.
        variants=ticket_variants(archive)
        outcome=compare_race(code,root)
        if outcome.get("status")!="historical_comparison_only":
            excluded["unconfirmed_or_invalid_result"]+=1;continue
        winner=outcome["winning_ticket"]
        flags={name:{f"top{k}":winner in tickets[:k] for k in TOPS}
               for name,tickets in variants.items()}
        for name in MODES:
            changes[name]+=int(variants[name]!=variants["baseline"])
            for k in TOPS:
                counts[name][f"top{k}"]+=int(flags[name][f"top{k}"])
        for name in ("single","bundle2"):
            for k in TOPS:
                key=f"top{k}"
                diffs[name][key]["gained"]+=int(flags[name][key] and not flags["baseline"][key])
                diffs[name][key]["lost"]+=int(flags["baseline"][key] and not flags[name][key])
        diag[classify_ticket_miss(variants["baseline"],winner)]+=1
        rows.append({"race_code":code,"winning_ticket":winner,"flags":flags,
                     "locally_generated_at_jst":archive["generated_at_jst"],
                     "deadline_jst":archive["deadline_jst"]})
    for name in diffs:
        for k in TOPS:
            key=f"top{k}";val=diffs[name][key]
            val["net"]=val["gained"]-val["lost"]
            if val["net"]!=counts[name][key]-counts["baseline"][key]:
                raise ValueError("attribution_mismatch")
    return {"schema":"HOLE_FORWARD_DATE_REPLAY_V1","status":"forward_date_research_only",
            "date_jst":date,"previous_research_end_date":"20261102",
            "scanned_archives":len(files),"comparable":len(rows),
            "excluded":dict(sorted(excluded.items())),
            "changed":dict(changes),"hits":counts,"delta":diffs,
            "baseline_miss_classes":dict(sorted(diag.items())),
            "formal":False,"independent_first_receipt_verified":False,
            "prospective_validation":False,"production_forecast_changed":False,
            "rows":rows,
            "warning":"Date is newer than previous 120-race study; local timestamps and Github first-add not independently verified. Small evolving settled cohort, no formal predictive rate."}


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",default=".")
    parser.add_argument("--date",default=CUTOFF)
    a=parser.parse_args()
    print(json.dumps(analyze(a.root,a.date),ensure_ascii=False,sort_keys=True))
