"""Read-only scheduled V2 collection evidence. A claimed push is not remote proof."""
import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))


def safe_json(root, relative):
    path = root / relative
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def count(data, key):
    value = data.get(key) if isinstance(data, dict) else None
    return value if type(value) is int and value >= 0 else None


def inspect(run, root):
    """Keep unknown separate from zero; never reclassify local push claims as remote proof."""
    result = {"run_id": run["id"], "created_at": run.get("created_at"),
              "capture_conclusion": run.get("capture_conclusion"),
              "failed_steps": run.get("failed_steps", []),
              "artifact_present": False, "source_title_rows": None,
              "source_card_rows": None, "generated_today": None,
              "newly_generated": None, "staged_valid": None,
              "publication_outcome": None, "claimed_added_forecasts": None,
              "claimed_commit_sha": None, "remote_main_verified": False,
              "failure_stage": None, "source_link_status": None,
              "source_link_checked": None, "source_link_hashes_present": None,
              "source_link_formal": False}
    status = safe_json(root, "four_mode_forecasts/capture_status.json")
    staging = safe_json(root, "four-mode-evidence/staging.json")
    publication = safe_json(root, "four-mode-evidence/publication.json")
    stages = safe_json(root, "four-mode-evidence/stages.json")
    source_links = safe_json(root, "four-mode-evidence/source-links.json")
    result["artifact_present"] = any(x is not None for x in (status, staging, publication, stages, source_links))
    if source_links is not None and source_links.get("schema") in ("FOUR_MODE_LOCAL_SOURCE_LINK_REPORT_V1", "FOUR_MODE_LOCAL_SOURCE_LINK_REPORT_V2"):
        if source_links.get("day_jst") == datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")).astimezone(JST).strftime("%Y%m%d"):
            result["source_link_status"] = source_links.get("publication_scope_status") if source_links.get("schema") == "FOUR_MODE_LOCAL_SOURCE_LINK_REPORT_V2" else "legacy_all_day_archives"
            result["source_link_checked"] = count(source_links, "checked")
            result["source_link_hashes_present"] = count(source_links, "hashes_present")
    try:
        day = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")).astimezone(JST).strftime("%Y%m%d")
    except (KeyError, ValueError, TypeError, AttributeError):
        day = None
    if status is not None and status.get("day_jst") == day and day is not None:
        result["source_title_rows"] = count(status, "published_title_rows")
        result["source_card_rows"] = count(status, "published_card_rows")
        result["generated_today"] = count(status, "eligible_forecasts_today")
        result["newly_generated"] = count(status, "last_run_new_count")
    if staging is not None:
        result["staged_valid"] = count(staging, "staged_valid")
    if publication is not None and publication.get("outcome") in (
        "pushed_to_main", "no_eligible_candidates", "failed"):
        result["publication_outcome"] = publication["outcome"]
        if publication["outcome"] == "pushed_to_main":
            sha = publication.get("commit_sha")
            added = count(publication, "added_forecasts")
            if isinstance(sha, str) and len(sha) == 40 and all(c in "0123456789abcdef" for c in sha):
                result["claimed_commit_sha"] = sha
                result["claimed_added_forecasts"] = added
        elif publication["outcome"] == "failed":
            result["failure_stage"] = publication.get("stage")
    if result["failure_stage"] is None and isinstance(stages, dict):
        if stages.get("publication") == "failed":
            result["failure_stage"] = stages.get("receipt_staging")
    return result


# The 09:20 JST inventory follows nine nominal captures (07:07 through 09:07).
# Six latest runs omit the first three and can hide early publication failures.
# Inspect twelve by default to retain a small retry margin; remain bounded.
def report(history, downloader, limit=12):
    if not isinstance(history, dict) or not isinstance(history.get("runs"), list) or not 1 <= limit <= 20:
        raise ValueError("invalid schedule history")
    rows = []
    for run in history["runs"][:limit]:
        if not isinstance(run, dict) or type(run.get("id")) is not int or run["id"] <= 0:
            raise ValueError("invalid run")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            error = None
            try:
                downloader(run["id"], root)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                error = type(exc).__name__
            row = inspect(run, root)
            if error is not None:
                row["artifact_download_error"] = error
            rows.append(row)
    claimed = [r["claimed_added_forecasts"] for r in rows if r["claimed_added_forecasts"] is not None]
    return {"schema": "FOUR_MODE_SCHEDULE_PUBLICATION_EVIDENCE_V1",
            "scheduled_runs_checked": len(rows),
            "history_runs_available": len(history["runs"]),
            "history_runs_omitted": max(0, len(history["runs"]) - len(rows)),
            "artifacts_present": sum(r["artifact_present"] for r in rows),
            "runs_claiming_push": sum(r["publication_outcome"] == "pushed_to_main" for r in rows),
            "claimed_added_forecasts_sum": sum(claimed) if claimed else None,
            "remote_main_verified": False,
            "note": "Artifact push claims are not independent proof of remote main ancestry.",
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
    def download(run_id, folder):
        subprocess.run(["gh", "run", "download", str(run_id), "--repo", args.repo,
                        "--name", "four-mode-capture-" + str(run_id),
                        "--dir", str(folder)], check=True, capture_output=True, timeout=50)
    result = report(history, download)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("FOUR_MODE_SCHEDULE_PUBLICATION_EVIDENCE=" + json.dumps({
        "scheduled_runs_checked": result["scheduled_runs_checked"],
        "history_runs_omitted": result["history_runs_omitted"],
        "artifacts_present": result["artifacts_present"],
        "runs_claiming_push": result["runs_claiming_push"],
        "claimed_added_forecasts_sum": result["claimed_added_forecasts_sum"],
        "remote_main_verified": False}, sort_keys=True))


if __name__ == "__main__":
    main()
