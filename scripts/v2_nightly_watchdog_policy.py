"""Conservative nightly V2 fallback dispatch policy (not a proof of scoring)."""
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
GOOD = {"schedule", "workflow_dispatch"}


def should_dispatch_nightly(runs, now, trigger):
    if now.tzinfo is None:
        raise ValueError("naive_watchdog_time")
    if trigger not in ("schedule", "push", "workflow_dispatch"):
        return False
    local = now.astimezone(JST)
    # Nightly research nominally starts 21:30 JST. Allow one same-night
    # recovery attempt, never before the normal run has had 15 minutes.
    if not (local.hour == 21 and local.minute >= 45 or local.hour in (22, 23)):
        return False
    start = local.replace(hour=21, minute=20, second=0, microsecond=0)
    for item in runs:
        if item.get("event") not in GOOD or item.get("head_branch") != "main":
            continue
        raw = item.get("created_at")
        try:
            created = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if created.tzinfo is None:
                continue
        except (TypeError, AttributeError, ValueError):
            continue
        if not start <= created.astimezone(JST) <= local:
            continue
        # Any prior manual/automatic dispatch is already the one fallback
        # attempt for the day, even if it later fails. An active/successful
        # scheduled run must not be displaced by the watchdog.
        if item["event"] == "workflow_dispatch":
            return False
        if item.get("status") != "completed" or item.get("conclusion") == "success":
            return False
    return True
