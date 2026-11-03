"""Score scheduled/dispatch V2 capture artifacts in existing nightly research CI.

Only existing GitHub capture runs, only Nov 4+ created on main, only the
frozen tickets inside the original same-job Actions artifact. No regeneration,
no production promotion, no independent remote first-seen assertion.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from four_mode_v2_frozen_third_artifact_score import score_zip

CUTOFF_CREATED_UTC = "2026-11-03T15:00:00Z"  # Nov 4 JST
EVENTS = {"schedule", "workflow_dispatch"}
STATUS = {"success", "failure", "cancelled", "timed_out", "action_required"}
RUN_MAX = 80
INVENTORY_LIMIT = 500
TOPS = (3, 5, 10)
RUN_ID = re.compile(r"[1-9][0-9]{0,16}\Z")


def choose_runs(inventory):
    if type(inventory) is not list:
        raise ValueError("bad_run_inventory")
    seen = set()
    chosen = []
    for item in inventory:
        if type(item) is not dict:
            raise ValueError("bad_run_inventory_row")
        num = item.get("databaseId")
        if (type(num) is not int or num <= 0
                or not RUN_ID.fullmatch(str(num))
                or num in seen):
            raise ValueError("invalid_or_duplicate_run_id")
        seen.add(num)
        if (item.get("headBranch") != "main" or
                item.get("event") not in EVENTS or
                not isinstance(item.get("createdAt"), str) or
                item["createdAt"] < CUTOFF_CREATED_UTC):
            continue
        if item.get("conclusion") not in STATUS:
            # Includes still-running jobs; don't assert absence or success.
            continue
        chosen.append((item["createdAt"], num, item["conclusion"]))
    chosen.sort()
    return chosen[-RUN_MAX:]


def summarize(inventory, root, download, out_dir):
    """Download exact artifact names and score individually; never count a
    missing artifact as zero-hit. Abort duplicate frozen races across runs."""
    selected = choose_runs(inventory)
    # Never claim a complete study when older captures were silently dropped.
    eligible = sum(1 for row in inventory if type(row) is dict and
                   row.get("headBranch") == "main" and row.get("event") in EVENTS
                   and isinstance(row.get("createdAt"), str)
                   and row["createdAt"] >= CUTOFF_CREATED_UTC
                   and row.get("conclusion") in STATUS)
    truncated = eligible > RUN_MAX
    inventory_limit_reached = len(inventory) >= INVENTORY_LIMIT
    report = {
        "schema": "V2_THIRD_RATE_FROZEN_NIGHTLY_ARTIFACT_AUDIT_V1",
        "status": "no_future_capture_runs" if not selected else "scored_frozen_artifacts",
        "formal": False,
        "remote_first_seen_independently_verified": False,
        "production_promotion_allowed": False,
        "searched_run_limit": RUN_MAX,
        "inventory_limit": INVENTORY_LIMIT,
        "eligible_runs_in_inventory": eligible,
        "older_eligible_runs_omitted": max(0, eligible - len(selected)),
        "inventory_limit_reached": inventory_limit_reached,
        "cohort_completeness_verified": False,
        "selected_runs": len(selected),
        "downloaded_artifacts": 0,
        "no_new_candidate_runs": 0,
        "bad_validation_runs": [],
        "missing_or_failed_artifacts": [],
        "paired": 0, "frozen": 0, "pending_results": 0,
        "invalid": 0, "excluded": 0,
        "race_codes_paired": [],
        "topn": {f"top{n}": {"baseline": 0, "candidate": 0,
                            "gained": 0, "lost": 0} for n in TOPS},
        "runs": [],
        "warning": "Limited recent-run inventory, no independent first-publication proof; never substitute retrospective rankings.",
    }
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frozen_seen = set()
    for _, run_id, conclusion in selected:
        row = {"run_id": run_id, "conclusion": conclusion}
        path = out_dir / (str(run_id) + ".zip")
        # Failed runs may still provide evidence. Capture all eligible runs.
        try:
            download(run_id, path)
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 15_000_000:
                raise ValueError("missing_or_unsafe_zip")
            scoring = score_zip(path, root)
            if scoring["published_forecasts"] == 0 and scoring["frozen"] == 0:
                # An explicitly successful no-new-publication report is normal.
                # A freeze validation failure must NEVER masquerade as empty.
                if (scoring.get("publication_evidence_status") != "no_confirmed_publication"
                        or scoring.get("validation_error_count", 0)):
                    raise ValueError("invalid_or_failed_empty_publication")
                row["status"] = "no_new_candidate_publication"
                report["no_new_candidate_runs"] += 1
                report["downloaded_artifacts"] += 1
                report["runs"].append(row)
                continue
            if scoring["invalid"] or scoring.get("validation_error_count", 0):
                report["bad_validation_runs"].append(run_id)
        except (OSError, ValueError, KeyError, TypeError,
                subprocess.SubprocessError, __import__("zipfile").BadZipFile) as exc:
            row["status"] = "artifact_unavailable_or_invalid"
            row["error_type"] = type(exc).__name__
            report["missing_or_failed_artifacts"].append(run_id)
            report["runs"].append(row)
            continue
        frozen = scoring["race_codes_frozen"]
        overlap = frozen_seen.intersection(frozen)
        if overlap:
            raise ValueError("duplicate_frozen_race_across_capture_runs")
        frozen_seen.update(frozen)
        row.update({"status": "read_only_scored",
                    "frozen": scoring["frozen"],
                    "paired": scoring["paired"],
                    "invalid": scoring["invalid"]})
        report["runs"].append(row)
        report["downloaded_artifacts"] += 1
        for field in ("paired", "frozen", "pending_results", "invalid", "excluded"):
            report[field] += scoring[field]
        report["race_codes_paired"].extend(scoring["race_codes_paired"])
        for n in TOPS:
            for name in ("baseline", "candidate", "gained", "lost"):
                report["topn"][f"top{n}"][name] += scoring["topn"][f"top{n}"][name]
    report["race_codes_paired"].sort()
    if len(set(report["race_codes_paired"])) != report["paired"]:
        raise ValueError("paired_roster_mismatch")
    for score in report["topn"].values():
        if score["candidate"] - score["baseline"] != score["gained"] - score["lost"]:
            raise ValueError("paired_gain_loss_mismatch")
    if report["missing_or_failed_artifacts"] or report["bad_validation_runs"]:
        report["status"] = "incomplete_capture_artifact_evidence"
    if truncated or inventory_limit_reached:
        report["status"] = "incomplete_run_inventory_coverage"
    if not report["downloaded_artifacts"] and selected and not (truncated or inventory_limit_reached):
        report["status"] = "capture_artifacts_unavailable"
    report["cohort_completeness_verified"] = bool(
        selected and not truncated and not inventory_limit_reached
        and not report["missing_or_failed_artifacts"]
        and not report["bad_validation_runs"])
    if report["cohort_completeness_verified"] and report["status"] == "scored_frozen_artifacts":
        report["status"] = "frozen_artifacts_scored_limited_cohort"
    return report


def _gh_download(run_id, destination):
    # The filename is the exact existing artifact name for the capture run.
    subprocess.run([
        "gh", "run", "download", str(run_id),
        "--name", "four-mode-capture-" + str(run_id),
        "--dir", str(destination.parent / ("extract_" + str(run_id))),
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=30)
    import zipfile
    extracted = destination.parent / ("extract_" + str(run_id))
    # gh extracts original artifact content, not an archive ZIP. Repack
    # the original exact bytes, preserving only the path needed by scorer.
    source = extracted / "four-mode-evidence" / "third-rate-shadow.json"
    if not source.is_file() or source.is_symlink() or source.stat().st_size > 2_000_000:
        raise ValueError("missing_third_rate_shadow")
    with zipfile.ZipFile(destination, "w") as z:
        z.write(source, "four-mode-evidence/third-rate-shadow.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-inventory", required=True, type=Path)
    parser.add_argument("--root", default=Path("."), type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.run_inventory.read_text(encoding="utf-8"))
    report = summarize(data, args.root, _gh_download, args.out_dir)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("V2_FROZEN_THIRD_NIGHTLY=" + json.dumps(report, sort_keys=True))
    # An incomplete run inventory is an evidence gap; visible diagnostic.
    # Do not fail unrelated research CI, but never claim successful holdout.
