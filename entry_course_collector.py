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
from entry_course_baseline_audit import audit_daily_bases
from entry_waku10_source import fetch_waku10
from entry_waku10_pilot import prepare_waku10_pilot
from entry_waku10_durable_ledger import publish_waku10, validate_waku10_archive

JST=timezone(timedelta(hours=9))
CODE=re.compile(r"20[0-9]{10}\Z")


def candidates(root, *, now=None, max_minutes=6, require_durable_t12=False):
    """Return only current-day frozen bases nearing later T-2 cutoff."""
    now=now or datetime.now(JST)
    root=Path(root)
    matches=[]
    day=now.strftime("%Y%m%d")
    # The automatic T−12 seeder writes immutable originals on the dedicated
    # branch. Actions checks that branch out into entry-course-ledger/.
    # Production requires an actual checkout of the immutable evidence branch;
    # local snapshots are only eligible for explicit research/test mode.
    durable=root/"entry-course-ledger"/"t12_baselines"/day
    sources=((durable,) if require_durable_t12 else
             (root/"research_snapshots",durable))
    seen=set()
    for file in [p for folder in sources for p in sorted(folder.glob(day+"*.json"))]:
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
            if require_durable_t12:
                # Being present on the dedicated branch is necessary, but
                # not sufficient. Revalidate the exact immutable bytes with
                # the T−12 predictor/source/cutoff schema. The simulated time
                # is used ONLY for retrospective internal consistency:
                # GitHub-server first-add-before-cutoff remains unproven.
                from entry_course_t12_seed import validate_base
                try:
                    archive_path=validate_base(
                        file.read_bytes(),code,
                        now=t12-timedelta(microseconds=1),
                        expected_deadline=deadline)
                except ValueError:
                    continue
                if archive_path!=f"t12_baselines/{day}/{code}.json":
                    continue
            if code in seen:
                continue
            seen.add(code)
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
            output_dir=None, max_minutes=6, min_starts=10,
            waku_enabled=True, waku_fetch=None,
            _selected=None, preview_poll_limit=3,
            skip_historical_fallback=False, require_durable_t12=False):
    if type(preview_poll_limit) is not int or not 1<=preview_poll_limit<=3:
        raise ValueError("invalid_preview_poll_limit")
    now=now or (lambda:datetime.now(JST))
    sampled_now=now()
    target=[_selected] if _selected is not None else candidates(
        root,now=sampled_now,max_minutes=max_minutes,
        require_durable_t12=require_durable_t12)
    if not target:
        return {"status":"no_frozen_baseline_in_late_window","stored":False,
                "baseline_audit":audit_daily_bases(root,now=sampled_now,max_minutes=max_minutes),
                "research_only":True}
    late,code,base=target[0]
    remaining=(late-now()).total_seconds()
    if remaining<45:
        return {"status":"too_close_to_late_cutoff","stored":False,"race_code":code,"research_only":True}
    if waku_enabled and ledger_ops is not None:
        # Five-minute schedule windows can overlap for the same race.
        # A fresh Actions runner must not regenerate a different immutable
        # 120-ticket ranking when the exact original is already archived.
        archived_path=f"waku10/{code[:8]}/{code}.json"
        remote_read,_=ledger_ops
        previous=remote_read(archived_path)
        if previous is not None:
            verified_path=validate_waku10_archive(previous,now=now())
            previous_data=json.loads(previous)
            if (verified_path!=archived_path or
                    previous_data.get("race_code")!=code or
                    previous_data.get("cutoff_at")!=late.isoformat() or
                    previous_data.get("reference_baseline_cutoff_at")!=base.get("cutoff_jst") or
                    previous_data.get("reference_t12_top10")!=base.get("predictions")):
                raise ValueError("existing_waku10_archive_reference_mismatch")
            if remote_read(archived_path)!=previous:
                raise ValueError("existing_waku10_archive_readback_changed")
            from hashlib import sha256
            return {"status":"already_identical_waku10_pilot","stored":True,
                    "path":archived_path,"branch":"entry-course-evidence-ledger",
                    "sha256":sha256(previous).hexdigest(),"race_code":code,
                    "research_only":True,"formal":False,
                    "forecast_record":True,
                    "independent_remote_first_seen_verified":False}
    if card_reader is None:
        from clean_racecard import racecard
        card_reader=racecard
    # Read the real race preview first; do not download 62 historical CSVs
    # when the T-5 preview is still unpublished.
    from entry_course_prospective_capture import _entry_from_preview
    card=None
    preview_error="late_preview_unavailable"
    preview_attempts=0
    for i in range(preview_poll_limit):
        if now()>=late-timedelta(seconds=10):
            break
        preview_attempts+=1
        try:
            # Race identity stays 12-digit in the ledger; the shared CLEAN
            # racecard function accepts 1..12 without a leading zero.
            observed=card_reader(code[:8],code[8:10],str(int(code[10:12])))
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
        if i<preview_poll_limit-1 and now()+timedelta(seconds=35)<late:
            sleep(35)
        else:
            break
    if card is None:
        return {"status":"preview_not_ready","stored":False,
                "race_code":code,"preview_attempts":preview_attempts,
                "reason":preview_error,"historical_requests":0,
                "research_only":True}
    # Preferred independent pilot: one pre-race Waku10 CSV replaces up to 62
    # old daily downloads. Actual course-slot counts gate every boat.
    # This NEVER pretends the Waku10 frame-average ST is course-average ST.
    waku_reason="waku10_not_attempted"
    waku_diagnostics={}
    if waku_enabled and now()<late-timedelta(seconds=10):
        try:
            waku=fetch_waku10(code,cutoff_at=late.isoformat(),
                              fetch=waku_fetch,clock=now)
            waku_frozen_at=now().isoformat()
            candidate=prepare_waku10_pilot(
                base,card,waku,frozen_at=waku_frozen_at,min_course_starts=8)
        except (ValueError,OSError,KeyError,TypeError,TimeoutError,URLError,HTTPError) as exc:
            waku_reason=str(exc) or type(exc).__name__
            if waku_reason=="waku10_pilot_insufficient_course_specific_frame_runs":
                # Diagnose this pre-cutoff source's actual per-course sample
                # counts. No new HTTP or model run, no minimum reduction,
                # and never convert an invalid pilot into a stored forecast.
                try:
                    from entry_waku10_source import extract_waku10_course_evidence
                    entry,_=_entry_from_preview(card,late)
                    observed=extract_waku10_course_evidence(
                        card,waku,entry,frozen_at=waku_frozen_at,min_course_starts=8)
                    waku_diagnostics={
                        "course_sample_counts":{
                            str(row["boat"]):row["matchedCourseCompletedRuns"]
                            for row in observed["rows"]},
                        "insufficient_course_boats":[
                            row["boat"] for row in observed["rows"]
                            if not row["sufficient_sample"]],
                        "minimum_course_starts_required":8,
                        "sample_source":"third_party_waku10_frame_history",
                    }
                except (ValueError,OSError,KeyError,TypeError,TimeoutError):
                    # An unverifiable diagnosis must not hide the real
                    # capture failure or invent course samples.
                    pass
        else:
            directory=Path(root)/"entry_waku10_attempts"
            path=freeze_capture(candidate,directory,clock=now)
            if now()>=late:
                raise ValueError("waku10_pilot_remote_publish_cutoff_exceeded")
            if ledger_ops is None:
                ledger_ops=github_ops(os.environ["GITHUB_REPOSITORY"])
            remote_read,remote_create=ledger_ops
            verdict=publish_waku10(path.read_bytes(),remote_read,remote_create,clock=now)
            verdict["race_code"]=code
            verdict["study"]="Waku10 independent frame-ST-proxy pilot"
            verdict["sample_counts"]=candidate["sample_counts"]
            verdict["preview_attempts"]=preview_attempts
            return verdict
    else:
        waku_reason="waku10_disabled_or_cutoff_too_close"
    if skip_historical_fallback:
        # A multi-race five-minute run must not spend its entire time budget
        # fetching 62 older CSVs for one failed Waku10 arm. The original
        # strict course-history fallback remains available to standalone runs.
        return {"status":"ineligible_waku10_pilot","stored":False,
                "race_code":code,"reason":waku_reason,
                "preview_attempts":preview_attempts,
                "historical_requests":0,"research_only":True,
                **waku_diagnostics}
    cache,fetch_errors=prefetch(code[:8])
    if now()>=late:
        return {"status":"history_fetch_crossed_late_cutoff","stored":False,"race_code":code,
                "source_failures":len(fetch_errors),
                "waku10_pilot_reason":waku_reason,"research_only":True}
    # Source code reports missing archived rows. It does not inject substitutes.
    def local_fetch(url):
        if url not in cache:
            raise OSError("historical_source_not_downloaded")
        return cache[url]
    batch=load_asof_history(code[:8],late.isoformat(),lookback_days=31,
                           fetch=local_fetch,clock=now)
    if not batch["history"]:
        return {"status":"no_verified_historical_pairs","stored":False,
                "race_code":code,"source_failures":len(fetch_errors),
                "waku10_pilot_reason":waku_reason,"research_only":True}
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
                "source_failures":len(fetch_errors),"waku10_pilot_reason":waku_reason,**diagnostics,
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


def expected_t2_without_baseline(now, root, *, schedule_fetch=None,
                                 max_minutes=6):
    """Detect T−2 races with a published pre-race deadline but no T−12 original.

    Read only a pre-race schedule (never results); this deliberately does not
    invent a forecast or relax any T−12 cutoff. If the schedule is missing,
    the caller must report a separate source outage, not a zero-race day.
    """
    from entry_course_t12_seed import _title
    rows,day,digest,source=(schedule_fetch or _title)(now)
    expected=[]
    expected_deadlines={}
    for item in rows:
        if not isinstance(item,dict):
            continue
        code=item.get("レースコード")
        clock=item.get("電話投票締切予定")
        if (type(code) is not str or CODE.fullmatch(code) is None or
                code[:8]!=day or type(clock) is not str or
                re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]",clock) is None):
            continue
        deadline=datetime.strptime(day+clock,"%Y%m%d%H:%M").replace(tzinfo=JST)
        remaining=((deadline-timedelta(minutes=2))-now).total_seconds()
        previous=expected_deadlines.get(code)
        if previous is not None and previous!=deadline:
            raise ValueError("t2_conflicting_live_schedule_deadlines")
        expected_deadlines[code]=deadline
        if 45<=remaining<=max_minutes*60:
            expected.append(code)
    return {"expected_race_codes":sorted(set(expected)),
            "expected_deadline_jst_by_race":{
                code:at.isoformat() for code,at in sorted(expected_deadlines.items())},
            "schedule_sha256":digest,"schedule_source":source,
            "research_only":True}


def attempt_batch(root, *, now=None, max_per_run=3,
                  verify_expected_schedule=False, schedule_fetch=None,
                  preview_retry_rounds=1, preview_retry_interval=35,
                  require_durable_t12=False, **kwargs):
    """Bounded independent race attempts; never mix the race cohorts."""
    if type(max_per_run) is not int or not 1<=max_per_run<=3:
        raise ValueError("invalid_t2_batch_size")
    if (type(preview_retry_rounds) is not int or not 1<=preview_retry_rounds<=7 or
            type(preview_retry_interval) not in (int,float) or
            not 1<=preview_retry_interval<=60):
        raise ValueError("invalid_t2_batch_preview_retry_bounds")
    now=now or (lambda:datetime.now(JST))
    snapshot_time=now()
    pool=candidates(root,now=snapshot_time,
                    require_durable_t12=require_durable_t12)
    if not pool:
        # Preserve the baseline diagnostics, but do not silently count a
        # scheduled T−2 race as a no-op when its T−12 original is absent.
        report=attempt(root,now=now,
                       require_durable_t12=require_durable_t12,**kwargs)
        if not verify_expected_schedule:
            return report
        try:
            expected=expected_t2_without_baseline(snapshot_time,root,
                                    schedule_fetch=schedule_fetch)
        except (ValueError,TypeError,OSError,TimeoutError,HTTPError,URLError) as exc:
            report.update(status="t2_expected_schedule_unavailable",
                          schedule_error_type=type(exc).__name__,
                          stored=False)
            return report
        report["expected_schedule"]=expected
        if expected["expected_race_codes"]:
            report.update(status="t2_missing_expected_t12_baselines",
                          missing_baseline_race_codes=expected["expected_race_codes"],
                          stored=False)
        return report
    # Read independent deadline evidence BEFORE creating any new T−2 archive.
    # Capture races that agree even when a separate race has a disagreement.
    # A transient schedule outage still allows research captures, but the
    # completed job remains an explicit source-audit failure.
    expected_schedule=None
    schedule_error_type=None
    missing_bases=[]
    deadline_conflicts=[]
    if verify_expected_schedule:
        try:
            expected_schedule=expected_t2_without_baseline(
                snapshot_time,root,schedule_fetch=schedule_fetch)
            due=set(expected_schedule["expected_race_codes"])
            known={entry[1] for entry in pool}
            missing_bases=sorted(due-known)
            independent_deadlines=expected_schedule["expected_deadline_jst_by_race"]
            for cutoff,code,base in pool:
                independent=independent_deadlines.get(code)
                if independent is None:
                    continue
                source_deadline=datetime.fromisoformat(independent)
                try:
                    archived_deadline=datetime.fromisoformat(
                        base.get("source_deadline_jst"))
                except (TypeError,ValueError):
                    archived_deadline=None
                if (archived_deadline!=source_deadline or
                        cutoff!=source_deadline-timedelta(minutes=2)):
                    deadline_conflicts.append(code)
            deadline_conflicts=sorted(set(deadline_conflicts))
        except (ValueError,TypeError,OSError,TimeoutError,HTTPError,URLError) as exc:
            schedule_error_type=type(exc).__name__
    blocked=set(deadline_conflicts)
    selected=pool[:max_per_run]
    records=[]
    def capture_one(chosen):
        code=chosen[1]
        try:
            return attempt(root,now=now,_selected=chosen,
                           preview_poll_limit=1,
                           skip_historical_fallback=True,
                           require_durable_t12=require_durable_t12,**kwargs)
        except Exception as exc:
            return {"race_code":code,"status":"collector_error",
                    "stored":False,"error_type":type(exc).__name__,
                    "research_only":True}
    # A race with independently conflicting deadline MUST NOT be
    # published. The unaffected races are still attempted first.
    for chosen in selected:
        if chosen[1] in blocked:
            records.append({"race_code":chosen[1],
                            "status":"independent_deadline_conflict",
                            "stored":False,"research_only":True})
        else:
            records.append(capture_one(chosen))
    # The preview is often published around T−5, which is only 3 minutes
    # before the separate T−2 cutoff. Five-minute cron alone can miss this
    # narrow interval. One running job may therefore recheck missing previews
    # at most six times, while respecting each race's original cutoff.
    retry_attempts=0
    retry_sleeps=0
    sleeper=kwargs.get("sleep",time.sleep)
    for round_no in range(1,preview_retry_rounds):
        pending=[i for i,chosen in enumerate(selected)
                 if records[i].get("status")=="preview_not_ready"
                 and (chosen[0]-now()).total_seconds()>45]
        if not pending:
            break
        safe_wait=min((selected[i][0]-now()).total_seconds()-45
                      for i in pending)
        seconds=min(preview_retry_interval,safe_wait)
        if seconds<1:
            break
        sleeper(seconds)
        retry_sleeps+=1
        for i in pending:
            if (selected[i][0]-now()).total_seconds()<=45:
                continue
            records[i]=capture_one(selected[i])
            retry_attempts+=1
    stored=sum(r.get("stored") is True for r in records)
    newly_stored=sum(r.get("status") in (
        "new_append_only_waku10_pilot","new_append_only_late_capture")
        for r in records)
    reused=sum(r.get("status") in (
        "already_identical_waku10_pilot","already_identical_late_capture")
        for r in records)
    failed=sum(r.get("status")=="collector_error" for r in records)
    skipped=len(records)-stored-failed
    if stored!=newly_stored+reused:
        raise ValueError("t2_unrecognized_stored_verdict")
    # The prospective cohort was independently checked BEFORE the first
    # write; preserve diagnostics after capturing all unaffected races.
    # A successful workflow with actual eligible races but zero verified
    # archives would hide an operational failure. No eligible races remain
    # a valid no-op, and partially stored batches remain visible as partial.
    if failed:
        status="t2_batch_error"
    elif schedule_error_type is not None:
        status="t2_batch_expected_schedule_unavailable"
    elif missing_bases:
        status="t2_batch_missing_expected_t12_baselines"
    elif deadline_conflicts:
        status="t2_batch_t12_deadline_conflict"
    elif stored==0:
        status="t2_batch_no_capture"
    elif skipped:
        status="t2_batch_partial_capture"
    else:
        status="t2_batch_completed"
    return {"status":status,
            "attempted_count":len(records),"stored_count":stored,
            "newly_stored_count":newly_stored,"reused_count":reused,
            "not_stored_count":skipped,
            "errors":failed,"deferred_count":max(0,len(pool)-max_per_run),
            "preview_retry_rounds_configured":preview_retry_rounds,
            "preview_retry_sleeps":retry_sleeps,
            "preview_retry_attempts":retry_attempts,
            "expected_schedule":expected_schedule,
            "missing_baseline_race_codes":missing_bases,
            "baseline_deadline_conflict_race_codes":deadline_conflicts,
            "schedule_error_type":schedule_error_type,
            "results":records,"research_only":True}


def t2_cli_failure(verdict):
    """The scheduled job must not mark partially captured races as success."""
    if not isinstance(verdict,dict):
        raise ValueError("t2_cli_invalid_verdict")
    fatal={"course_evidence_collector_failed","t2_batch_error",
           "t2_batch_no_capture","t2_batch_partial_capture",
           "t2_missing_expected_t12_baselines",
           "t2_expected_schedule_unavailable",
           "t2_batch_missing_expected_t12_baselines",
           "t2_batch_t12_deadline_conflict",
           "t2_batch_expected_schedule_unavailable"}
    return verdict.get("status") in fatal


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=".")
    p.add_argument("--output",default="entry-course-evidence/last-attempt.json")
    args=p.parse_args()
    try:
        remote_read,remote_create=github_ops(os.environ['GITHUB_REPOSITORY'])
        access=verify_write_access(remote_read,remote_create)
        from entry_course_scheduled_write_probe import from_environment
        scheduled_access=from_environment("t2",remote_read,remote_create)
        verdict=attempt_batch(Path(args.root),ledger_ops=(remote_read,remote_create),
                              verify_expected_schedule=True,
                              preview_retry_rounds=7,
                              require_durable_t12=True)
        verdict['ledger_write_access_probe']=access
        verdict['scheduled_actions_write_probe']=scheduled_access
    except Exception as exc:
        verdict={"status":"course_evidence_collector_failed","stored":False,
                 "error_type":type(exc).__name__,"research_only":True}
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(verdict,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    print("COURSE_LATE_EVIDENCE="+json.dumps(verdict,ensure_ascii=False,sort_keys=True))
    if t2_cli_failure(verdict):
        raise SystemExit(2)

if __name__=="__main__":
    main()
