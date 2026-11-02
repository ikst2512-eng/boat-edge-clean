"""Pure fail-closed T−12 observation decision helpers."""
from datetime import datetime, timedelta

def _jst(ts):
    dt = datetime.fromisoformat(ts)
    if dt.utcoffset() != timedelta(hours=9):
        raise ValueError("Expected explicit JST timestamp")
    return dt

def decision(before_received_jst, deadline_jst, now_jst):
    before, deadline, now = map(_jst, (before_received_jst, deadline_jst, now_jst))
    cutoff = deadline - timedelta(minutes=12)
    if before > cutoff:
        status = "beforeinfo_after_t12"
    elif now + timedelta(seconds=20) >= cutoff:
        status = "insufficient_time_to_fetch_odds"
    else:
        status = "fetch_odds"
    return {"status": status, "cutoff_jst": cutoff.isoformat(),
            "both_complete_before_t12": False, "forecast_usable": False}

def can_retry(now_jst, deadline_jst, attempt, attempts):
    return attempt < attempts and _jst(now_jst) + timedelta(seconds=55) < _jst(deadline_jst) - timedelta(minutes=12)

def receipt_at_or_before_t12(received_at_jst, deadline_jst):
    """Arrival time, not request start, decides whether evidence is timely."""
    return _jst(received_at_jst) <= _jst(deadline_jst) - timedelta(minutes=12)
