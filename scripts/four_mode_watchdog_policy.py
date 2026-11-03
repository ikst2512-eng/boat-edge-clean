"""Pure watchdog dispatch policy; a success is not forecast publication proof."""
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

def should_dispatch(runs, now, event, *, recent_minutes=27, cooldown_minutes=20):
    if recent_minutes <= 0 or cooldown_minutes <= 0:
        raise ValueError("invalid_dispatch_window")
    if now.tzinfo is None:
        raise ValueError("timezone_required")
    if event == "pull_request" or not 7 <= now.astimezone(JST).hour <= 20:
        return False
    def age(run):
        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        if created.tzinfo is None:
            raise ValueError("run_time_timezone_required")
        return (now-created).total_seconds()
    # A manual dispatch on a feature branch cannot satisfy or block main's
    # scheduled capture slot. GitHub provides head_branch for actual runs.
    main_runs = [r for r in runs if r.get("head_branch", "main") == "main"]
    recent = [r for r in main_runs if 0 <= age(r) < recent_minutes*60]
    # Even an older queued/running job must block duplicate publication.
    # Bound the lookback to avoid stale infrastructure records blocking forever.
    active_or_success = any(
        (r["status"] != "completed" and 0 <= age(r) < 120*60) or
        (r["conclusion"] == "success" and r in recent)
        for r in main_runs
    )
    fallback_cooldown = any(r["event"] == "workflow_dispatch" and 0 <= age(r) < cooldown_minutes*60 for r in main_runs)
    return not active_or_success and not fallback_cooldown
