"""Read-only reconciliation of future archived races against captured hole evidence.

A confirmed race missing a shadow does not become a replay hit. The report
identifies attrition and late-result cases without reconstructing a frozen pick.
Coverage is of files present in the checked-out repository, never all races.
"""
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race

FIRST_DAY=date(2026,11,4)
CODE=re.compile(r"20[0-9]{10}\Z")


def reconcile(root, start, end_exclusive, observed_codes, scored_codes):
    root=Path(root)
    start=max(date.fromisoformat(start),FIRST_DAY)
    end=date.fromisoformat(end_exclusive)
    if end<=start:
        return {"status":"no_eligible_complete_days","archived":0,
                "confirmed":0,"formal":False}
    observed=set(observed_codes)
    scored=set(scored_codes)
    if not scored.issubset(observed):
        raise ValueError("scored_without_capture")
    excluded=Counter();seen=set();confirmed_codes=[]
    pending_codes=[];not_scored_codes=[]
    directory=root/"four_mode_forecasts"
    for path in sorted(directory.glob("20??????????.json")) if directory.is_dir() else []:
        name=path.stem
        if not CODE.fullmatch(name):
            excluded["invalid_filename"]+=1;continue
        try:day=date.fromisoformat(name[:4]+"-"+name[4:6]+"-"+name[6:8])
        except ValueError:
            excluded["invalid_race_day"]+=1;continue
        if not start<=day<end:continue
        if path.is_symlink():
            excluded["symlink"]+=1;continue
        seen.add(name)
        code,archive=archived_four_modes(name,root)
        if code!=200:
            excluded["invalid_archive"]+=1;continue
        outcome=compare_race(name,root)
        if outcome.get("status")!="historical_comparison_only":
            pending_codes.append(name);continue
        confirmed_codes.append(name)
        if name not in scored:not_scored_codes.append(name)
    not_observed=sorted(code for code in confirmed_codes if code not in observed)
    unscored_observed=sorted(code for code in confirmed_codes if code in observed and code not in scored)
    late_result_pending=sorted(code for code in pending_codes if code in observed)
    return {"schema":"HOLE_FUTURE_RESULT_COVERAGE_V1",
            "status":"file_inventory_reconciliation",
            "window_start_jst":start.isoformat(),"window_end_exclusive_jst":end.isoformat(),
            "archived":len(seen),
            "valid_archived":len(confirmed_codes)+len(pending_codes),
            "confirmed":len(confirmed_codes),
            "confirmed_scored":len(set(confirmed_codes)&scored),
            "confirmed_without_shadow":len(not_observed),
            "confirmed_shadow_but_unscored":len(unscored_observed),
            "unconfirmed":len(pending_codes),
            "unconfirmed_with_shadow":len(late_result_pending),
            "invalid_by_reason":dict(excluded),
            "confirmed_missing_shadow_codes":not_observed,
            "confirmed_unscored_shadow_codes":unscored_observed,
            "pending_with_shadow_codes":late_result_pending,
            "all_archived_scored":bool(confirmed_codes) and len(not_scored_codes)==0 and not excluded and not pending_codes,
            "capture_window_complete_proven":False,
            "formal":False,"independent_first_receipt_verified":False,
            "production_forecast_changed":False,
            "warning":"Local repo file inventory only; missing/late results, absent artifacts and code coverage must be audited separately. No formal accuracy without independently verified predeadline first receipt."}


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=".")
    p.add_argument("--start",required=True)
    p.add_argument("--end-exclusive",required=True)
    a=p.parse_args()
    print(json.dumps(reconcile(a.root,a.start,a.end_exclusive,[],[]),
                     ensure_ascii=False,sort_keys=True))
