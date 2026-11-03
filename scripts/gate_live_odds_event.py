"""Fail-closed gate for alternate odds probe triggers.

The existing CLEAN prospective workflow sometimes receives real schedule events
when the odds cron has no observed schedule trigger. Only such completed
scheduled upstream runs are eligible for fallback operational sampling.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from probe_live_odds_health import event_provenance

UPSTREAM = "CLEAN prospective pre-cutoff capture"


def fallback_slot_eligible(trigger, *, now=None):
    """Allow only the upstream 12:45/14:45/16:45 JST catch-up windows.

    The upstream is scheduled each 15 minutes; counting every completion would
    flood operational evidence and inflate the success denominator. Fail closed
    on missing, stale, future, or out-of-window timestamps.
    """
    try:
        source = datetime.fromisoformat(trigger["upstream_created_at"].replace("Z", "+00:00"))
        if source.tzinfo is None:
            return False
        source = source.astimezone(timezone.utc)
    except (KeyError, AttributeError, TypeError, ValueError):
        return False
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not 0 <= (now - source).total_seconds() <= 60 * 60:
        return False
    jst = timezone(timedelta(hours=9))
    source_local = source.astimezone(jst)
    for hour in (12, 14, 16):
        cutoff = source_local.replace(hour=hour, minute=25, second=0, microsecond=0)
        elapsed_minutes = (source_local - cutoff).total_seconds() / 60
        if 15 <= elapsed_minutes < 30:
            return True
    return False


def eligible(event, trigger, *, now=None):
    if event in ("schedule", "workflow_dispatch", "pull_request"):
        return True  # PRs are separately excluded by the reliability aggregator.
    if event != "workflow_run" or not isinstance(trigger, dict):
        return False
    return (trigger.get("event") == "workflow_run"
            and trigger.get("upstream_event") == "schedule"
            and trigger.get("upstream_workflow") == UPSTREAM
            and trigger.get("upstream_branch") == "main"
            and type(trigger.get("upstream_run_id")) is int
            and trigger["upstream_run_id"] > 0
            and fallback_slot_eligible(trigger, now=now))


def main():
    trigger = event_provenance()
    event = trigger["event"]
    allowed = eligible(event, trigger)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fp:
            fp.write("collect=" + str(allowed).lower() + "\n")
    if not allowed:
        now = datetime.now(timezone.utc)
        data = {
            "checked_at_jst": now.astimezone(timezone(timedelta(hours=9))).isoformat(),
            "source_status": "fallback_ineligible",
            "trigger": trigger,
            "samples": [],
            "reason": "upstream_not_verified_or_outside_bounded_fallback_window",
        }
        Path("live_odds_metrics.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("LIVE_ODDS_TRIGGER_GATE " + json.dumps({
        "collect": allowed, "source": event,
        "upstream_event": trigger.get("upstream_event"),
        "upstream_run_id": trigger.get("upstream_run_id")}), flush=True)


if __name__ == "__main__":
    main()
