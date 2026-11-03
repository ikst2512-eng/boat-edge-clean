"""Read-only candidate readiness diagnostics for the T−2 entry-course collector.

No outcome, forecast generation, network calls or source timestamp changes.
Do not mistake a scheduled job with zero candidates for an API outage.
"""
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
import json
import re

CODE=re.compile(r"20[0-9]{10}\Z")


def _date(value):
    try:
        d=datetime.fromisoformat(value)
        return d if d.utcoffset() is not None else None
    except (TypeError,ValueError):
        return None


def audit_daily_bases(root, *, now, max_minutes=6):
    if not isinstance(now,datetime) or now.utcoffset() is None:
        raise ValueError("audit_clock_not_timezone_aware")
    if type(max_minutes) not in (int,float) or not 1<=max_minutes<=30:
        raise ValueError("invalid_candidate_audit_window")
    root=Path(root)
    counts=Counter()
    sample_ids={key:[] for key in ("eligible","outside_window","past_t2","invalid")}
    day=now.strftime("%Y%m%d")
    counts["snapshot_files_today"]=0
    sources=(root/"research_snapshots",root/"entry-course-ledger"/"t12_baselines"/day)
    seen=set()
    for file in [p for folder in sources for p in sorted(folder.glob(day+"*.json"))]:
        if file.stem in seen:
            counts["duplicate_baseline_code"]+=1
            continue
        seen.add(file.stem)
        counts["snapshot_files_today"]+=1
        code=file.stem
        if not CODE.fullmatch(code) or file.is_symlink() or file.stat().st_size>30000:
            counts["invalid_snapshot"]+=1
            sample_ids["invalid"].append(code[:12])
            continue
        try:
            raw=json.loads(file.read_text(encoding="utf-8"))
        except (OSError,ValueError,UnicodeError):
            counts["invalid_snapshot"]+=1
            sample_ids["invalid"].append(code)
            continue
        if not isinstance(raw,dict) or raw.get("race_code")!=code:
            counts["invalid_snapshot"]+=1
            sample_ids["invalid"].append(code)
            continue
        generated=_date(raw.get("generated_at"))
        t12=_date(raw.get("cutoff_jst"))
        deadline=_date(raw.get("source_deadline_jst"))
        if (raw.get("status")!="research" or raw.get("validated") is not False
                or not generated or not t12 or not deadline
                or not generated<=t12<deadline):
            counts["invalid_snapshot"]+=1
            sample_ids["invalid"].append(code)
            continue
        counts["valid_frozen_research"]+=1
        t2=deadline-timedelta(minutes=2)
        remaining=(t2-now).total_seconds()
        if remaining<=0:
            counts["past_t2"]+=1
            sample_ids["past_t2"].append(code)
        elif remaining<45:
            counts["too_close_to_t2"]+=1
        elif remaining>max_minutes*60:
            counts["outside_window"]+=1
            sample_ids["outside_window"].append(code)
        else:
            counts["eligible"]+=1
            sample_ids["eligible"].append(code)
    if counts["snapshot_files_today"]==0:
        status="missing_current_day_research_snapshots"
    elif counts["valid_frozen_research"]==0:
        status="invalid_current_day_research_snapshots"
    elif counts["eligible"]>0:
        status="eligible_candidates_present"
    else:
        status="no_candidate_in_t2_window"
    return {"schema":"entry-course-daily-baseline-audit-v1","status":status,
            "day":day,"observed_at":now.isoformat(),
            "counts":{k:counts[k] for k in (
                "snapshot_files_today","valid_frozen_research","invalid_snapshot",
                "past_t2","outside_window","too_close_to_t2","eligible",
                "duplicate_baseline_code")},
            "race_code_samples":{k:v[:10] for k,v in sample_ids.items()},
            "research_only":True,"forecast_record":False}
