"""Read-only Git first-add audit for 2026-11-04+ hole frozen predictions.

A Git first-add commit and self-declared committer date are NOT independent
GitHub remote receipt timestamps. NEVER classify this as formal accuracy proof.
"""
import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from hole_future_locked_eval import FIRST_ELIGIBLE_DAY, verify_locked_selection

JST=timezone(timedelta(hours=9))
HEX40=re.compile(r"[a-f0-9]{40}\Z")
CODE=re.compile(r"20[0-9]{10}\Z")
MAX_FORECAST_BYTES=30000


def first_add(code, root, git=None):
    """Audit the exact original main-line Git blob, using local full history."""
    if type(code) is not str or not CODE.fullmatch(code):
        raise ValueError("invalid_race_code")
    root=Path(root)
    path=f"four_mode_forecasts/{code}.json"
    file=root/path
    if file.is_symlink() or not file.is_file() or file.stat().st_size>MAX_FORECAST_BYTES:
        return {"status":"source_unavailable_or_unsafe","race_code":code}
    status,archive=archived_four_modes(code,root)
    if status!=200:
        return {"status":"invalid_frozen_archive","race_code":code}
    cutoff=datetime.fromisoformat(archive["deadline_jst"])-timedelta(minutes=12)
    if cutoff.utcoffset()!=timedelta(hours=9):
        return {"status":"invalid_cutoff_timezone","race_code":code}
    call=git or (lambda *args: subprocess.check_output(
        ["git",*args],cwd=root,timeout=30))
    try:
        firsts=call("log","--first-parent","--diff-filter=A","--format=%H",
                    "--",path).decode().splitlines()
    except (OSError,subprocess.SubprocessError,UnicodeError) as exc:
        return {"status":"git_history_unavailable","race_code":code,
                "error_type":type(exc).__name__}
    if len(firsts)!=1 or not HEX40.fullmatch(firsts[0]):
        return {"status":"unique_first_add_not_found","race_code":code,
                "candidate_commit_count":len(firsts)}
    sha=firsts[0]
    try:
        original=call("show",sha+":"+path)
        claimed_time=call("show","--no-patch","--format=%cI",sha).decode().strip()
        recorded=datetime.fromisoformat(claimed_time)
    except (OSError,subprocess.SubprocessError,UnicodeError,ValueError) as exc:
        return {"status":"first_add_blob_unavailable","race_code":code,
                "error_type":type(exc).__name__}
    if recorded.utcoffset() is None:
        return {"status":"invalid_committer_clock","race_code":code}
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    if hashlib.sha256(original).hexdigest()!=digest:
        return {"status":"current_archive_differs_from_first_add",
                "race_code":code,"first_add_commit":sha,
                "current_sha256":digest,
                "first_add_sha256":hashlib.sha256(original).hexdigest()}
    # This is a local self-declared Git clock, NOT remote first-seen.
    return {
        "status":("local_git_first_add_clock_before_t12_unverified"
                  if recorded<cutoff else "local_git_first_add_clock_late"),
        "race_code":code,"first_add_commit":sha,
        "source_sha256":digest,
        "commit_committer_time_self_declared":recorded.isoformat(),
        "t_minus_12_jst":cutoff.isoformat(),
        "content_exact_first_add_match":True,
        "remote_first_receipt_verified":False,
        "formal":False,
    }


def audit(root,as_of,days=14,git=None):
    root=Path(root)
    verify_locked_selection()
    if type(days) is not int or not 1<=days<=31:
        raise ValueError("invalid_day_window")
    if not isinstance(as_of,date) or isinstance(as_of,datetime):
        raise ValueError("invalid_as_of")
    start=max(FIRST_ELIGIBLE_DAY,as_of-timedelta(days=days-1))
    directory=root/"four_mode_forecasts"
    paths=sorted(directory.glob("20??????????.json")) if directory.is_dir() else []
    rows=[];counts=Counter();days_seen=Counter()
    for path in paths:
        if not CODE.fullmatch(path.stem):
            continue
        try:
            day=date.fromisoformat(path.stem[:4]+"-"+path.stem[4:6]+"-"+path.stem[6:8])
        except ValueError:
            continue
        if day<start or day>as_of:
            continue
        if path.is_symlink():
            row={"race_code":path.stem,"status":"source_unavailable_or_unsafe"}
        else:
            row=first_add(path.stem,root,git)
        rows.append(row)
        counts[row["status"]]+=1
        days_seen[day.isoformat()]+=1
    if sum(counts.values())!=len(rows) or sum(days_seen.values())!=len(rows):
        raise ValueError("first_add_denominator_mismatch")
    return {
        "schema":"HOLE_FUTURE_LOCAL_FIRST_ADD_AUDIT_V1",
        "status":"read_only_first_add_git_evidence_not_remote_attestation",
        "first_eligible_jst":FIRST_ELIGIBLE_DAY.isoformat(),
        "window_start_jst":start.isoformat(),
        "window_end_jst":as_of.isoformat(),
        "scanned_forecasts":len(rows),"counts":dict(sorted(counts.items())),
        "by_day":dict(sorted(days_seen.items())),"records":rows,
        "independent_remote_first_receipt_verified":False,
        "eligible_for_formal_accuracy":False,"formal":False,
        "locked_selector_changed":False,"production_forecast_changed":False,
        "warning":"Matching first-add Git blob prevents local archive attribution "
                  "errors but committer dates are self-declared. This is not "
                  "independent proof of first remote receipt before the cutoff."
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",default=".")
    parser.add_argument("--as-of",default=datetime.now(JST).date().isoformat())
    parser.add_argument("--days",type=int,default=14)
    args=parser.parse_args()
    print(json.dumps(audit(args.root,date.fromisoformat(args.as_of),args.days),
                     ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
