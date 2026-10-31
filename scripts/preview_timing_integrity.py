"""Strictly classify source row timestamps relative to each race cutoff.

Read-only diagnostic. Source timestamps are claims from source CSV, whereas
HTTP receipt is directly observed. A row cannot be certified pre-cutoff if
the actual HTTP receipt is at/after cutoff or its timestamp is missing.
"""
from datetime import datetime, timedelta
from research_model import JST

def parse_jst(value):
    if not isinstance(value, str) or not value.strip(): return None
    raw=value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y%m%d%H%M%S"):
        try: return datetime.strptime(raw,fmt).replace(tzinfo=JST)
        except ValueError: pass
    try:
        parsed=datetime.fromisoformat(raw)
        return parsed.replace(tzinfo=JST) if parsed.tzinfo is None else parsed.astimezone(JST)
    except ValueError: return None

def classify(row, received_at, margin_minutes=12):
    deadline=parse_jst(row.get("締切時刻"))
    if deadline is None:
        code=row.get("レースコード","")
        hhmm=row.get("締切時刻","")
        if isinstance(code,str) and len(code)==12 and code.isascii() and code.isdigit() and isinstance(hhmm,str):
            try: deadline=datetime.strptime(code[:8]+hhmm,"%Y%m%d%H:%M").replace(tzinfo=JST)
            except ValueError: pass
    source_time=parse_jst(row.get("取得日時"))
    if deadline is None or source_time is None: return "unknown_time"
    if deadline.tzinfo is None or received_at.tzinfo is None: return "unknown_time"
    # Race previews must describe the same JST calendar day as their deadline.
    # Reject stale previous-day source timestamps even when they precede T-12.
    if source_time.astimezone(JST).date()!=deadline.date() or received_at.astimezone(JST).date()!=deadline.date():
        return "unknown_time"
    cutoff=deadline-timedelta(minutes=margin_minutes)
    if source_time>received_at: return "unknown_time"
    if source_time>=cutoff or received_at>=cutoff: return "too_late"
    return "pre_cutoff_observed"

if __name__=="__main__":
    raise SystemExit("Use through preview diagnostic")
