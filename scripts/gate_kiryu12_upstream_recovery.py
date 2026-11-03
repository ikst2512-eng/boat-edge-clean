"""Exact-window research gate for Kiryu12, November 3 only."""
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
WINDOW_START = datetime(2026, 11, 3, 19, 30, tzinfo=JST)
DEADLINE = datetime(2026, 11, 3, 20, 19, tzinfo=JST)
BUFFER = timedelta(seconds=90)


def check_window(now, upstream_started):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now needs timezone")
    if not isinstance(upstream_started, str):
        raise ValueError("upstream timestamp required")
    try:
        started = datetime.fromisoformat(upstream_started.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid upstream timestamp") from exc
    if started.utcoffset() is None:
        raise ValueError("upstream needs timezone")
    now = now.astimezone(JST)
    started = started.astimezone(JST)
    if not (WINDOW_START <= now < DEADLINE - BUFFER):
        raise ValueError("outside safe T12 research window")
    if not (WINDOW_START <= started <= now):
        raise ValueError("upstream run stale or future dated")
    return True
