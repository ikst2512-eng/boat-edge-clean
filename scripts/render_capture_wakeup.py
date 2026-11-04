"""Independent Render cron wakeup for existing safeguarded GitHub captures.

This opt-in operator entrypoint is intentionally inert until an external cron
service and restricted GITHUB_DISPATCH_TOKEN are configured. It NEVER writes
forecast files and a successful dispatch NEVER proves publication.

Expected external wakeup: every five minutes, UTC hours 22-13 inclusive.
Only narrow windows after actual JST primary slots can dispatch.
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
REPOSITORY = "ikst2512-eng/boat-edge-clean"
WORKFLOWS = {
    "clean": "clean-prospective.yml",
    "four_mode": "four-mode-prospective-capture.yml",
}
SCHEMA = "EXTERNAL_CAPTURE_WAKEUP_DECISION_V1"


def planned_slots(kind, now):
    local = now.astimezone(JST)
    day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if kind == "four_mode":
        return [day.replace(hour=h, minute=m)
                for h in range(7, 21) for m in (7, 22, 37, 52)]
    if kind == "clean":
        return ([day.replace(hour=h, minute=m)
                 for h in range(7, 22) for m in (4, 19, 34, 49)]
                + [day.replace(hour=22, minute=m) for m in (4, 19, 28)])
    raise ValueError("unknown_capture_workflow")


def eligible_slot(kind, now):
    """At most one external five-minute tick is eligible for each real slot."""
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("timezone_aware_now_required")
    local = now.astimezone(JST)
    slots = planned_slots(kind, now)
    earlier = [slot for slot in slots if slot <= local]
    if not earlier:
        return None
    slot = earlier[-1]
    age_minutes = (local - slot).total_seconds() / 60
    if kind == "clean" and slot.hour == 22 and slot.minute == 28:
        return slot if 1 <= age_minutes < 4 else None
    minimum, maximum = (2, 5) if kind == "four_mode" else (5, 8)
    return slot if minimum <= age_minutes < maximum else None


def _read_run_list(base, event, token, request):
    uri = base + "/runs?event=" + event + "&per_page=100"
    req = urllib.request.Request(uri, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "BOAT-EDGE-CLEAN-EXTERNAL-WAKEUP/1.0",
    })
    with request(req, timeout=20) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise ValueError("github_history_missing_or_malformed")
    rows = payload["workflow_runs"]
    if len(rows) > 100:
        raise ValueError("github_history_oversized")
    return rows


def _validated_events(rows, kind, slot, now):
    parsed = []
    for row in rows:
        if not isinstance(row, dict) or row.get("event") != kind:
            raise ValueError("github_history_event_mismatch")
        if type(row.get("id")) is not int or row["id"] <= 0:
            raise ValueError("github_history_id_unverified")
        if not isinstance(row.get("head_branch"), str):
            raise ValueError("github_history_branch_unverified")
        raw_time = row.get("created_at")
        if not isinstance(raw_time, str):
            raise ValueError("github_history_time_unverified")
        created = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        if created.tzinfo is None or created > now + timedelta(minutes=2):
            raise ValueError("github_history_chronology_unverified")
        if not isinstance(row.get("status"), str):
            raise ValueError("github_history_status_unverified")
        if row["head_branch"] == "main":
            parsed.append((created.astimezone(JST), row))
    # A full first page still inside the operational lookback is ambiguous:
    # never interpret its missing tail as evidence of no other slot run.
    if len(rows) == 100 and (not parsed or min(t for t, _ in parsed) >= slot - timedelta(hours=2)):
        raise ValueError("github_history_pagination_incomplete")
    return parsed


def decide(kind, scheduled, manual, slot, now):
    """Block duplicates and unknowns; only an absent/failed direct run qualifies."""
    if slot is None:
        return {"action": "no_dispatch", "reason": "outside_jst_recovery_window"}
    s = _validated_events(scheduled, "schedule", slot, now)
    m = _validated_events(manual, "workflow_dispatch", slot, now)
    after_direct = [r for timestamp, r in s if slot <= timestamp <= now.astimezone(JST)]
    near_manual = [r for timestamp, r in m
                   if slot - timedelta(minutes=2) <= timestamp <= now.astimezone(JST)]
    older_active = [r for timestamp, r in [*s, *m]
                    if now.astimezone(JST) - timedelta(hours=2) <= timestamp < slot
                    and r.get("status") != "completed"]
    base = {"slot_jst": slot.isoformat(),
            "direct_runs_after_slot": len(after_direct),
            "manual_runs_near_slot": len(near_manual)}
    if near_manual or older_active:
        return {**base, "action": "no_dispatch", "reason": "previous_dispatch_or_active_job"}
    if any(r["status"] != "completed" or
           r.get("conclusion") not in ("failure", "cancelled", "timed_out")
           for r in after_direct):
        return {**base, "action": "no_dispatch", "reason": "direct_success_active_or_unknown"}
    return {**base, "action": "eligible_for_dispatch",
            "reason": "direct_schedule_missing_or_explicitly_failed"}


def _dispatch(base, token, request):
    body = b'{"ref":"main"}'
    req = urllib.request.Request(base + "/dispatches", data=body, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "BOAT-EDGE-CLEAN-EXTERNAL-WAKEUP/1.0",
    }, method="POST")
    with request(req, timeout=20) as response:
        if response.status != 204:
            raise RuntimeError("github_external_dispatch_not_accepted")


def run(*, token, now=None, request=urllib.request.urlopen):
    now = now or datetime.now(timezone.utc)
    result = {"schema": SCHEMA, "checked_at_jst": now.astimezone(JST).isoformat(),
              "on_time_cron_proven": False, "new_forecast_saved_proven": False,
              "formal": False, "workflows": {}}
    eligible = {kind: eligible_slot(kind, now) for kind in WORKFLOWS}
    if not any(eligible.values()):
        result["action"] = "outside_recovery_windows_no_network"
        for kind in WORKFLOWS:
            result["workflows"][kind] = {"action": "no_dispatch",
                                         "reason": "outside_jst_recovery_window"}
        return result
    if not isinstance(token, str) or not token:
        raise ValueError("GITHUB_DISPATCH_TOKEN_required")
    deferred = []
    # Validate *both* GitHub histories before posting to either workflow.
    # A GitHub API failure for the second collector must not leave the first
    # collector accidentally dispatched with no complete decision receipt.
    for kind, filename in WORKFLOWS.items():
        slot = eligible[kind]
        if slot is None:
            result["workflows"][kind] = {"action": "no_dispatch",
                                         "reason": "outside_jst_recovery_window"}
            continue
        root = f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/{filename}"
        schedule = _read_run_list(root, "schedule", token, request)
        manual = _read_run_list(root, "workflow_dispatch", token, request)
        verdict = decide(kind, schedule, manual, slot, now)
        result["workflows"][kind] = verdict
        if verdict["action"] == "eligible_for_dispatch":
            deferred.append((kind, root))
    for kind, root in deferred:
        _dispatch(root, token, request)
        result["workflows"][kind]["action"] = "dispatch_accepted_not_forecast_proof"
    result["action"] = "checked_not_publication_proof"
    return result


def main():
    try:
        report = run(token=os.environ.get("GITHUB_DISPATCH_TOKEN"))
        print("EXTERNAL_CAPTURE_WAKEUP=" + json.dumps(report, sort_keys=True), flush=True)
    except Exception as exc:
        print("EXTERNAL_CAPTURE_WAKEUP_ERROR=" + json.dumps({
            "schema": SCHEMA, "error_type": type(exc).__name__,
            "new_forecast_saved_proven": False, "on_time_cron_proven": False}), flush=True)
        raise


if __name__ == "__main__":
    main()
