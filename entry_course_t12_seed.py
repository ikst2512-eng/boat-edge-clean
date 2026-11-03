"""Prospective T-12 research baseline seeding for course experiments.

Automatically freezes the EXISTING research_model.predict only when the
current source and local clock precede its 12-minute deadline. The original
JSON is kept byte-for-byte, on a separate immutable research evidence branch.
This does not promote or change the four formal modes.
"""
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
import csv
import hashlib
import io
import json
import re

from entry_course_durable_ledger import github_ops
from research_model import JST, predict, _record_path

URL_ROOT="https://boatracecsv.github.io/data/programs/title/"
CODE=re.compile(r"20[0-9]{10}\Z")
SHA=re.compile(r"[a-f0-9]{64}\Z")
ALLOWED_WINDOW=(3,9)  # Between three and nine minutes BEFORE T-12.
MAX_FILE=20_000


def _dt(raw):
    try:
        dt=datetime.fromisoformat(raw)
        return dt if dt.utcoffset() is not None else None
    except (ValueError,TypeError):
        return None


def _title(now, *, fetch=None):
    if now.utcoffset() is None:
        raise ValueError("t12_clock_without_timezone")
    day=now.astimezone(JST).strftime("%Y%m%d")
    url=f"{URL_ROOT}{day[:4]}/{day[4:6]}/{day[6:8]}.csv"
    if fetch is None:
        def fetch(url):
            with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=8) as r:
                if r.status!=200:
                    raise ValueError("t12_title_http_failure")
                return r.read(250_001)
    raw=fetch(url)
    if type(raw) is not bytes or len(raw)>250_000 or not raw:
        raise ValueError("t12_title_bad_source_size")
    try:
        parsed=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if not parsed.fieldnames or not {"レースコード","電話投票締切予定"}.issubset(parsed.fieldnames):
            raise ValueError("t12_title_source_schema_invalid")
        rows=list(parsed)
    except (UnicodeError,csv.Error) as exc:
        raise ValueError("t12_title_csv_invalid") from exc
    return rows,day,hashlib.sha256(raw).hexdigest()


def near_t12(rows, day, *, now, max_per_run=3):
    """Do not target races if already at/after the 12-minute cutoff."""
    if now.utcoffset() is None or type(max_per_run) is not int or not 1<=max_per_run<=10:
        raise ValueError("t12_selection_invalid")
    found=[]
    for row in rows:
        code=row.get("レースコード")
        clock=row.get("電話投票締切予定")
        if type(code) is not str or not CODE.fullmatch(code) or code[:8]!=day:
            continue
        if type(clock) is not str or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",clock):
            continue
        deadline=datetime.strptime(day+clock,"%Y%m%d%H:%M").replace(tzinfo=JST)
        cutoff=deadline-timedelta(minutes=12)
        remaining=(cutoff-now).total_seconds()
        if ALLOWED_WINDOW[0]*60<=remaining<=ALLOWED_WINDOW[1]*60:
            found.append((cutoff,code))
    return [code for cutoff,code in sorted(set(found))[:max_per_run]]


def validate_base(raw, code, *, now):
    if type(raw) is not bytes or len(raw)>MAX_FILE:
        raise ValueError("t12_archive_invalid_size")
    try:
        d=json.loads(raw)
    except (ValueError,UnicodeError) as exc:
        raise ValueError("t12_archive_invalid_json") from exc
    if (type(d) is not dict or d.get("race_code")!=code or
            d.get("status")!="research" or d.get("validated") is not False or
            d.get("model_version")!="national-beta0.4-exploratory-v1"):
        raise ValueError("t12_archive_invalid_reference")
    deadline=_dt(d.get("source_deadline_jst"))
    cutoff=_dt(d.get("cutoff_jst"))
    generated=_dt(d.get("generated_at"))
    title=_dt(d.get("source_title_received_jst"))
    card=_dt(d.get("source_cards_received_jst"))
    if (not all([deadline,cutoff,generated,title,card]) or
            cutoff!=deadline-timedelta(minutes=12) or
            max(generated,title,card)>cutoff or now.utcoffset() is None or now>=cutoff):
        raise ValueError("t12_archive_missed_cutoff")
    from research_model import probabilities
    rates=d.get("national_win_rates")
    if (type(rates) is not list or len(rates)!=6 or
        d.get("predictions")!=["-".join(map(str,t)) for t,p in probabilities(rates)[:10]]):
        raise ValueError("t12_archive_baseline_rank_drift")
    for key in ("source_title_sha256","source_cards_sha256",
                "input_sha256","model_source_sha256"):
        if not SHA.fullmatch(str(d.get(key) or "")):
            raise ValueError("t12_archive_missing_digest")
    return f"t12_baselines/{code[:8]}/{code}.json"


def publish_base(raw, code, remote_read, remote_create, *, clock):
    now=clock()
    path=validate_base(raw,code,now=now)
    previous=remote_read(path)
    if previous is not None and previous!=raw:
        raise ValueError("t12_existing_baseline_immutable_conflict")
    if previous is None:
        remote_create(path,raw)
        state="new_t12_baseline"
    else:
        state="existing_identical_t12_baseline"
    if remote_read(path)!=raw:
        raise ValueError("t12_baseline_readback_failed")
    if clock()>=_dt(json.loads(raw)["cutoff_jst"]):
        raise ValueError("t12_baseline_remote_commit_after_cutoff")
    return {"status":state,"path":path,
            "sha256":hashlib.sha256(raw).hexdigest(),"research_only":True,
            "formal":False,"forecast_record":True,
            "independent_first_seen_verified":False}


def seed_once(*, now, fetch_title=None, predictor=predict,
              record_path=_record_path, ledger_ops=None, max_per_run=3):
    """Use unchanged predict() and its original on-disk T-12 evidence."""
    first=now()
    rows,day,title_digest=_title(first,fetch=fetch_title)
    eligible=near_t12(rows,day,now=now(),max_per_run=max_per_run)
    if not eligible:
        return {"status":"no_races_in_t12_generation_window",
                "day":day,"eligible_count":0,"stored_count":0,
                "title_sha256":title_digest,"research_only":True}
    if ledger_ops is None:
        import os
        ledger_ops=github_ops(os.environ["GITHUB_REPOSITORY"])
    read,create=ledger_ops
    states=[]
    for code in eligible:
        try:
            # A GitHub Actions retry starts on a fresh filesystem. Re-running
            # predict() would produce a *different* generated_at and immutable
            # bytes for an already archived race. Check readback FIRST.
            remote_path=f"t12_baselines/{code[:8]}/{code}.json"
            existing=read(remote_path)
            if existing is not None:
                path=validate_base(existing,code,now=now())
                if path!=remote_path:
                    raise ValueError("t12_existing_baseline_wrong_path")
                if read(remote_path)!=existing:
                    raise ValueError("t12_existing_baseline_readback_changed")
                states.append({"race_code":code,"status":"existing_identical_t12_baseline",
                               "path":remote_path,
                               "sha256":hashlib.sha256(existing).hexdigest(),
                               "research_only":True,"formal":False,
                               "forecast_record":True,
                               "independent_first_seen_verified":False})
                continue
            # Only the FIRST invocation may create a fresh original. The
            # immutable ledger's create-only write rejects concurrent races.
            predictor(code[:8],code[8:10],code[10:12])
            path=record_path(code)
            raw=path.read_bytes()
            states.append(dict(race_code=code,
                               **publish_base(raw,code,read,create,clock=now)))
        except Exception as exc:
            states.append({"race_code":code,"status":"failed",
                           "error_type":type(exc).__name__,
                           "error_code":str(exc)[:120] if isinstance(exc,ValueError) else None})
    return {"status":"t12_generation_attempted","day":day,
            "eligible_count":len(eligible),
            "stored_count":sum(s["status"] in ("new_t12_baseline","existing_identical_t12_baseline") for s in states),
            "title_sha256":title_digest,"results":states,"research_only":True}


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="entry-course-evidence/t12-seed.json")
    args=p.parse_args()
    try:
        report=seed_once(now=lambda:datetime.now(JST))
    except Exception as exc:
        report={"status":"t12_seed_failed","error_type":type(exc).__name__,
                "error_code":str(exc)[:120] if isinstance(exc,ValueError) else None,
                "research_only":True}
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    print("T12_BASELINE_SEED="+json.dumps(report,ensure_ascii=False))
    if report["status"]=="t12_seed_failed" or any(x["status"]=="failed" for x in report.get("results",[])):
        raise SystemExit(2)


if __name__=="__main__":
    main()
