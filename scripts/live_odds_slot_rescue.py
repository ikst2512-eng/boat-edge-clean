"""Best-effort odds recovery when GitHub misses the 12:25/14:25/16:25 JST cron.

This is a separate late recovery attempt. It is NEVER direct-slot evidence,
never edits forecasts, and never calls the prediction or betting API.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from scripts.clean_prospective_watchdog import trusted_schedule_completion

JST = timezone(timedelta(hours=9))
WORKFLOW = "live-official-odds-probe.yml"
OUTPUT = Path("four-mode-evidence/odds-slot-rescue-decision.json")
SLOTS = (12, 14, 16)
EARLIEST_MINUTES = 15
LATEST_MINUTES = 45


def slot_for(now):
    """Only evaluate the bounded recovery window after each direct 25m slot."""
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("timezone_aware_now_required")
    local = now.astimezone(JST)
    for hour in SLOTS:
        target = local.replace(hour=hour, minute=25, second=0, microsecond=0)
        elapsed = (local - target).total_seconds() / 60
        if EARLIEST_MINUTES <= elapsed < LATEST_MINUTES:
            return target
    return None


def permitted_wakeup(event, ref, trigger, repository):
    if ref != "refs/heads/main":
        return False
    if event in ("schedule", "push"):
        return True
    if event == "workflow_run":
        return trusted_schedule_completion(trigger, repository)
    return False


def checked_history(payload, event, slot, now):
    """Return events within the window, or fail closed on incomplete history."""
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise ValueError("invalid_odds_run_history")
    runs = payload["workflow_runs"]
    parsed = []
    for run in runs:
        if not isinstance(run, dict) or run.get("event") != event:
            raise ValueError("unexpected_odds_history_event")
        if type(run.get("id")) is not int or run["id"] <= 0:
            raise ValueError("invalid_odds_history_run_id")
        raw = run.get("created_at")
        if not isinstance(raw, str):
            raise ValueError("invalid_odds_history_created_at")
        try:
            created = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid_odds_history_timestamp") from exc
        if created.tzinfo is None or created > now + timedelta(minutes=2):
            raise ValueError("invalid_odds_history_chronology")
        # A different, explicitly identified branch is not main's operational
        # evidence. Missing branch identity is ambiguous and fails closed.
        if not isinstance(run.get("head_branch"), str):
            raise ValueError("odds_history_branch_unverified")
        if run["head_branch"] != "main":
            continue
        parsed.append((created.astimezone(JST), run))
    if len(runs) == 100 and (not parsed or min(t for t, _ in parsed) >= slot):
        raise ValueError("odds_history_page_truncated_in_slot")
    return [r for t, r in parsed if slot <= t <= now.astimezone(JST)]


def decision(schedule_payload, dispatch_payload, now, event, ref, trigger, repository):
    slot = slot_for(now)
    if slot is None or not permitted_wakeup(event, ref, trigger, repository):
        return {"action": "no_dispatch", "reason": "out_of_window_or_untrusted"}
    direct = checked_history(schedule_payload, "schedule", slot, now)
    dispatched = checked_history(dispatch_payload, "workflow_dispatch", slot, now)
    record = {
        "slot_jst": slot.isoformat(),
        "direct_runs_after_slot": len(direct),
        "dispatch_runs_after_slot": len(dispatched),
    }
    if dispatched:
        return {**record, "action": "no_dispatch", "reason": "prior_slot_dispatch_exists"}
    if any(r.get("status") != "completed" or r.get("conclusion") == "success"
           for r in direct):
        return {**record, "action": "no_dispatch",
                "reason": "direct_schedule_success_or_active"}
    return {**record, "action": "eligible_for_recovery",
            "reason": "direct_schedule_missing_or_failed"}


def fetch_history(root, headers, event):
    uri = root + "/runs?event=" + event + "&per_page=100"
    request = Request(uri, headers=headers)
    with urlopen(request, timeout=16) as response:
        return json.load(response)


def dispatch(root, headers):
    req = Request(root + "/dispatches", data=b'{"ref":"main"}',
                  headers={**headers, "Content-Type": "application/json"},
                  method="POST")
    with urlopen(req, timeout=16) as response:
        if response.status != 204:
            raise RuntimeError("odds_slot_rescue_dispatch_rejected")


def main():
    now = datetime.now(timezone.utc)
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    ref = os.environ.get("GITHUB_REF", "")
    repo = os.environ.get("GH_REPOSITORY", "")
    report = {
        "schema": "CLEAN_ODDS_MISSED_SLOT_RESCUE_V1",
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "checked_at_jst": now.astimezone(JST).isoformat(),
        "direct_cron_observed": False,
        "recovery_odds_verified": False,
        "on_time_slot_verified": False,
        "formal": False,
        "action": "no_dispatch",
    }
    try:
        trigger = None
        if event == "workflow_run":
            source = os.environ.get("GITHUB_EVENT_PATH")
            if source:
                trigger = json.loads(Path(source).read_text(encoding="utf-8"))
        if not permitted_wakeup(event, ref, trigger, repo) or slot_for(now) is None:
            report["reason"] = "out_of_window_or_untrusted"
            return
        if not repo or "/" not in repo or not os.environ.get("GH_TOKEN"):
            raise ValueError("odds_rescue_repository_or_token_missing")
        root = "https://api.github.com/repos/" + repo + "/actions/workflows/" + WORKFLOW
        headers = {
            "Authorization": "Bearer " + os.environ["GH_TOKEN"],
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "BOAT-EDGE-CLEAN-ODDS-SLOT-RESCUE/1.0",
        }
        # Query events separately; noisy PR activity must never displace
        # actual scheduled/dispatch evidence from a mixed first page.
        scheduled = fetch_history(root, headers, "schedule")
        previous = fetch_history(root, headers, "workflow_dispatch")
        report.update(decision(scheduled, previous, now, event, ref, trigger, repo))
        if report["action"] == "eligible_for_recovery":
            dispatch(root, headers)
            report["action"] = "fallback_dispatch_accepted_not_sample_proof"
    except Exception as exc:
        report["action"] = "rescue_check_or_dispatch_failed"
        report["error_type"] = type(exc).__name__
        raise
    finally:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
        print("CLEAN_ODDS_SLOT_RESCUE=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
