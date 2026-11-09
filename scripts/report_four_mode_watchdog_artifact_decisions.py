"""Read-only verify watchdog decisions from uploaded Actions artifacts.

Do not infer publication from a dispatch; temporal matching is not causation.
"""
import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.report_four_mode_schedule_publications import safe_json


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("invalid timestamp")
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.utcoffset() is None:
        raise ValueError("timestamp requires zone")
    return date.astimezone(timezone.utc)


def inspect_clean_webhook_recovery(history, downloader, limit=12):
    """Check a bounded sample of *successful webhook jobs*, not all webhooks.

    The existing watchdog writes a separate CLEAN decision artifact after a
    trusted upstream schedule completion. A 204 dispatch acknowledgment does
    not return the downstream run ID, so matching by time is correlation only.
    """
    candidates = history.get("recent_successful_watchdog_workflow_run", [])
    clean_runs = history.get("recent_clean_dispatch_runs", [])
    if (not isinstance(candidates, list) or not isinstance(clean_runs, list)
            or type(limit) is not int or not 1 <= limit <= 12):
        raise ValueError("invalid clean webhook audit history")
    from scripts.clean_prospective_watchdog import TRUSTED_SCHEDULES

    following = []
    seen_clean = set()
    for item in clean_runs:
        if (not isinstance(item, dict) or item.get("workflow") != "clean-prospective.yml"
                or item.get("event") != "workflow_dispatch"
                or type(item.get("id")) is not int or item["id"] <= 0
                or item["id"] in seen_clean):
            raise ValueError("invalid clean dispatch metadata")
        seen_clean.add(item["id"])
        following.append((timestamp(item.get("created_at")), item))

    rows = []
    checked_ids = set()
    for run in candidates[:limit]:
        if (not isinstance(run, dict)
                or run.get("workflow") != "four-mode-capture-watchdog.yml"
                or run.get("event") != "workflow_run"
                or run.get("head_branch") != "main"
                or not isinstance(run.get("head_repository_full_name"), str)
                or not run["head_repository_full_name"]
                or run.get("status") != "completed"
                or run.get("conclusion") != "success"
                or type(run.get("id")) is not int or run["id"] <= 0
                or run["id"] in checked_ids):
            raise ValueError("invalid successful webhook evidence")
        run_id = run["id"]
        checked_ids.add(run_id)
        started = timestamp(run.get("created_at"))
        row = {"run_id": run_id, "trigger_event": "workflow_run",
               "evidence_status": "missing_or_invalid_clean_decision",
               "decision": None, "claimed_upstream_run_id": None,
               "claimed_upstream_workflow": None,
               "upstream_parent_verified": False,
               "temporally_following_clean_dispatch_ids": [],
               "following_clean_dispatch_completed_success_ids": [],
               "causal_link_proven": False,
               "new_first_add_proven": False}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            try:
                downloader(run_id, root)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                row["evidence_status"] = "artifact_download_" + type(exc).__name__
                rows.append(row)
                continue
            nested = safe_json(root, "four-mode-evidence/clean-prospective-watchdog-decision.json")
            flat = safe_json(root, "clean-prospective-watchdog-decision.json")
            # Conflicting paths are ambiguous. Refuse both, do not pick one.
            record = nested if flat is None else flat if nested is None else None
        if record is not None:
            try:
                checked_at = timestamp(record.get("checked_at_utc"))
                valid = (
                    record.get("schema") == "CLEAN_PROSPECTIVE_WATCHDOG_DECISION_V1"
                    and record.get("github_run_id") == str(run_id)
                    and record.get("event") == "workflow_run"
                    and record.get("trigger_ref") == "refs/heads/main"
                    and record.get("target") == "clean-prospective.yml"
                    and record.get("formal") is False
                    and record.get("remote_first_seen_verified") is False
                    and record.get("new_forecast_saved_proven") is False
                    and record.get("action") in (
                        "no_dispatch", "fallback_dispatch_accepted_not_capture_proof",
                        "watchdog_check_or_dispatch_failed")
                    and type(record.get("upstream_run_id")) is int
                    and record["upstream_run_id"] > 0
                    and record.get("upstream_workflow") in TRUSTED_SCHEDULES
                    and started <= checked_at <= started + timedelta(hours=2)
                )
            except (TypeError, ValueError, OverflowError):
                valid = False
            if valid:
                row["evidence_status"] = "clean_decision_artifact_verified"
                row["decision"] = record["action"]
                row["claimed_upstream_run_id"] = record["upstream_run_id"]
                row["claimed_upstream_workflow"] = record["upstream_workflow"]
                if record["action"] == "fallback_dispatch_accepted_not_capture_proof":
                    correlated = [
                        item for at, item in following
                        if checked_at <= at <= checked_at + timedelta(minutes=3)]
                    row["temporally_following_clean_dispatch_ids"] = sorted(
                        item["id"] for item in correlated)
                    row["following_clean_dispatch_completed_success_ids"] = sorted(
                        item["id"] for item in correlated
                        if item.get("status") == "completed"
                        and item.get("conclusion") == "success")
        rows.append(row)
    verified = [r for r in rows
                if r["evidence_status"] == "clean_decision_artifact_verified"]
    return {
        "clean_webhook_runs_checked": len(rows),
        "clean_webhook_decisions_verified": len(verified),
        "clean_webhook_fallback_accepted_verified": sum(
            r["decision"] == "fallback_dispatch_accepted_not_capture_proof"
            for r in verified),
        "clean_webhook_error_decisions": sum(
            r["decision"] == "watchdog_check_or_dispatch_failed"
            for r in verified),
        "clean_webhook_unknown_evidence": len(rows) - len(verified),
        "clean_webhook_first_page_only": True,
        "clean_webhook_causal_link_proven": False,
        "clean_webhook_new_first_add_proven": False,
        "clean_webhook_runs": rows,
    }


def inspect(history, downloader, limit=40):
    if (not isinstance(history, dict)
            or not isinstance(history.get("recent_watchdog_runs"), list)
            or not isinstance(history.get("recent_capture_runs"), list)
            or type(limit) is not int or not 1 <= limit <= 40):
        raise ValueError("invalid watchdog evidence history")
    dispatches = []
    for capture in history["recent_capture_runs"]:
        if not isinstance(capture, dict):
            raise ValueError("invalid capture")
        if capture.get("event") == "workflow_dispatch":
            if type(capture.get("id")) is not int or capture["id"] <= 0:
                raise ValueError("invalid dispatch ID")
            dispatches.append((timestamp(capture.get("created_at")), capture))
    rows = []
    ids = set()
    for run in history["recent_watchdog_runs"][:limit]:
        if not isinstance(run, dict) or run.get("workflow") != "four-mode-capture-watchdog.yml":
            raise ValueError("invalid watchdog workflow")
        run_id, event = run.get("id"), run.get("event")
        if type(run_id) is not int or run_id <= 0 or run_id in ids or event not in ("push", "schedule"):
            raise ValueError("invalid watchdog identity/event")
        ids.add(run_id)
        started = timestamp(run.get("created_at"))
        row = {"run_id": run_id, "trigger_event": event, "decision": None,
               "evidence_status": "missing_or_invalid_artifact",
               "temporally_following_dispatch_ids": [],
               "causal_link_proven": False}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            try:
                downloader(run_id, root)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                row["evidence_status"] = "artifact_download_" + type(exc).__name__
                rows.append(row)
                continue
            nested = safe_json(root, "four-mode-evidence/watchdog-decision.json")
            flat = safe_json(root, "watchdog-decision.json")
            # GitHub's artifact upload may flatten an individual-file upload.
            # Conflicting copies must not be accepted as valid proof.
            record = nested if flat is None else flat if nested is None else None
        if record is not None:
            try:
                checked_at = timestamp(record.get("checked_at_utc"))
                valid = (
                    record.get("schema") == "FOUR_MODE_WATCHDOG_DECISION_V1"
                    and record.get("github_run_id") == str(run_id)
                    and record.get("github_event") == event
                    and record.get("dry_run") is False
                    and record.get("action") in ("no_dispatch", "fallback_dispatch_accepted")
                    and checked_at >= started
                    and checked_at <= started + timedelta(hours=2)
                )
            except (ValueError, TypeError, OverflowError):
                valid = False
            if valid:
                row["evidence_status"] = "decision_artifact_verified"
                row["decision"] = record["action"]
                if record["action"] == "fallback_dispatch_accepted":
                    row["temporally_following_dispatch_ids"] = sorted(
                        c["id"] for when, c in dispatches
                        if checked_at <= when <= checked_at + timedelta(minutes=3))
        rows.append(row)
    verified = [r for r in rows if r["evidence_status"] == "decision_artifact_verified"]
    clean = inspect_clean_webhook_recovery(history, downloader)
    return {"schema": "FOUR_MODE_WATCHDOG_ARTIFACT_DECISIONS_V1",
            **clean,
            "runs_checked": len(rows),
            "artifact_decisions_verified": len(verified),
            "fallback_accepted_verified": sum(r["decision"] == "fallback_dispatch_accepted" for r in verified),
            "no_dispatch_verified": sum(r["decision"] == "no_dispatch" for r in verified),
            "unknown_evidence": len(rows) - len(verified),
            "causal_link_proven": False,
            "remote_publication_proven": False,
            "note": ("A post-acceptance dispatch in a time window is correlation, "
                     "not verified causation. Successful webhook samples are "
                     "bounded to the visible first page; CLEAN job success "
                     "does not prove any new first-add."),
            "runs": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not os.environ.get("GH_TOKEN"):
        raise SystemExit("GH_TOKEN required")
    history = json.loads(Path(args.history).read_text(encoding="utf-8"))
    def download(run_id, dest):
        subprocess.run(["gh", "run", "download", str(run_id), "--repo", args.repo,
                        "--name", f"four-mode-watchdog-decision-{run_id}",
                        "--dir", str(dest)], check=True, capture_output=True, timeout=40)
    result = inspect(history, download)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("FOUR_MODE_WATCHDOG_ARTIFACT_DECISIONS=" + json.dumps({
        "runs_checked": result["runs_checked"],
        "artifact_decisions_verified": result["artifact_decisions_verified"],
        "fallback_accepted_verified": result["fallback_accepted_verified"],
        "no_dispatch_verified": result["no_dispatch_verified"],
        "unknown_evidence": result["unknown_evidence"],
        "clean_webhook_runs_checked": result["clean_webhook_runs_checked"],
        "clean_webhook_decisions_verified": result["clean_webhook_decisions_verified"],
        "clean_webhook_fallback_accepted_verified": result["clean_webhook_fallback_accepted_verified"],
        "clean_webhook_unknown_evidence": result["clean_webhook_unknown_evidence"],
        "clean_webhook_rows": result["clean_webhook_runs"],
        "accepted_rows": [r for r in result["runs"] if r["decision"] == "fallback_dispatch_accepted"]
    }, sort_keys=True))


if __name__ == "__main__":
    main()
