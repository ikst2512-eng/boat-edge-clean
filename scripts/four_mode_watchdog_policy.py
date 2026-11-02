"""Pure watchdog dispatch policy; a success is not forecast publication proof."""
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

def should_dispatch(runs, now, event):
    if now.tzinfo is None:
        raise ValueError("timezone_required")
    if event == "pull_request" or not 7 <= now.astimezone(JST).hour <= 20:
        return False
    def age(run):
        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        if created.tzinfo is None:
            raise ValueError("run_time_timezone_required")
        return (now-created).total_seconds()
    recent = [r for r in runs if 0 <= age(r) < 27*60]
    active_or_success = any(r["status"] != "completed" or r["conclusion"] == "success" for r in recent)
    fallback_cooldown = any(r["event"] == "workflow_dispatch" and 0 <= age(r) < 20*60 for r in runs)
    return not active_or_success and not fallback_cooldown
