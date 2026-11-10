"""Read-only evidence of scheduled captures, fallback dispatches, and watchdog runs."""
import argparse
import json
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

CAPTURE = "four-mode-prospective-capture.yml"
WATCHDOG = "four-mode-capture-watchdog.yml"
CLEAN = "clean-prospective.yml"


def api_json(url, token):
    req = Request(url, headers={"Authorization": "Bearer " + token,
                                 "Accept": "application/vnd.github+json",
                                 "X-GitHub-Api-Version": "2022-11-28",
                                 "User-Agent": "boat-edge-clean-watchdog-evidence"})
    with urlopen(req, timeout=20) as res:
        return json.load(res)


def check_runs(payload, event):
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise ValueError("invalid workflow run response")
    items = payload["workflow_runs"]
    total = payload.get("total_count")
    if (len(items) > 100 or (total is not None and (
            type(total) is not int or total < len(items)))):
        raise ValueError("invalid workflow run history coverage")
    rows = []
    seen = set()
    for r in items:
        if (not isinstance(r, dict) or r.get("event") != event
                or type(r.get("id")) is not int or r["id"] <= 0
                or r["id"] in seen):
            raise ValueError("unexpected or duplicate workflow run")
        seen.add(r["id"])
        try:
            moment = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, ValueError, TypeError) as exc:
            raise ValueError("invalid run time") from exc
        if moment.utcoffset() is None:
            raise ValueError("timezone required")
        # GitHub cannot certify a run concluded successfully before it
        # completed. Treat contradictory status/conclusion as corrupt
        # evidence, not a positive capture.
        if r.get("status") != "completed" and r.get("conclusion") is not None:
            raise ValueError("noncompleted_run_has_conclusion")
        # A feature-branch workflow_dispatch can finish "success" while its
        # privileged capture job is skipped (main-only). Preserve the branch
        # and owning repository so it cannot masquerade as main publication.
        head_repo = r.get("head_repository")
        head_repo_name = (head_repo.get("full_name")
                          if isinstance(head_repo, dict) else None)
        rows.append({"id": r["id"], "event": event, "created_at": moment.isoformat(),
                     "status": r.get("status"), "conclusion": r.get("conclusion"),
                     "html_url": r.get("html_url"),
                     "head_branch": r.get("head_branch"),
                     "head_repository_full_name": head_repo_name})
    return rows



JST = timezone(timedelta(hours=9))


def audit_current_day_schedule_observations(workflow, runs, source_coverage, as_of):
    """Triage observed starts, never individual Cron delivery or rescued saves.

    Slot definitions mirror the existing main YAML. This is a read-only view
    over the inventory's existing API page; it does not add a workflow.
    """
    if workflow not in (CLEAN, WATCHDOG):
        raise ValueError("unsupported schedule workflow")
    if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
        raise ValueError("timezone-aware observation time required")
    if not isinstance(source_coverage, dict) or not isinstance(runs, list):
        raise ValueError("invalid schedule evidence")
    local = as_of.astimezone(JST)
    day = local.date()
    if workflow == CLEAN:
        first = datetime.combine(day, time(7, 4), tzinfo=JST)
        slots = [first + timedelta(minutes=15 * i) for i in range(60)]
        slots += [datetime.combine(day, time(22, minute), tzinfo=JST)
                  for minute in (4, 19, 28)]
    else:
        first = datetime.combine(day, time(7, 13), tzinfo=JST)
        slots = [first + timedelta(minutes=15 * i) for i in range(60)]
        slots += [datetime.combine(day, time(hour, minute), tzinfo=JST)
                  for hour, minute in ((21, 50), (22, 13), (22, 20),
                                       (22, 29), (22, 44))]
    slots.sort()
    grace = timedelta(minutes=5)
    due = sum(at + grace <= local for at in slots)
    end = slots[-1] + grace
    seen_ids = set()
    in_window = []
    off_window = []
    for run in runs:
        if (not isinstance(run, dict) or run.get("workflow") != workflow
                or run.get("event") != "schedule"
                or type(run.get("id")) is not int or run["id"] <= 0
                or run["id"] in seen_ids):
            raise ValueError("invalid schedule observation")
        seen_ids.add(run["id"])
        try:
            created = datetime.fromisoformat(run["created_at"]).astimezone(JST)
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise ValueError("invalid schedule observation timestamp") from exc
        if created.date() != day or created > local:
            continue
        (in_window if first <= created <= end else off_window).append(run)
    earliest = source_coverage.get("earliest_created_at")
    try:
        boundary = (datetime.fromisoformat(earliest).astimezone(JST) < first
                    if isinstance(earliest, str) else False)
    except ValueError:
        boundary = False
    total = source_coverage.get("total_count_reported")
    returned = source_coverage.get("returned")
    # A truncated first page is safe only if sorted descending and extends
    # before today's first nominal time. A partial same-day page is unknown.
    complete = (
        type(total) is int and type(returned) is int
        and (total == returned
             or (source_coverage.get("descending_by_created_at") is True
                 and boundary)))
    observed = len(in_window)
    percent = round(100 * observed / due, 2) if due else None
    if due == 0:
        state = "no_nominal_slots_due"
    elif not complete:
        state = "api_coverage_unverified"
    elif observed == 0:
        state = "no_in_window_schedule_observation"
    elif due >= 12 and observed * 4 < due:
        state = "severely_below_nominal_observation"
    elif observed < due:
        state = "below_nominal_observation"
    else:
        state = "nominal_count_met_not_slot_proof"
    return {
        "day_jst": day.strftime("%Y%m%d"),
        "as_of_jst": local.isoformat(),
        "nominal_slots_per_day": len(slots),
        "nominal_slots_due_with_five_minute_grace": due,
        "in_window_observed_count": observed,
        "in_window_run_ids": sorted(run["id"] for run in in_window),
        "in_window_completed_success_run_ids": sorted(
            run["id"] for run in in_window
            if run.get("status") == "completed"
            and run.get("conclusion") == "success"),
        "same_day_off_window_run_ids": sorted(run["id"] for run in off_window),
        "observed_pct_of_nominal_due": percent,
        "api_page_covers_current_day": complete,
        "schedule_observation_state": state,
        "per_slot_schedule_delivery_verified": False,
        "new_first_add_proven": False,
        "note": "Observed workflow run starts, not proven individual Cron deliveries, accepted rescues or new publications.",
    }


def inventory(repo, token, fetch=api_json, now=None):
    if not repo or repo.count("/") != 1 or not token:
        raise ValueError("invalid arguments")
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise ValueError("timezone required")
    all_rows = []
    coverage = {}
    global_seen_ids = set()
    for workflow, events in ((CAPTURE, ("schedule", "workflow_dispatch")),
                             (WATCHDOG, ("schedule", "push", "workflow_run")),
                             (CLEAN, ("schedule", "workflow_dispatch"))):
        for event in events:
            url = (f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}"
                   f"/runs?event={event}&per_page=100")
            payload = fetch(url, token)
            rows = check_runs(payload, event)
            total = payload.get("total_count")
            # GitHub's event-filtered API may include successful manual runs
            # on a feature branch. For those, the capture job is intentionally
            # skipped. Unknown branch/repository provenance also fails closed.
            # Never count any of them toward main's liveness or watchdog.
            main_rows = [
                r for r in rows
                if r["head_branch"] == "main"
                and r["head_repository_full_name"] == repo]
            excluded = [
                r["id"] for r in rows
                if r["head_branch"] != "main"
                or r["head_repository_full_name"] != repo]
            coverage[workflow + ":" + event] = {
                "returned": len(rows), "main_verified_returned": len(main_rows),
                "excluded_nonmain_or_unverified_run_ids": excluded,
                "first_page_only": True,
                "total_count_reported": total,
                "earliest_created_at": min((r["created_at"] for r in rows), default=None),
                "descending_by_created_at": all(
                    rows[i]["created_at"] >= rows[i + 1]["created_at"]
                    for i in range(len(rows) - 1)),
                "may_be_truncated": (
                    len(rows) == 100 or
                    (type(total) is int and total > len(rows)))}
            # Even excluded rows must be checked for duplicate API run IDs.
            for r in rows:
                if r["id"] in global_seen_ids:
                    raise ValueError("same_run_id_in_multiple_event_listings")
                global_seen_ids.add(r["id"])
                r["workflow"] = workflow
            all_rows.extend(main_rows)
    all_rows.sort(key=lambda r: r["created_at"], reverse=True)
    captures = [r for r in all_rows if r["workflow"] == CAPTURE]
    watchdogs = [r for r in all_rows if r["workflow"] == WATCHDOG]
    clean_schedules = [r for r in all_rows if r["workflow"] == CLEAN and r["event"] == "schedule"]
    clean_dispatches = [r for r in all_rows if r["workflow"] == CLEAN and r["event"] == "workflow_dispatch"]
    # Keep legacy direct-trigger watchdog artifact consumers stable. The
    # high-volume workflow_run hook is a distinct source and a completed
    # skipped job is *not* a successful recovery. Its API page is bounded.
    direct_watchdogs = [r for r in watchdogs
                        if r["event"] in ("schedule", "push")]
    webhook_watchdogs = [r for r in watchdogs if r["event"] == "workflow_run"]
    latest_capture = captures[0] if captures else None
    gap = None
    if latest_capture is not None:
        stamp = datetime.fromisoformat(latest_capture["created_at"])
        gap = max(0, round((now - stamp).total_seconds() / 60, 1))
    def count(rows, event):
        selected = [r for r in rows if r["event"] == event]
        return {"returned": len(selected),
                "success": sum(
                    r["status"] == "completed" and r["conclusion"] == "success"
                    for r in selected),
                "failed": sum(
                    r["status"] == "completed" and r["conclusion"] == "failure"
                    for r in selected),
                "pending": sum(r["status"] != "completed" for r in selected),
                "completed_unknown_outcome": sum(
                    r["status"] == "completed" and r["conclusion"] is None
                    for r in selected),
                "completed_other_non_success": sum(
                    r["status"] == "completed"
                    and r["conclusion"] not in ("success", "failure", None)
                    for r in selected),
                "skipped": sum(
                    r["status"] == "completed" and r["conclusion"] == "skipped"
                    for r in selected)}
    return {"schema": "FOUR_MODE_WATCHDOG_DISPATCH_COVERAGE_V1",
            "as_of_utc": now.isoformat(),
            "capture_schedule": count(captures, "schedule"),
            "capture_workflow_dispatch": count(captures, "workflow_dispatch"),
            "watchdog_schedule": count(watchdogs, "schedule"),
            "watchdog_push": count(watchdogs, "push"),
            "watchdog_workflow_run": count(watchdogs, "workflow_run"),
            "clean_schedule": count(clean_schedules, "schedule"),
            "current_day_clean_schedule_observation": audit_current_day_schedule_observations(
                CLEAN, clean_schedules, coverage[CLEAN + ":schedule"], now),
            "current_day_watchdog_schedule_observation": audit_current_day_schedule_observations(
                WATCHDOG, [r for r in watchdogs if r["event"] == "schedule"],
                coverage[WATCHDOG + ":schedule"], now),
            "clean_workflow_dispatch": count(clean_dispatches, "workflow_dispatch"),
            "latest_capture": latest_capture, "minutes_since_latest_capture": gap,
            # Preserve latest direct-trigger watchdog semantics for existing
            # consumers, and expose webhook observations independently.
            "latest_watchdog": direct_watchdogs[0] if direct_watchdogs else None,
            "latest_watchdog_workflow_run": (
                webhook_watchdogs[0] if webhook_watchdogs else None),
            "source_coverage": coverage,
            "dispatch_accepted_proven": False,
            "forecast_saved_proven": False,
            "note": ("Run listings are bounded first-page metadata only. "
                     "Only main-branch runs from the expected source repo "
                     "count toward capture and watchdog liveness; excluded "
                     "run IDs remain visible in source_coverage. The watchdog "
                     "workflow_run counts cover only its first GitHub API "
                     "page, and CLEAN dispatch counts are independently "
                     "bounded; neither proves 72-hour event totals. Skipped is "
                     "a subset of completed_other_non_success, not a dispatch. "
                     "Pending, "
                     "completed with no conclusion, and other non-success "
                     "outcomes are separate. A successful job does not "
                     "prove dispatch cause, main publication, or "
                     "individual Cron slot delivery."),
            "recent_capture_runs": captures,
            # Do not displace actual direct watchdog decision artifacts with
            # high-volume webhook skipped runs. Keep the raw webhook scope
            # separate and explicitly bounded.
            "recent_watchdog_runs": direct_watchdogs[:40],
            "recent_watchdog_workflow_run": webhook_watchdogs[:40],
            "recent_successful_watchdog_workflow_run": [
                r for r in webhook_watchdogs
                if r["status"] == "completed" and r["conclusion"] == "success"][:12],
            "recent_clean_schedule_runs": clean_schedules[:100],
            "recent_clean_dispatch_runs": clean_dispatches[:100]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    data = inventory(args.repo, os.environ.get("GITHUB_TOKEN"))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("FOUR_MODE_WATCHDOG_DISPATCH_COVERAGE=" + json.dumps({
        "as_of_utc": data["as_of_utc"],
        "capture_schedule": data["capture_schedule"],
        "capture_workflow_dispatch": data["capture_workflow_dispatch"],
        "watchdog_schedule": data["watchdog_schedule"],
        "watchdog_push": data["watchdog_push"],
        "watchdog_workflow_run": data["watchdog_workflow_run"],
        "clean_schedule": data["clean_schedule"],
        "current_day_clean_schedule_observation": data["current_day_clean_schedule_observation"],
        "current_day_watchdog_schedule_observation": data["current_day_watchdog_schedule_observation"],
        "clean_workflow_dispatch": data["clean_workflow_dispatch"],
        "latest_watchdog_workflow_run": data["latest_watchdog_workflow_run"],
        "latest_capture": data["latest_capture"],
        "recent_capture_runs": data["recent_capture_runs"][:10],
        "minutes_since_latest_capture": data["minutes_since_latest_capture"]}, sort_keys=True))


if __name__ == "__main__":
    main()
