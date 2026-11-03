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
from entry_course_durable_ledger import github_ops, publish

JST=timezone(timedelta(hours=9))
CODE=re.compile(r"20[0-9]{10}\Z")


def candidates(root, *, now=None, max_minutes=12):
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
            output_dir=None, max_minutes=12, min_starts=10):
    now=now or (lambda:datetime.now(JST))
    target=candidates(root,now=now(),max_minutes=max_minutes)
    if not target:
        return {"status":"no_frozen_baseline_in_late_window","stored":False,"research_only":True}
    late,code,base=target[0]
    remaining=(late-now()).total_seconds()
    if remaining<45:
        return {"status":"too_close_to_late_cutoff","stored":False,"race_code":code,"research_only":True}
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
    if card_reader is None:
        from clean_racecard import racecard
        card_reader=racecard
    reason="late_preview_unavailable"
    # At most three attempts; no polling or storage after the research cutoff.
    for attempt_number in range(3):
        if now()>=late-timedelta(seconds=10):
            break
        try:
            card=card_reader(code[:8],code[8:10],code[10:12])
            candidate=prepare_late_preview_study(
                base,card,batch,frozen_at=now().isoformat(),min_starts=min_starts)
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
            return verdict
        except (ValueError,OSError,KeyError,TypeError,TimeoutError) as exc:
            reason=str(exc) if str(exc) else type(exc).__name__
            # If local freeze exists but remote write fails, never rerun to
            # regenerate the candidate or overwrite its evidence.
            if reason.startswith(("course_ledger_","late_capture_remote_",
                                  "remote_published_after_","immutable_late_",
                                  "late_study_remote_publish_")):
                raise
        if attempt_number<2 and now()+timedelta(seconds=35)<late:
            sleep(35)
        else:
            break
    return {"status":"ineligible_late_study","stored":False,
            "race_code":code,"reason":reason,"source_failures":len(fetch_errors),
            "research_only":True}


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=".")
    p.add_argument("--output",default="entry-course-evidence/last-attempt.json")
    args=p.parse_args()
    try:
        verdict=attempt(Path(args.root))
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
