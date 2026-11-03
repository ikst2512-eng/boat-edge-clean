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


def eligible(event, trigger):
    if event in ("schedule", "workflow_dispatch", "pull_request"):
        return True  # PRs are separately excluded by the reliability aggregator.
    if event != "workflow_run" or not isinstance(trigger, dict):
        return False
    return (trigger.get("event") == "workflow_run"
            and trigger.get("upstream_event") == "schedule"
            and trigger.get("upstream_workflow") == UPSTREAM
            and trigger.get("upstream_branch") == "main"
            and type(trigger.get("upstream_run_id")) is int
            and trigger["upstream_run_id"] > 0)


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
            "reason": "upstream_event_not_verified_as_main_schedule",
        }
        Path("live_odds_metrics.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("LIVE_ODDS_TRIGGER_GATE " + json.dumps({
        "collect": allowed, "source": event,
        "upstream_event": trigger.get("upstream_event"),
        "upstream_run_id": trigger.get("upstream_run_id")}), flush=True)


if __name__ == "__main__":
    main()
