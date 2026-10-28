"""Read-only Git first-add attestation for a complete daily four-mode archive cohort.

This verifies Git history and byte identity. It does not validate result sources
or assert any winning ticket / ROI.
"""
import argparse
import json
import re
from pathlib import Path
from verification_pipeline import attest_first_git_add

ROOT=Path(__file__).resolve().parent

def audit(day,root=ROOT,checker=attest_first_git_add):
    if not re.fullmatch(r"20\d{6}",day):raise ValueError("invalid_day")
    paths=sorted((root/"four_mode_forecasts").glob(day+"*.json"))
    failed=[];verified=0;commits=set()
    for path in paths:
        try:
            record=json.loads(path.read_text(encoding="utf-8"))
            if record.get("race_code")!=path.stem:raise ValueError("identity_mismatch")
            sha=checker(path,record["deadline_jst"])
            if not sha:raise ValueError("first_add_proof_missing")
            commits.add(sha);verified+=1
        except (ValueError,KeyError,TypeError,OSError,RuntimeError) as exc:
            failed.append({"race_code":path.stem,"issue":str(exc)[:120]})
    return {"schema":"CLEAN_DAILY_FIRST_ADD_AUDIT_V1","day_jst":day,
            "archives":len(paths),"verified_first_add":verified,"unique_first_add_commits":len(commits),
            "failures":failed,"official_results_checked":False,"actual_hit_rate_calculated":False}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("day")
    args=parser.parse_args()
    report=audit(args.day)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    if report["failures"] or report["archives"]==0:raise SystemExit(1)
