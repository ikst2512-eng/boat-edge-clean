"""Locked, future-only, research-only hole candidate evaluation.

Candidate logic was fixed on 2026-11-03. Never tune on future settled outcomes.
No self-declared time or Git chronology independently proves first receipt.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race
from hole_third_choice_research import national_rates, variants

FIRST_ELIGIBLE_DAY=date(2026,11,4)
POLICIES=("baseline","donor_order","max_ticket_score","third_national_rate")
TOPS=(3,5,10)
EXPECTED_MODEL_VERSIONS=frozenset(
    ("CLEAN_FOUR_MODES_V1_UNCALIBRATED",
     "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"))


# Pin exact Git blobs of every research module that chooses candidate tickets.
# Changing one of these files invalidates future comparisons until a separately
# versioned method and fresh future-only window are defined.
LOCKED_SELECTION_BLOBS={
    "hole_third_choice_research.py":"579edc1ae846489d447307fbf03b35fc7d4c09b9",
    "hole_pair_diversification_research.py":"56f06c10f6d07e03b2e37624ecf57dc6de7d8748",
    "hole_top5_safe_bundle_research.py":"a43f53d898ac73829e7f2b24f81624d69d26d74a",
    "hole_pair_third_bundle_research.py":"88c4ed506588a24bb593d104b5d0f59c7502d73a",
}

def verify_locked_selection(root=None):
    """Fail closed if any selector source differs from the precommitted method."""
    source_root=Path(__file__).resolve().parent if root is None else Path(root)
    matches={}
    for name,expected in LOCKED_SELECTION_BLOBS.items():
        source=source_root/name
        if source.is_symlink() or not source.is_file():
            raise ValueError("locked_selector_missing:"+name)
        blob=source.read_bytes()
        actual=hashlib.sha1(b"blob "+str(len(blob)).encode()+b"\0"+blob).hexdigest()
        if actual!=expected:
            raise ValueError("locked_selector_changed:"+name)
        matches[name]=actual
    return matches

def date_from_code(code):
    if not re.fullmatch(r"20[0-9]{10}",code):
        raise ValueError("invalid_race_code")
    return date.fromisoformat(code[:4]+"-"+code[4:6]+"-"+code[6:8])

def evaluate(root,as_of,days=14):
    root=Path(root)
    locked_selector_blobs=verify_locked_selection()
    if as_of < FIRST_ELIGIBLE_DAY:
        return {"status":"not_yet_eligible","formal":False,"comparable":0}
    if type(days) is not int or not 1<=days<=31:
        raise ValueError("invalid_day_window")
    latest_day=as_of
    earliest_day=max(FIRST_ELIGIBLE_DAY,latest_day-timedelta(days=days-1))
    forecast_dir=root/"four_mode_forecasts"
    files=sorted(forecast_dir.glob("20??????????.json")) if forecast_dir.is_dir() else []
    counts={p:{f"top{k}":0 for k in TOPS} for p in POLICIES}
    changes=Counter();skips=Counter()
    rows=[];dates=set()
    daily={}
    by_model={}
    def day_entry(day):
        label=day.isoformat()
        if label not in daily:
            daily[label]={"scanned":0,"comparable":0,"excluded":{},
                          "hits":{p:{f"top{k}":0 for k in TOPS} for p in POLICIES}}
        return daily[label]
    def exclude(day,reason):
        skips[reason]+=1
        d=day_entry(day)["excluded"]
        d[reason]=d.get(reason,0)+1
    for path in files:
        if path.is_symlink():
            skips["symlink_source"]+=1;continue
        try:day=date_from_code(path.stem)
        except ValueError:
            skips["invalid_date_code"]+=1;continue
        if not earliest_day<=day<=latest_day:continue
        code=path.stem
        if code in dates:raise ValueError("duplicate_race")
        dates.add(code)
        day_entry(day)["scanned"]+=1
        status,archive=archived_four_modes(code,root)
        if status!=200:
            exclude(day,"invalid_frozen_archive");continue
        if archive["model_version"] not in EXPECTED_MODEL_VERSIONS:
            exclude(day,"unexpected_model_version");continue
        creation=datetime.fromisoformat(archive["generated_at_jst"])
        cutoff=datetime.fromisoformat(archive["deadline_jst"])
        if (creation.utcoffset()!=timedelta(hours=9)
                or cutoff.utcoffset()!=timedelta(hours=9)
                or creation>=cutoff or cutoff.date()!=day):
            exclude(day,"local_timing_invalid");continue
        # All candidates determined before opening any confirmed result.
        rates=national_rates(code,root)
        picks=variants(archive,rates)
        if set(picks)!=set(POLICIES):raise ValueError("policy_mismatch")
        base=picks["baseline"]
        if any(picks[p][:5]!=base[:5] or len(picks[p])!=len(base)
               for p in POLICIES):
            raise ValueError("top5_protection_failed")
        outcome=compare_race(code,root)
        if outcome.get("status")!="historical_comparison_only":
            exclude(day,"unconfirmed_result");continue
        winner=outcome["winning_ticket"]
        day_entry(day)["comparable"]+=1
        version=archive["model_version"]
        if version not in by_model:
            by_model[version]={"comparable":0,"hits":{
                p:{f"top{k}":0 for k in TOPS} for p in POLICIES}}
        by_model[version]["comparable"]+=1
        flags={}
        for p in POLICIES:
            flags[p]={f"top{k}":winner in picks[p][:k] for k in TOPS}
            changes[p]+=int(picks[p]!=base)
            for k in TOPS:
                key=f"top{k}"
                flag=int(flags[p][key])
                counts[p][key]+=flag
                day_entry(day)["hits"][p][key]+=flag
                by_model[version]["hits"][p][key]+=flag
        rows.append({"race_code":code,"flags":flags,
                     "model_version":archive["model_version"],
                     "local_generated_at_jst":archive["generated_at_jst"]})
    delta={}
    for p in POLICIES:
        if p=="baseline":continue
        delta[p]={}
        for k in TOPS:
            key=f"top{k}"
            gained=sum(int(r["flags"][p][key] and not r["flags"]["baseline"][key])
                       for r in rows)
            lost=sum(int(r["flags"]["baseline"][key] and not r["flags"][p][key])
                     for r in rows)
            if gained-lost!=counts[p][key]-counts["baseline"][key]:
                raise ValueError("attribution_mismatch")
            delta[p][key]={"gained":gained,"lost":lost,"net":gained-lost}
            if k<=5 and (gained or lost):
                raise ValueError("top5_moved")
    if sum(d["scanned"] for d in daily.values())!=len(dates):
        raise ValueError("daily_scanned_denominator_mismatch")
    if sum(d["comparable"] for d in daily.values())!=len(rows):
        raise ValueError("daily_comparable_denominator_mismatch")
    if sum(x["comparable"] for x in by_model.values())!=len(rows):
        raise ValueError("model_comparable_denominator_mismatch")
    if len(rows)+sum(skips.values())!=len(dates):
        # Unparseable/symlink forecast files are recorded separately and
        # must not be silently treated as valid dated forecasts.
        if len(rows)+sum(d["excluded"].get(reason,0)
               for d in daily.values() for reason in d["excluded"])!=len(dates):
            raise ValueError("forecast_inventory_denominator_mismatch")
    for p in POLICIES:
        for k in TOPS:
            key=f"top{k}"
            if (sum(d["hits"][p][key] for d in daily.values())!=counts[p][key]
                    or sum(v["hits"][p][key] for v in by_model.values())!=counts[p][key]):
                raise ValueError("by_day_model_hit_reconciliation")
    # Pin the exact current algorithm bytes in each result to detect later tuning.
    algorithm_path=Path(__file__).resolve().parent/"hole_third_choice_research.py"
    algorithm_sha=hashlib.sha256(algorithm_path.read_bytes()).hexdigest()
    return {"schema":"HOLE_FUTURE_LOCKED_EVAL_V1",
            "status":"post_lock_research_comparison" if rows else "insufficient_new_confirmed_races",
            "method_locked_on_jst":"2026-11-03",
            "first_eligible_jst":FIRST_ELIGIBLE_DAY.isoformat(),
            "window_start_jst":earliest_day.isoformat(),
            "window_end_jst":latest_day.isoformat(),
            "algorithm_sha256":algorithm_sha,
            "locked_selector_git_blobs":locked_selector_blobs,
            "scanned_valid_date_codes":len(dates),
            "by_day":dict(sorted(daily.items())),
            "by_model_version":dict(sorted(by_model.items())),
            "evidence_quality":{
                "archive_file_creation_time_is_self_reported":True,
                "independent_remote_first_receipt_proof_present":False,
                "confirmed_result_file_required":True,
                "eligible_for_formal_accuracy":False,
            },
            "comparable":len(rows),"excluded_by_reason":dict(skips),
            "hits":counts,"changed":dict(changes),"delta":delta,
            "race_codes":[r["race_code"] for r in rows],
            "race_flags":{r["race_code"]:r["flags"] for r in rows},
            "formal":False,"independent_first_receipt_verified":False,
            "prospective_validation":False,"production_forecast_changed":False,
            "candidate_scores_calibrated":False,
            "warning":"Future period relative to the 2026-11-03 rule lock, but not independently verified as received before race deadline. No formal predictive accuracy or promotion."}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",default=".")
    parser.add_argument("--as-of",default=datetime.now(timezone(timedelta(hours=9))).date().isoformat())
    parser.add_argument("--days",type=int,default=14)
    args=parser.parse_args()
    print(json.dumps(evaluate(args.root,date.fromisoformat(args.as_of),args.days),
                     ensure_ascii=False,sort_keys=True))

if __name__=="__main__":main()
