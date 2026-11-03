"""Bounded scheduled attempt to freeze ONE late-preview course study per run.

Never reads result for today's target, never changes production predictions,
and reports explicit no-op reasons. GitHub Actions may run late; all cutoff
checks use real UTC time and a late run cannot fabricate a prospective freeze.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
import json
import os
import re
import sys
import time

from entry_course_history_source import BASE, _fetch, load_asof_history
from entry_course_late_preview import prepare_late_preview_study
from entry_course_write_once import freeze_capture
from entry_course_durable_ledger import github_ops, publish, verify_write_access

JST=timezone(timedelta(hours=9))
CODE=re.compile(r"20[0-9]{10}\Z")


def candidates(root, *, now=None, max_minutes=6):
    """Return only current-day frozen bases nearing later T-2 cutoff."""
    now=now or datetime.now(JST)
    root=Path(root)
    matches=[]
    for file in sorted((root/"research_snapshots").glob("20*.json")):
        if file.is_symlink() or file.stat().st_size>30000:
            continue
        try:
            base=json.loads(file.read_text(encoding="utf-8"))
            code=base["race_code"]
            if not isinstance(code,str) or CODE.fullmatch(code) is None or file.stem!=code or code[:8]!=now.strftime("%Y%m%d"):
                continue
            freeze=datetime.fromisoformat(base["generated_at"])
            t12=datetime.fromisoformat(base["cutoff_jst"])
            deadline=datetime.fromisoformat(base["source_deadline_jst"])
            late=deadline-timedelta(minutes=2)
            if any(t.utcoffset() is None for t in (freeze,t12,deadline)):
                continue
            if (base.get("status")!="research" or base.get("validated") is not False
                    or not freeze<=t12<late or not 45 <= (late-now).total_seconds() <= max_minutes*60):
                continue
            matches.append((late,code,base))
        except (OSError,TypeError,KeyError,ValueError,UnicodeError):
            continue
    return sorted(matches,key=lambda x:(x[0],x[1]))


def historical_prefetch(day, *, lookback_days=31, fetch=_fetch, workers=6):
    """Download bounded past-date CSVs concurrently; no target-date results."""
    day=datetime.strptime(day,"%Y%m%d").date()
    urls=[]
    for n in range(1,lookback_days+1):
        date=(day-timedelta(days=n)).strftime("%Y/%m/%d.csv")
        urls.extend([BASE+"programs/race_cards/"+date,BASE+"results/realtime/"+date])
    cached={}
    errors={}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future={pool.submit(fetch,url):url for url in urls}
        for task in as_completed(future):
            url=future[task]
            try:
                raw=task.result()
                if type(raw) is not bytes or len(raw)>2_000_000:
                    raise ValueError("invalid_source_bytes")
                cached[url]=raw
            except (OSError,ValueError,HTTPError,URLError,TimeoutError) as exc:
                errors[url]=type(exc).__name__
    return cached,errors


def attempt(root, *, now=None, prefetch=historical_prefetch,
            card_reader=None, ledger_ops=None, sleep=time.sleep,
            output_dir=None, max_minutes=6, min_starts=10):
    now=now or (lambda:datetime.now(JST))
    target=candidates(root,now=now(),max_minutes=max_minutes)
    if not target:
        return {"status":"no_frozen_baseline_in_late_window","stored":False,"research_only":True}
    late,code,base=target[0]
    remaining=(late-now()).total_seconds()
    if remaining<45:
        return {"status":"too_close_to_late_cutoff","stored":False,"race_code":code,"research_only":True}
    if card_reader is None:
        from clean_racecard import racecard
        card_reader=racecard
    # Read the real race preview first; do not download 62 historical CSVs
    # when the T-5 preview is still unpublished.
    from entry_course_prospective_capture import _entry_from_preview
    card=None
    preview_error="late_preview_unavailable"
    preview_attempts=0
    for i in range(3):
        if now()>=late-timedelta(seconds=10):
            break
        preview_attempts+=1
        try:
            observed=card_reader(code[:8],code[8:10],code[10:12])
            meta=observed.get("meta",{})
            if (observed.get("race_key")!=f"{code[:8]}-{code[8:10]}-{code[10:]}"
                    or meta.get("phase")!="PRE_RESULT"
                    or meta.get("results_seen") is not False):
                raise ValueError("not_verified_same_race_preresult")
            _, preview_receipts=_entry_from_preview(
                observed,late)
            from entry_course_prospective_capture import _when
            if any(_when(item["received_at"])>now() for item in preview_receipts):
                raise ValueError("preview_receipt_after_current_clock")
            card=observed
            break
        except (ValueError,OSError,KeyError,TypeError,TimeoutError) as exc:
            preview_error=str(exc) or type(exc).__name__
        if i<2 and now()+timedelta(seconds=35)<late:
            sleep(35)
        else:
            break
    if card is None:
        return {"status":"preview_not_ready","stored":False,
                "race_code":code,"preview_attempts":preview_attempts,
                "reason":preview_error,"historical_requests":0,
                "research_only":True}
    cache,fetch_errors=prefetch(code[:8])
    if now()>=late:
        return {"status":"history_fetch_crossed_late_cutoff","stored":False,"race_code":code,
                "source_failures":len(fetch_errors),"research_only":True}
    # Source code reports missing archived rows. It does not inject substitutes.
    def local_fetch(url):
        if url not in cache:
            raise OSError("historical_source_not_downloaded")
        return cache[url]
    batch=load_asof_history(code[:8],late.isoformat(),lookback_days=31,
                           fetch=local_fetch,clock=now)
    if not batch["history"]:
        return {"status":"no_verified_historical_pairs","stored":False,
                "race_code":code,"source_failures":len(fetch_errors),"research_only":True}
    reason="late_preview_unavailable"
    # Preview has been preflighted; use a fresh frozen_at after all source reads.
    # A result or future receipt must never be used to repair this cohort.
    if now()>=late-timedelta(seconds=10):
        return {"status":"history_fetch_too_close_to_cutoff",
                "stored":False,"race_code":code,
                "source_failures":len(fetch_errors),"research_only":True}
    try:
        candidate=prepare_late_preview_study(
            base,card,batch,frozen_at=now().isoformat(),min_starts=min_starts)
    except (ValueError,OSError,KeyError,TypeError,TimeoutError) as exc:
        reason=str(exc) or type(exc).__name__
        diagnostics={}
        if reason=="late_study_insufficient_course_samples":
            # Inspect the same as-of historical rows, without relaxing the
            # minimum or generating any prediction, to explain coverage gaps.
            from entry_course_history import compile_asof_course_history
            from entry_course_prospective_capture import _entry_from_preview
            entry,_=_entry_from_preview(card,late)
            coverage=compile_asof_course_history(
                card,batch["history"],cutoff_at=late.isoformat(),
                entry=entry,min_starts=min_starts)
            diagnostics["course_start_counts"]={
                str(r["boat"]):r["courseStarts"] for r in coverage["boats"]}
            diagnostics["insufficient_boats"]=[
                r["boat"] for r in coverage["boats"] if not r["sufficient_sample"]]
            diagnostics["historical_exclusions"]=coverage["excluded"]
        return {"status":"ineligible_late_study","stored":False,
                "race_code":code,"reason":reason,
                "preview_attempts":preview_attempts,
                "eligible_historical_pairs":len(batch["history"]),
                "source_failures":len(fetch_errors),**diagnostics,
                "research_only":True}
    dest=output_dir or (Path(root)/"entry_course_attempts")
    path=freeze_capture(candidate,dest,clock=now)
    if now()>=late:
        raise ValueError("late_study_remote_publish_cutoff_exceeded")
    if ledger_ops is None:
        ledger_ops=github_ops(os.environ["GITHUB_REPOSITORY"])
    remote_read,remote_create=ledger_ops
    verdict=publish(path.read_bytes(),remote_read,remote_create,clock=now)
    verdict["race_code"]=code
    verdict["source_failures"]=len(fetch_errors)
    verdict["preview_attempts"]=preview_attempts
    verdict["eligible_historical_pairs"]=len(batch["history"])
    return verdict


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=".")
    p.add_argument("--output",default="entry-course-evidence/last-attempt.json")
    args=p.parse_args()
    try:
        remote_read,remote_create=github_ops(os.environ['GITHUB_REPOSITORY'])
        access=verify_write_access(remote_read,remote_create)
        verdict=attempt(Path(args.root),ledger_ops=(remote_read,remote_create))
        verdict['ledger_write_access_probe']=access
    except Exception as exc:
        verdict={"status":"course_evidence_collector_failed","stored":False,
                 "error_type":type(exc).__name__,"research_only":True}
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(verdict,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    print("COURSE_LATE_EVIDENCE="+json.dumps(verdict,ensure_ascii=False,sort_keys=True))
    if verdict["status"]=="course_evidence_collector_failed":
        raise SystemExit(2)

if __name__=="__main__":
    main()
