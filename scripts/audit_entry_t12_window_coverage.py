"""Read-only, race-scoped T-12 Action creation-window diagnostics.

This does not dispatch jobs, collect sources, write immutable archives, or
certify that a GitHub Action executed its collector step before a cutoff.
The caller must explicitly attest that both event-type inventories are complete.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import json
import re

JST = timezone(timedelta(hours=9))
CODE = re.compile(r"20[0-9]{10}$")
DAY = re.compile(r"20[0-9]{6}$")
WORKFLOW_ID = 405663641
EVENTS = frozenset(("schedule", "workflow_dispatch"))
# Exactly matches entry_course_t12_seed.near_t12: (2, 14) minutes
# before the T-12 cutoff (deadline - 12 minutes).
EARLY_MINUTES = 14
LATE_MINUTES = 2


def _time(value, field):
    if type(value) is not str:
        raise ValueError("window_audit_invalid_" + field)
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("window_audit_invalid_" + field) from exc
    if stamp.utcoffset() is None:
        raise ValueError("window_audit_naive_" + field)
    return stamp.astimezone(JST)


def audit_snapshot(payload):
    """Audit *creation times*, not collector execution or saved-source receipt."""
    if type(payload) is not dict:
        raise ValueError("window_audit_invalid_input")
    day = payload.get("date_jst")
    if type(day) is not str or not DAY.fullmatch(day):
        raise ValueError("window_audit_invalid_day")
    try:
        datetime.strptime(day, "%Y%m%d")
    except ValueError as exc:
        raise ValueError("window_audit_invalid_day") from exc
    observed = _time(payload.get("observed_at_jst"), "observation")
    complete = payload.get("run_inventory_complete")
    if type(complete) is not bool:
        raise ValueError("window_audit_inventory_flag_required")
    event_types = payload.get("event_types_checked")
    if event_types != ["schedule", "workflow_dispatch"]:
        raise ValueError("window_audit_both_event_types_required")
    deadlines = payload.get("races")
    runs = payload.get("runs")
    ledger_codes = payload.get("ledger_present_race_codes")
    if type(deadlines) is not list or type(runs) is not list or type(ledger_codes) is not list:
        raise ValueError("window_audit_invalid_lists")
    if type(payload.get("ledger_inventory_complete")) is not bool:
        raise ValueError("window_audit_ledger_flag_required")
    seen_codes = set()
    for code in ledger_codes:
        if type(code) is not str or not CODE.fullmatch(code) or code[:8] != day or code in seen_codes:
            raise ValueError("window_audit_invalid_ledger_codes")
        seen_codes.add(code)
    ledger = set(ledger_codes)
    seen_runs = set()
    eligible_runs = []
    for run in runs:
        if type(run) is not dict:
            raise ValueError("window_audit_invalid_run")
        run_id = run.get("id")
        if type(run_id) is not int or run_id <= 0 or run_id in seen_runs:
            raise ValueError("window_audit_invalid_run_id")
        seen_runs.add(run_id)
        at = _time(run.get("created_at"), "run_created")
        if at > observed:
            raise ValueError("window_audit_run_after_observation")
        if (run.get("workflow_id") == WORKFLOW_ID and
                run.get("event") in EVENTS and run.get("head_branch") == "main"):
            eligible_runs.append((at, run))
    seen_races = set()
    rows = []
    for race in deadlines:
        if type(race) is not dict:
            raise ValueError("window_audit_invalid_race")
        code = race.get("race_code")
        if type(code) is not str or not CODE.fullmatch(code) or code[:8] != day or code in seen_races:
            raise ValueError("window_audit_invalid_race_code")
        seen_races.add(code)
        deadline = _time(race.get("source_deadline_jst"), "deadline")
        if deadline.strftime("%Y%m%d") != day:
            raise ValueError("window_audit_mismatched_deadline_day")
        cutoff = deadline - timedelta(minutes=12)
        start = cutoff - timedelta(minutes=EARLY_MINUTES)
        end = cutoff - timedelta(minutes=LATE_MINUTES)
        observed_runs = [run for at, run in eligible_runs if start <= at <= end]
        if observed < end:
            state = "window_not_finished"
        elif not complete:
            state = "incomplete_action_inventory_unverified"
        elif observed_runs:
            state = "on_time_action_created_execution_unverified"
        else:
            state = "no_on_time_action_creation_observed"
        rows.append({
            "race_code": code,
            "source_deadline_jst": deadline.isoformat(),
            "t12_cutoff_jst": cutoff.isoformat(),
            "selection_window_start_jst": start.isoformat(),
            "selection_window_end_jst": end.isoformat(),
            "created_on_time_action_ids": sorted(run["id"] for run in observed_runs),
            "action_creation_state": state,
            "ledger_path_present": code in ledger if payload["ledger_inventory_complete"] else None,
            "source_available_before_cutoff_verified": False,
            "collector_step_executed_in_window_verified": False,
            "first_git_add_before_cutoff_verified": False,
            "formal_t12_certified": False,
        })
    counts = {state: sum(r["action_creation_state"] == state for r in rows)
              for state in ("window_not_finished", "incomplete_action_inventory_unverified",
                            "on_time_action_created_execution_unverified",
                            "no_on_time_action_creation_observed")}
    return {
        "schema": "entry-t12-per-race-action-window-v1",
        "date_jst": day,
        "observed_at_jst": observed.isoformat(),
        "run_inventory_complete": complete,
        "ledger_inventory_complete": payload["ledger_inventory_complete"],
        "count": len(rows),
        "state_counts": counts,
        "races": sorted(rows, key=lambda r: r["race_code"]),
        "research_only": True,
        "formal": False,
        "independent_first_seen_verified": False,
        "collector_execution_proven": False,
        "no_dispatch_or_ledger_write": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Read-only JSON evidence snapshot")
    parser.add_argument("--output", required=True, help="Where to write the diagnostic JSON")
    args = parser.parse_args()
    report = audit_snapshot(json.loads(Path(args.input).read_text(encoding="utf-8")))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + chr(10),
                      encoding="utf-8")
    print(json.dumps({"state_counts": report["state_counts"], "formal": False}, sort_keys=True))


if __name__ == "__main__":
    main()
