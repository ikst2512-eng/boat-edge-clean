"""Read-only scheduled V2 collection evidence. A claimed push is not remote proof."""
import argparse
import json
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
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


def research_roster_evidence(publication, third, hole):
    """Check artifact-local same-run identities, not independent Git remote proof."""
    if not isinstance(publication, dict):
        return {"status": "unknown", "reason": "publication_evidence_missing"}
    if publication.get("outcome") != "pushed_to_main":
        return {"status": "not_applicable" if publication.get("outcome") == "no_eligible_candidates"
                else "unknown", "reason": "no_confirmed_push"}
    sha = publication.get("commit_sha")
    added = count(publication, "added_forecasts")
    if (not isinstance(sha, str) or len(sha) != 40
            or any(ch not in "0123456789abcdef" for ch in sha)
            or added is None or added <= 0):
        return {"status": "mismatch", "reason": "invalid_publication_claim"}
    if not isinstance(third, dict) or not isinstance(hole, dict):
        return {"status": "unknown", "reason": "research_artifact_missing"}
    if (third.get("schema") != "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1"
            or hole.get("schema") != "HOLE_SHADOW_PUBLISHED_SAME_JOB_V1"):
        return {"status": "mismatch", "reason": "wrong_shadow_schema"}
    if (third.get("publication_commit_sha") != sha
            or hole.get("publication_commit_sha") != sha
            or count(third, "published_forecasts") != added
            or count(hole, "published_new_count") != added):
        return {"status": "mismatch", "reason": "shadow_commit_or_count_mismatch"}
    rosters = []
    for artifact in (third, hole):
        records = artifact.get("records")
        if (not isinstance(records, list) or len(records) != added
                or not all(isinstance(row, dict)
                           and isinstance(row.get("race_code"), str)
                           and len(row["race_code"]) == 12
                           and row["race_code"].isdigit()
                           and row["race_code"].startswith("20")
                           for row in records)):
            return {"status": "mismatch", "reason": "invalid_shadow_race_roster"}
        codes = [row["race_code"] for row in records]
        if len(set(codes)) != len(codes):
            return {"status": "mismatch", "reason": "duplicate_shadow_race"}
        rosters.append(set(codes))
    if rosters[0] != rosters[1]:
        return {"status": "mismatch", "reason": "shadow_race_rosters_disagree"}
    # The three third-rate verdicts must form a strict partition, including
    # the independently accounted validation-error status.
    if "ineligible_count" in third:
        actual = sum(row.get("status") == "ineligible" for row in third["records"])
        reported = third["ineligible_count"]
        if type(reported) is not int or reported != actual:
            return {"status": "mismatch",
                    "reason": "shadow_freeze_accounting_mismatch",
                    "research": "third", "field": "ineligible_count",
                    "reported": reported, "record_count": actual}
    # Match of IDs is not proof that all records were successfully frozen.
    # Where the producer supplies aggregate verdicts, they must agree with
    # each actual per-race status. Older hole artifacts without the new
    # validation_error_count retain identity-only verification.
    for artifact, frozen_key, frozen_status, label in (
            (third, "frozen_before_t_minus_12",
             "frozen_in_same_job_before_t_minus_12", "third"),
            (hole, "frozen_count", "shadow_frozen_unverified", "hole")):
        records = artifact["records"]
        for key, status in ((frozen_key, frozen_status),
                            ("validation_error_count", "validation_error")):
            if key not in artifact:
                continue  # Legacy artifact: unknown accounting, not proven zero.
            reported = artifact[key]
            actual = sum(row.get("status") == status for row in records)
            if type(reported) is not int or reported < 0 or reported != actual:
                return {"status": "mismatch",
                        "reason": "shadow_freeze_accounting_mismatch",
                        "research": label, "field": key,
                        "reported": reported, "record_count": actual}
    return {"status": "matched", "reason": "same_local_push_claim_and_race_roster",
            "matched_races": added, "commit_sha": sha,
            # Exact identities are needed for the later independent Git-tree
            # reconciliation. This list is bounded by added_forecasts <= 500
            # in normal capture receipts and contains public race IDs only.
            "race_codes": sorted(rosters[0])}


def inspect(run, root):
    """Keep unknown separate from zero; never reclassify local push claims as remote proof."""
    result = {"run_id": run["id"], "created_at": run.get("created_at"),
              "capture_conclusion": run.get("capture_conclusion"),
              "failed_steps": run.get("failed_steps", []),
              "artifact_present": False, "source_title_rows": None,
              "source_card_rows": None, "generated_today": None,
              "excluded_races": None, "excluded_race_count": None,
              "newly_generated": None, "staged_valid": None,
              "publication_outcome": None, "claimed_added_forecasts": None,
              "claimed_commit_sha": None, "remote_main_verified": False,
              "failure_stage": None, "third_rate_shadow_outcome": None,
              "hole_shadow_outcome": None, "third_rate_ledger_outcome": None,
              "third_rate_ledger_status": None, "third_rate_ledger_probe_status": None,
              "research_roster_evidence": None,
              "source_link_status": None,
              "source_link_checked": None, "source_link_hashes_present": None,
              "source_link_formal": False}
    status = safe_json(root, "four_mode_forecasts/capture_status.json")
    staging = safe_json(root, "four-mode-evidence/staging.json")
    publication = safe_json(root, "four-mode-evidence/publication.json")
    stages = safe_json(root, "four-mode-evidence/stages.json")
    third = safe_json(root, "four-mode-evidence/third-rate-shadow.json")
    hole = safe_json(root, "four-mode-evidence/hole-shadow.json")
    ledger = safe_json(root, "four-mode-evidence/third-rate-ledger.json")
    if ledger is not None:
        status_value = ledger.get("status")
        if status_value in ("new_immutable_ledger_entry",
                            "already_preserved_identical",
                            "no_eligible_frozen_predictions",
                            "ledger_preservation_failed"):
            result["third_rate_ledger_status"] = status_value
        probe = ledger.get("write_access_probe")
        if isinstance(probe, dict) and probe.get("status") in (
                "new_write_permission_probe", "existing_write_probe_readback"):
            result["third_rate_ledger_probe_status"] = probe["status"]
    result["research_roster_evidence"] = research_roster_evidence(publication, third, hole)
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
        excluded = status.get("excluded")
        if isinstance(excluded, dict) and all(
            isinstance(reason, str) and type(number) is int and number >= 0
            for reason, number in excluded.items()
        ):
            result["excluded_race_count"] = sum(excluded.values())
        details = status.get("excluded_races")
        if isinstance(details, list) and len(details) <= 30 and all(
            isinstance(row, dict)
            and isinstance(row.get("race_code"), str)
            and len(row["race_code"]) == 12
            and row["race_code"].isdigit()
            and row["race_code"].startswith(day)
            and isinstance(row.get("reason"), str)
            and 0 < len(row["reason"]) <= 64
            for row in details
        ):
            result["excluded_races"] = details
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
    # Research step outcomes are separate from immutable V2 publication.
    # Old artifacts may lack these fields: unknown is not success.
    if isinstance(stages, dict):
        for field in ("third_rate_shadow", "hole_shadow", "third_rate_ledger"):
            value = stages.get(field)
            if value in ("success", "failure", "skipped", "cancelled"):
                result[field + "_outcome"] = value
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
    selected = history["runs"][:limit]
    for run in selected:
        if not isinstance(run, dict) or type(run.get("id")) is not int or run["id"] <= 0:
            raise ValueError("invalid run")

    def inspect_one(run):
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
            return row

    # At 09:20 JST the daily audit checks up to twelve captures. Twelve
    # sequential 50-second gh downloads can exhaust the 12-minute job budget
    # before the independent Git publication gate executes. Four bounded
    # workers preserve listing order and isolate downloads in separate dirs.
    with ThreadPoolExecutor(max_workers=min(4, len(selected) or 1)) as pool:
        rows = list(pool.map(inspect_one, selected))
    claimed = [r["claimed_added_forecasts"] for r in rows if r["claimed_added_forecasts"] is not None]
    # Failure count alone is misleading when prior artifacts do not contain
    # the new stage verdicts. Report coverage per research step explicitly.
    research_coverage = {}
    for field in ("third_rate_shadow", "hole_shadow"):
        outcomes = [r[field + "_outcome"] for r in rows]
        research_coverage[field] = {
            "success": outcomes.count("success"),
            "failure": outcomes.count("failure"),
            "skipped": outcomes.count("skipped"),
            "cancelled": outcomes.count("cancelled"),
            "unknown": outcomes.count(None),
            "checked": len(outcomes),
        }
    ledger_outcomes = [r["third_rate_ledger_outcome"] for r in rows]
    return {"schema": "FOUR_MODE_SCHEDULE_PUBLICATION_EVIDENCE_V1",
            "scheduled_runs_checked": len(rows),
            "history_runs_available": len(history["runs"]),
            "history_runs_omitted": max(0, len(history["runs"]) - len(rows)),
            "artifacts_present": sum(r["artifact_present"] for r in rows),
            "runs_claiming_push": sum(r["publication_outcome"] == "pushed_to_main" for r in rows),
            "research_stage_coverage": research_coverage,
            "third_rate_ledger_coverage": {
                "success": ledger_outcomes.count("success"),
                "failure": ledger_outcomes.count("failure"),
                "skipped": ledger_outcomes.count("skipped"),
                "cancelled": ledger_outcomes.count("cancelled"),
                "unknown": ledger_outcomes.count(None),
                "checked": len(ledger_outcomes)},
            "third_rate_ledger_failure_run_ids": [
                r["run_id"] for r in rows
                if r["third_rate_ledger_outcome"] == "failure"
                or r["third_rate_ledger_status"] == "ledger_preservation_failed"],
            "third_rate_ledger_probe_verified_run_ids": [
                r["run_id"] for r in rows
                if r["third_rate_ledger_probe_status"] in (
                    "new_write_permission_probe", "existing_write_probe_readback")
                and r["third_rate_ledger_outcome"] == "success"],
            "research_roster_status_counts": {
                state: sum(r["research_roster_evidence"]["status"] == state for r in rows)
                for state in ("matched", "mismatch", "unknown", "not_applicable")},
            "research_roster_mismatch_run_ids": [
                r["run_id"] for r in rows
                if r["research_roster_evidence"]["status"] == "mismatch"],
            "third_rate_shadow_failure_runs": [
                r["run_id"] for r in rows if r["third_rate_shadow_outcome"] == "failure"],
            "hole_shadow_failure_runs": [
                r["run_id"] for r in rows if r["hole_shadow_outcome"] == "failure"],
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
        "excluded_race_evidence": [
            {"run_id": row["run_id"],
             "excluded_race_count": row["excluded_race_count"],
             "excluded_races": row["excluded_races"]}
            for row in result["runs"] if row["excluded_race_count"]
        ],
        "artifacts_present": result["artifacts_present"],
        "runs_claiming_push": result["runs_claiming_push"],
        "research_stage_coverage": result["research_stage_coverage"],
        "third_rate_ledger_coverage": result["third_rate_ledger_coverage"],
        "third_rate_ledger_failure_run_ids": result["third_rate_ledger_failure_run_ids"],
        "third_rate_ledger_probe_verified_run_ids": result["third_rate_ledger_probe_verified_run_ids"],
        "research_roster_status_counts": result["research_roster_status_counts"],
        "research_roster_mismatch_run_ids": result["research_roster_mismatch_run_ids"],
        "third_rate_shadow_failure_runs": result["third_rate_shadow_failure_runs"],
        "hole_shadow_failure_runs": result["hole_shadow_failure_runs"],
        "claimed_added_forecasts_sum": result["claimed_added_forecasts_sum"],
        "remote_main_verified": False}, sort_keys=True))


if __name__ == "__main__":
    main()
