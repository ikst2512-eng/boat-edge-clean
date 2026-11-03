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
            record = safe_json(root, "four-mode-evidence/watchdog-decision.json")
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
    return {"schema": "FOUR_MODE_WATCHDOG_ARTIFACT_DECISIONS_V1",
            "runs_checked": len(rows),
            "artifact_decisions_verified": len(verified),
            "fallback_accepted_verified": sum(r["decision"] == "fallback_dispatch_accepted" for r in verified),
            "no_dispatch_verified": sum(r["decision"] == "no_dispatch" for r in verified),
            "unknown_evidence": len(rows) - len(verified),
            "causal_link_proven": False,
            "remote_publication_proven": False,
            "note": "A post-acceptance dispatch in a time window is correlation, not verified causation.",
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
        "accepted_rows": [r for r in result["runs"] if r["decision"] == "fallback_dispatch_accepted"]
    }, sort_keys=True))


if __name__ == "__main__":
    main()
