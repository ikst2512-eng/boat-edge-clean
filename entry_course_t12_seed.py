"""Prospective T-12 research baseline seeding for course experiments.

Automatically freezes the EXISTING research_model.predict only when the
current source and local clock precede its 12-minute deadline. The original
JSON is kept byte-for-byte, on a separate immutable research evidence branch.
This does not promote or change the four formal modes.
"""
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
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
ALLOWED_WINDOW=(2,14)  # 2–14 minutes BEFORE T-12; retries remain strictly pre-cutoff.
MAX_FILE=20_000


def _dt(raw):
    try:
        dt=datetime.fromisoformat(raw)
        return dt if dt.utcoffset() is not None else None
    except (ValueError,TypeError):
        return None


def _title(now, *, fetch=None, fallback=None):
    if now.utcoffset() is None:
        raise ValueError("t12_clock_without_timezone")
    day=now.astimezone(JST).strftime("%Y%m%d")
    url=f"{URL_ROOT}{day[:4]}/{day[4:6]}/{day[6:8]}.csv"
    live_fetch=fetch is None
    if fetch is None:
        def fetch(url):
            with urlopen(Request(url,headers={"User-Agent":"BOAT-EDGE-CLEAN-RESEARCH/1.0"}),timeout=8) as r:
                if r.status!=200:
                    raise ValueError("t12_title_http_failure")
                return r.read(250_001)
    try:
        raw=fetch(url)
    except (OSError,TimeoutError,URLError,HTTPError) as exc:
        # The daily *published archive* can be missing while races are open.
        # Use the same independent pre-race holding schedule accepted by
        # clean_racecard; never read a result or accept an untimed source.
        if fallback is None:
            from clean_direct_sources import holding_rows
            fallback=holding_rows
        rows,observed,digest=fallback(day)
        if (not isinstance(rows,list) or not rows or
                not isinstance(observed,datetime) or observed.utcoffset() is None or
                observed>now + timedelta(seconds=30) or
                not SHA.fullmatch(str(digest or ""))):
            raise ValueError("t12_live_schedule_receipt_invalid") from exc
        return rows,day,digest,"live_holding_schedule"
    if type(raw) is not bytes or len(raw)>250_000 or not raw:
        raise ValueError("t12_title_bad_source_size")
    try:
        parsed=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if not parsed.fieldnames or not {"レースコード","電話投票締切予定"}.issubset(parsed.fieldnames):
            raise ValueError("t12_title_source_schema_invalid")
        rows=list(parsed)
    except (UnicodeError,csv.Error) as exc:
        raise ValueError("t12_title_csv_invalid") from exc
    archive_digest=hashlib.sha256(raw).hexdigest()
    # A published daily file can itself be an earlier, partial snapshot.
    # In live operation, supplement *only missing race codes* using a
    # separately receipt-backed, pre-result holding schedule. Never silently
    # overwrite a conflicting existing deadline.
    if live_fetch or fallback is not None:
        if fallback is None:
            from clean_direct_sources import holding_rows
            fallback=holding_rows
        try:
            live_rows,observed,live_digest=fallback(day)
            if (not isinstance(live_rows,list) or not live_rows or
                    not isinstance(observed,datetime) or observed.utcoffset() is None or
                    observed>now+timedelta(seconds=30) or
                    not SHA.fullmatch(str(live_digest or ""))):
                raise ValueError("t12_live_schedule_receipt_invalid")
        except (OSError,TimeoutError,ValueError,KeyError,URLError,HTTPError):
            # Already valid public archive remains usable; no fabricated
            # supplementation or source-confidence claim.
            return rows,day,archive_digest,"published_daily_title"
        current={r["レースコード"]:r for r in rows
                 if isinstance(r,dict) and isinstance(r.get("レースコード"),str)}
        additions=[]
        conflicts=set()
        for entry in live_rows:
            if not isinstance(entry,dict):
                continue
            code=entry.get("レースコード")
            clock=entry.get("電話投票締切予定")
            if (type(code) is not str or not CODE.fullmatch(code) or
                    code[:8]!=day or type(clock) is not str or
                    re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",clock) is None):
                continue
            if code in current:
                if current[code].get("電話投票締切予定")!=clock:
                    conflicts.add(code)
                continue
            if code not in {r["レースコード"] for r in additions}:
                additions.append(entry)
        if conflicts:
            # Conflicting deadlines are not a safe basis for pre-cutoff
            # publication, even when the target race looks eligible.
            rows=[r for r in rows if r.get("レースコード") not in conflicts]
        if additions or conflicts:
            combined=hashlib.sha256(
                (archive_digest+":"+live_digest).encode("ascii")).hexdigest()
            return rows+additions,day,combined,"published_title_plus_live_checked"
    return rows,day,archive_digest,"published_daily_title"


def near_t12(rows, day, *, now, max_per_run=5):
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


def validate_base(raw, code, *, now, expected_deadline=None):
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
            (expected_deadline is not None and deadline!=expected_deadline) or
            cutoff!=deadline-timedelta(minutes=12) or
            max(generated,title,card)>=cutoff or
            now.utcoffset() is None or now>=cutoff or
            max(generated,title,card)>now):
        raise ValueError("t12_archive_missed_cutoff")
    # A pre-existing research_snapshots/<race>.json can be hours old:
    # research_model.predict() reuses it verbatim. It must not masquerade
    # as a forecast generated during this T-12 selection window.
    if generated < cutoff-timedelta(minutes=ALLOWED_WINDOW[1]):
        raise ValueError("t12_archive_generated_before_selection_window")
    if title>generated or card>generated:
        raise ValueError("t12_archive_source_received_after_generation")
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


def publish_base(raw, code, remote_read, remote_create, *, clock,
                 expected_deadline=None):
    now=clock()
    path=validate_base(raw,code,now=now,expected_deadline=expected_deadline)
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


def _fresh_t12_prediction_bytes(code):
    """Run the unchanged research model in an empty, isolated snapshot store.

    Earlier research_snapshots/<race>.json files are immutable research
    history and must not be mistaken for a fresh T-12 model generation.
    One GitHub Actions seed process runs sequentially; the temporary STORE
    override is restored before returning, even when the source fails.
    """
    import tempfile
    import research_model
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix="boat-edge-t12-") as root:
        isolated=Path(root)
        with patch.object(research_model,"STORE",isolated):
            predict(code[:8],code[8:10],code[10:12])
            original=isolated/(code+".json")
            if original.is_symlink() or not original.is_file():
                raise ValueError("t12_fresh_model_original_missing")
            return original.read_bytes()


def seed_once(*, now, fetch_title=None, fallback_title=None, predictor=predict,
              record_path=_record_path, ledger_ops=None, max_per_run=10):
    """Use unchanged predict() and its original on-disk T-12 evidence."""
    first=now()
    rows,day,title_digest,title_source=_title(first,fetch=fetch_title,fallback=fallback_title)
    eligible=near_t12(rows,day,now=now(),max_per_run=max_per_run)
    if not eligible:
        return {"status":"no_races_in_t12_generation_window",
                "day":day,"eligible_count":0,"stored_count":0,
                "newly_stored_count":0,"reused_count":0,"failed_count":0,
                "title_sha256":title_digest,"title_schedule_source":title_source,"research_only":True}
    if ledger_ops is None:
        import os
        ledger_ops=github_ops(os.environ["GITHUB_REPOSITORY"])
    read,create=ledger_ops
    # Bind the candidate's scheduling deadline to its immutable prediction.
    # The predictor uses multiple source types, which may disagree.
    expected_deadlines={}
    for row in rows:
        code=row.get("レースコード")
        if code not in eligible:
            continue
        clock_text=row.get("電話投票締切予定")
        expected=datetime.strptime(day+clock_text,"%Y%m%d%H:%M").replace(tzinfo=JST)
        previous=expected_deadlines.get(code)
        if previous is not None and previous!=expected:
            raise ValueError("t12_conflicting_schedule_deadlines")
        expected_deadlines[code]=expected
    if len(expected_deadlines)!=len(eligible):
        raise ValueError("t12_selected_schedule_incomplete")
    states=[]
    for code in eligible:
        try:
            # A GitHub Actions retry starts on a fresh filesystem. Re-running
            # predict() would produce a *different* generated_at and immutable
            # bytes for an already archived race. Check readback FIRST.
            remote_path=f"t12_baselines/{code[:8]}/{code}.json"
            existing=read(remote_path)
            if existing is not None:
                path=validate_base(existing,code,now=now(),
                                   expected_deadline=expected_deadlines[code])
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
            if predictor is predict and record_path is _record_path:
                # Main unattended path always generates new T-12-timed bytes
                # without mutating existing local research_snapshots.
                raw=_fresh_t12_prediction_bytes(code)
            else:
                # Preserve the explicit dependency-injection interface used
                # by deterministic test/replay fixtures.
                predictor(code[:8],code[8:10],code[10:12])
                raw=record_path(code).read_bytes()
            states.append(dict(race_code=code,
                               **publish_base(raw,code,read,create,clock=now,
                                              expected_deadline=expected_deadlines[code])))
        except Exception as exc:
            states.append({"race_code":code,"status":"failed",
                           "error_type":type(exc).__name__,
                           "error_code":str(exc)[:120] if isinstance(exc,ValueError) else None})
    newly_stored=sum(s["status"]=="new_t12_baseline" for s in states)
    reused=sum(s["status"]=="existing_identical_t12_baseline" for s in states)
    errors=sum(s["status"]=="failed" for s in states)
    if newly_stored+reused+errors!=len(states):
        raise ValueError("t12_unrecognized_publish_verdict")
    return {"status":"t12_generation_attempted","day":day,
            "eligible_count":len(eligible),
            "stored_count":newly_stored+reused,
            "newly_stored_count":newly_stored,"reused_count":reused,
            "failed_count":errors,
            "title_sha256":title_digest,"title_schedule_source":title_source,
            "results":states,"research_only":True}


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="entry-course-evidence/t12-seed.json")
    args=p.parse_args()
    try:
        from entry_course_scheduled_write_probe import from_environment
        import os
        remote_read,remote_create=github_ops(os.environ["GITHUB_REPOSITORY"])
        access=from_environment("t12",remote_read,remote_create)
        report=seed_once(now=lambda:datetime.now(JST),
                         ledger_ops=(remote_read,remote_create))
        report["scheduled_actions_write_probe"]=access
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
