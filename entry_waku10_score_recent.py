"""Catch up delayed Waku10 post-result scoring without changing forecasts.

Three independent day-scoped cohorts (today, yesterday, day before) are
re-checked; never pool the same race across days or call this a validated lift.
Only output inspection artifacts; no writes to the evidence ledger.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from entry_waku10_score import evaluate_waku10_archives

JST=timezone(timedelta(hours=9))


def score_recent(root, *, now=None, days_back=2, evaluator=None):
    now=now or datetime.now(JST)
    if not isinstance(now,datetime) or now.utcoffset() is None:
        raise ValueError("waku10_catchup_clock_requires_timezone")
    if type(days_back) is not int or not 0<=days_back<=6:
        raise ValueError("waku10_catchup_window_out_of_bounds")
    if evaluator is None:
        evaluator=evaluate_waku10_archives
    days=[(now.astimezone(JST).date()-timedelta(days=n)).strftime("%Y%m%d")
          for n in range(days_back+1)]
    results=[]
    failures=[]
    for day in days:
        try:
            result=evaluator(root,day)
            if result.get("day")!=day:
                raise ValueError("waku10_catchup_wrong_day")
            results.append(result)
        except Exception as exc:
            # Mark every unresolved day; an API error is NEVER counted as a
            # score of zero or a miss. Continue checking other days.
            failures.append({"day":day,"error_type":type(exc).__name__})
    return {"schema":"waku10-forward-catchup-audit-v1",
            "checked_days":days,"day_reports":results,
            "failed_days":failures,"completed_days":len(results),
            "days_with_paired_races":sum(r.get("paired_races",0)>0 for r in results),
            "sum_of_disjoint_day_matched_races":sum(r.get("paired_races",0) for r in results),
            "research_only":True,"formal":False,
            "empirical_accuracy_improvement_proven":False,
            "archive_first_seen_independently_verified":False}


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--ledger-root",default="entry-course-ledger")
    p.add_argument("--output",default="entry-course-evidence/waku10-catchup.json")
    p.add_argument("--days-back",type=int,default=2)
    args=p.parse_args()
    report=score_recent(args.ledger_root,days_back=args.days_back)
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("WAKU10_CATCHUP="+json.dumps({
        "checked_days":report["checked_days"],
        "completed_days":report["completed_days"],
        "paired_races":report["sum_of_disjoint_day_matched_races"],
        "failed_days":report["failed_days"]},ensure_ascii=False))
    if report["failed_days"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
