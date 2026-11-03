"""Audit actual workflow_dispatch capture artifacts using the existing bounded inspector.

This bridges the gap in scheduled-only publication evidence. No new
collector/scheduler, publication changes, or remote-first-seen claims.
"""
import argparse
import json
import os
import subprocess
from pathlib import Path

from scripts.report_four_mode_schedule_publications import report

CAPTURE_WORKFLOW = "four-mode-prospective-capture.yml"


# Retain the early morning fallback run when later no-op dispatches accumulate.
# Download inspection stays bounded and uses the shared four-worker inspector.
def dispatch_history(capture_inventory, *, limit=12):
    if (not isinstance(capture_inventory, dict)
            or not isinstance(capture_inventory.get("recent_capture_runs"), list)
            or type(limit) is not int or not 1 <= limit <= 20):
        raise ValueError("invalid capture inventory")
    runs = []
    seen = set()
    matched = 0
    for run in capture_inventory["recent_capture_runs"]:
        if not isinstance(run, dict):
            raise ValueError("invalid capture run")
        if run.get("workflow") != CAPTURE_WORKFLOW:
            raise ValueError("unexpected capture workflow")
        if run.get("event") != "workflow_dispatch":
            continue
        run_id = run.get("id")
        stamp = run.get("created_at")
        if (type(run_id) is not int or run_id <= 0 or not isinstance(stamp, str)
                or not stamp or run_id in seen):
            raise ValueError("invalid or duplicate dispatch run")
        seen.add(run_id)
        matched += 1
        if len(runs) < limit:
            runs.append({"id": run_id, "created_at": stamp,
                         "capture_conclusion": run.get("conclusion"),
                         # Workflow listing cannot prove which step failed.
                         "failed_steps": []})
    return {"schema": "FOUR_MODE_DISPATCH_CAPTURE_HISTORY_V1",
            "matching_dispatch_runs_available": matched, "runs": runs}


def inspect_dispatches(capture_inventory, downloader, limit=12):
    history = dispatch_history(capture_inventory, limit=limit)
    # Empty discovery is unknown, not a claim of success.
    if not history["runs"]:
        return {"schema": "FOUR_MODE_DISPATCH_PUBLICATION_EVIDENCE_V1",
                "dispatch_runs_checked": 0, "artifacts_present": 0,
                "runs_claiming_push": 0, "claimed_added_forecasts_sum": None,
                "research_stage_coverage": {
                    field: {"success": 0, "failure": 0, "skipped": 0,
                            "cancelled": 0, "unknown": 0, "checked": 0}
                    for field in ("third_rate_shadow", "hole_shadow")},
                "third_rate_shadow_failure_runs": [], "hole_shadow_failure_runs": [],
                "research_roster_status_counts": {
                    "matched": 0, "mismatch": 0, "unknown": 0, "not_applicable": 0},
                "research_roster_mismatch_run_ids": [],
                "remote_main_verified": False, "runs": [],
                "note": "No dispatch runs in bounded listing; no publication conclusion."}
    result = report(history, downloader, limit=limit)
    result["schema"] = "FOUR_MODE_DISPATCH_PUBLICATION_EVIDENCE_V1"
    result["dispatch_runs_checked"] = result.pop("scheduled_runs_checked")
    result["history_runs_available"] = history["matching_dispatch_runs_available"]
    result["history_runs_omitted"] = max(
        0, history["matching_dispatch_runs_available"] - result["dispatch_runs_checked"])
    for row in result["runs"]:
        row["trigger_event"] = "workflow_dispatch"
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--history", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    if not os.environ.get("GH_TOKEN"):
        raise SystemExit("GH_TOKEN required")
    inventory = json.loads(Path(args.history).read_text(encoding="utf-8"))

    def download(run_id, destination):
        subprocess.run(["gh", "run", "download", str(run_id), "--repo", args.repo,
                        "--name", "four-mode-capture-" + str(run_id),
                        "--dir", str(destination)], check=True, capture_output=True, timeout=50)

    result = inspect_dispatches(inventory, download)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("FOUR_MODE_DISPATCH_PUBLICATIONS=" + json.dumps({
        "dispatch_runs_checked": result["dispatch_runs_checked"],
        "history_runs_omitted": result.get("history_runs_omitted", 0),
        "artifacts_present": result["artifacts_present"],
        "runs_claiming_push": result["runs_claiming_push"],
        "research_stage_coverage": result["research_stage_coverage"],
        "research_roster_status_counts": result["research_roster_status_counts"],
        "research_roster_mismatch_run_ids": result["research_roster_mismatch_run_ids"],
        "third_rate_shadow_failure_runs": result["third_rate_shadow_failure_runs"],
        "hole_shadow_failure_runs": result["hole_shadow_failure_runs"],
        "claimed_added_forecasts_sum": result["claimed_added_forecasts_sum"],
        "per_run": [{"run_id": row["run_id"],
                      "capture_conclusion": row["capture_conclusion"],
                      "publication_outcome": row["publication_outcome"],
                      "third_rate_shadow_outcome": row["third_rate_shadow_outcome"],
                      "hole_shadow_outcome": row["hole_shadow_outcome"],
                      "research_roster_evidence": row["research_roster_evidence"],
                      "source_link_status": row["source_link_status"],
                      "staged_valid": row["staged_valid"],
                      "source_title_rows": row["source_title_rows"],
                      "source_card_rows": row["source_card_rows"],
                      "generated_today": row["generated_today"],
                      "artifact_present": row["artifact_present"]}
                     for row in result["runs"]]
    }, sort_keys=True))


if __name__ == "__main__":
    main()
