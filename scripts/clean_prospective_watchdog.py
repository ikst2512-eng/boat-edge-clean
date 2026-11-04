"""Best-effort missed-cron recovery for the independent CLEAN prospective collector.

Uses the existing four-mode watchdog's successful-run / active-job / cooldown
policy, but targets only clean-prospective.yml. A dispatch is not evidence of a
new immutable prediction or of a successful independent first-add audit.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scripts.four_mode_watchdog_policy import should_dispatch

WORKFLOW = "clean-prospective.yml"
OUTPUT = Path("four-mode-evidence/clean-prospective-watchdog-decision.json")
WINDOW_MINUTES = 14
# Existing independent scheduled workflows; no extra cron or publication path.
TRUSTED_SCHEDULES = frozenset({
    "Four-mode prospective capture (research only)",
    "CLEAN independent daily schedule capture",
    "Preview capture (schedule)",
    # Independently observed completed main/schedule runs on 2026-11-04:
    # odds probe 22:07 JST and entry T−12 research archive 21:15 JST.
    "CLEAN live official trifecta odds probe",
    "Entry research T-minus-12 baseline archival",
})


def trusted_schedule_completion(payload, repository):
    """Accept only a successful scheduled main run of a known same-repo workflow."""
    if not isinstance(payload, dict) or not repository:
        return False
    upstream = payload.get("workflow_run")
    if not isinstance(upstream, dict):
        return False
    head_repo = upstream.get("head_repository")
    return (
        upstream.get("name") in TRUSTED_SCHEDULES
        and upstream.get("event") == "schedule"
        and upstream.get("head_branch") == "main"
        and upstream.get("status") == "completed"
        and upstream.get("conclusion") == "success"
        and isinstance(head_repo, dict)
        and head_repo.get("full_name") == repository
    )


def last_night_slot_view(runs, now):
    """At 22:29-22:32 JST, do not mistake 22:19's success for 22:28.

    Earlier active jobs still block duplicate publication. A completed
    earlier manual retry is not evidence that the distinct 22:28 slot ran.
    No new writer, cron, or relaxation of the collector's T-12 gate.
    """
    local = now.astimezone(timezone(timedelta(hours=9)))
    if local.hour != 22 or not 29 <= local.minute <= 32:
        return runs
    slot_start = local.replace(minute=28, second=0, microsecond=0).astimezone(timezone.utc)
    visible = []
    for run in runs:
        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        if created.tzinfo is None:
            raise ValueError("run_time_timezone_required")
        if created >= slot_start or run["status"] != "completed":
            visible.append(run)
    return visible


def decide(runs, now, event_name, ref, *, trigger=None, repository=None):
    """Only trusted main branch schedules can wake recovery from another workflow."""
    if ref != "refs/heads/main" or event_name not in (
            "schedule", "push", "workflow_dispatch", "workflow_run"):
        return False
    if event_name == "workflow_run" and not trusted_schedule_completion(
            trigger, repository):
        return False
    publication = [run for run in runs
                   if run.get("event") in ("schedule", "workflow_dispatch")
                   and run.get("head_branch") == "main"]
    publication = last_night_slot_view(publication, now)
    return should_dispatch(
        publication, now, event_name,
        recent_minutes=WINDOW_MINUTES, cooldown_minutes=WINDOW_MINUTES,
        end_hour_jst=22)


def fetch_runs(repo, token):
    root = f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW}"
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    runs = []
    # Query event types separately. Busy PR traffic must not evict cron runs.
    for event in ("schedule", "workflow_dispatch"):
        req = urllib.request.Request(
            root + "/runs?event=" + event + "&per_page=30", headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            runs.extend(json.load(response)["workflow_runs"])
    return runs, root, headers


def dispatch(root, headers):
    body = json.dumps({"ref": "main"}).encode("utf-8")
    req = urllib.request.Request(
        root + "/dispatches", data=body, headers={
            **headers, "Content-Type": "application/json"
        }, method="POST")
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 204:
            raise RuntimeError("clean_prospective_dispatch_not_accepted")


def main():
    now = datetime.now(timezone.utc)
    event = os.environ["GITHUB_EVENT_NAME"]
    ref = os.environ["GITHUB_REF"]
    repository = os.environ.get("GH_REPOSITORY")
    # workflow_run is privileged: never trust a PR/manual/foreign-repo parent.
    # Refuse missing, malformed or incomplete provenance before API access.
    trigger = None
    if event == "workflow_run":
        trigger_path = os.environ.get("GITHUB_EVENT_PATH")
        if trigger_path:
            trigger = json.loads(Path(trigger_path).read_text(encoding="utf-8"))
    report = {
        "schema": "CLEAN_PROSPECTIVE_WATCHDOG_DECISION_V1",
        "github_run_id": os.environ["GITHUB_RUN_ID"],
        "checked_at_utc": now.isoformat(),
        "event": event,
        "trigger_ref": ref,
        "target": WORKFLOW,
        "formal": False,
        "remote_first_seen_verified": False,
        "new_forecast_saved_proven": False,
        "action": "no_dispatch",
        "upstream_workflow": (
            trigger.get("workflow_run", {}).get("name")
            if isinstance(trigger, dict) and isinstance(trigger.get("workflow_run"), dict)
            else None
        ),
        "upstream_run_id": (
            trigger.get("workflow_run", {}).get("id")
            if isinstance(trigger, dict) and isinstance(trigger.get("workflow_run"), dict)
            else None
        ),
    }
    try:
        # No token/network needed outside main's pre-cutoff collection hours.
        if not decide([], now, event, ref,
                      trigger=trigger, repository=repository):
            report["reason"] = "out_of_hours_or_untrusted_trigger"
            return
        repo = os.environ["GH_REPOSITORY"]
        token = os.environ["GH_TOKEN"]
        runs, root, headers = fetch_runs(repo, token)
        main_runs = [r for r in runs if r.get("head_branch") == "main"]
        report["observed_main_runs"] = len(main_runs)
        report["newest_main_run_utc"] = max(
            (r["created_at"] for r in main_runs), default=None)
        if decide(runs, now, event, ref,
                  trigger=trigger, repository=repository):
            # At most one best-effort fallback per 14m window. The collector
            # itself retains all original T-12, 90s, append-only and audit gates.
            dispatch(root, headers)
            report["action"] = "fallback_dispatch_accepted_not_capture_proof"
        else:
            report["reason"] = "recent_success_active_or_cooldown"
    except Exception as exc:
        report["action"] = "watchdog_check_or_dispatch_failed"
        report["error_type"] = type(exc).__name__
        raise
    finally:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(
            json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
        print("CLEAN_PROSPECTIVE_WATCHDOG=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
