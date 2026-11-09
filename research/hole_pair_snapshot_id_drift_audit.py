"""Read-only comparison of one frozen hole-pair source roster to a later Git snapshot.

This is a coverage/missingness diagnostic, NOT a scheduler, candidate freezer,
independent receipt, official race calendar or formal study admission. The later
commit must be proven a descendant of the exact original immutable main commit.
No outcome files, forecasts, frozen tickets or production selectors are opened.
"""
import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path

CODE = re.compile(r"20[0-9]{10}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
PATH = re.compile(r"four_mode_forecasts/(20[0-9]{10})\.json\Z")
MAX_IDS = 500


def _ids(codes, day, label):
    if (type(codes) is not list or len(codes) > MAX_IDS
            or any(type(code) is not str for code in codes)
            or codes != sorted(codes) or len(set(codes)) != len(codes)):
        raise ValueError("invalid_or_duplicate_" + label)
    for code in codes:
        if not CODE.fullmatch(code) or code[:8] != day:
            raise ValueError("invalid_or_cross_day_" + label)
        try:
            date(int(code[:4]), int(code[4:6]), int(code[6:8]))
        except ValueError as exc:
            raise ValueError("invalid_calendar_" + label) from exc
        if not (1 <= int(code[8:10]) <= 24 and 1 <= int(code[10:12]) <= 12):
            raise ValueError("invalid_venue_or_race_" + label)
    return codes


def audit(original, later_sha, later_codes, *, descendant_verified=False):
    """Only compare exact IDs after checking the nonformal manifest census."""
    if type(original) is not dict or original.get("schema") != "HOLE_PAIR_FUTURE_ACTIONS_BATCH_V1":
        raise ValueError("invalid_original_batch")
    day, original_sha = original.get("capture_day_jst"), original.get("source_main_commit")
    if (type(day) is not str or not re.fullmatch(r"20[0-9]{6}", day)
            or day < "20261109" or type(original_sha) is not str
            or not SHA.fullmatch(original_sha) or type(later_sha) is not str
            or not SHA.fullmatch(later_sha) or descendant_verified is not True):
        raise ValueError("untrusted_main_history_or_day")
    if (original.get("status") != "local_predeadline_freeze_not_formal"
            or any(original.get(field) is not False for field in (
                "formal", "prospective_validation",
                "independent_first_receipt_verified", "production_forecast_changed"))):
        raise ValueError("untrusted_formal_or_batch_status")
    source = _ids(original.get("source_forecast_codes"), day, "original_ids")
    later = _ids(later_codes, day, "later_ids")
    frozen = original.get("records")
    excluded = original.get("excluded_race_codes_by_reason")
    if type(frozen) is not list or type(excluded) is not dict:
        raise ValueError("invalid_initial_classification")
    frozen_ids = _ids(sorted(r.get("race_code") for r in frozen
                             if type(r) is dict and type(r.get("race_code")) is str),
                      day, "frozen_ids")
    if len(frozen_ids) != len(frozen):
        raise ValueError("invalid_frozen_candidate_ids")
    excluded_ids = []
    for reason, codes in excluded.items():
        if type(reason) is not str:
            raise ValueError("invalid_exclusion_reason")
        excluded_ids.extend(_ids(codes, day, "excluded_ids"))
    if (len(set(frozen_ids + excluded_ids)) != len(source)
            or set(frozen_ids + excluded_ids) != set(source)):
        raise ValueError("original_source_classification_does_not_reconcile")
    coverage = original.get("source_snapshot_coverage")
    if (type(coverage) is not dict
            or coverage.get("source_main_commit") != original_sha
            or coverage.get("capture_day_jst") != day
            or coverage.get("snapshot_forecasts_examined") != len(source)
            or coverage.get("frozen_locally_unverified") != len(frozen)
            or coverage.get("source_snapshot_race_coverage_complete") is not True
            or coverage.get("entire_day_or_official_schedule_complete_verified") is not False
            or original.get("eligible_forecasts_examined") != len(source)
            or original.get("frozen_count") != len(frozen)):
        raise ValueError("untrusted_initial_snapshot_coverage")
    if (original.get("excluded_by_reason") != coverage.get("excluded_by_reason")
            or original.get("excluded_race_codes_by_reason")
            != coverage.get("excluded_race_codes_by_reason")
            or original.get("source_snapshot_coverage", {}).get(
                "frozen_codes_by_candidate_cutoff_order") is None):
        raise ValueError("untrusted_exclusion_census")
    if (sorted(coverage["frozen_codes_by_candidate_cutoff_order"]) != frozen_ids
            or original["excluded_by_reason"] != {
                key: len(value) for key, value in sorted(excluded.items())}):
        raise ValueError("untrusted_frozen_order_or_exclusion_counts")
    added = sorted(set(later) - set(source))
    removed = sorted(set(source) - set(later))
    if original_sha == later_sha and (added or removed):
        raise ValueError("same_immutable_commit_has_different_source_ids")
    return {
        "schema": "HOLE_PAIR_SNAPSHOT_ID_DRIFT_NONFORMAL_V1",
        "capture_day_jst": day,
        "original_main_sha": original_sha,
        "later_descendant_main_sha": later_sha,
        "initial_snapshot_ids": len(source),
        "later_snapshot_ids": len(later),
        "newly_visible_race_codes": added,
        "initial_ids_missing_in_later_snapshot": removed,
        "newly_visible_count": len(added),
        "missing_original_count": len(removed),
        "status": ("id_drift_observed_requires_missingness_review"
                   if (added or removed) else
                   "no_id_drift_observed_whole_day_still_unverified"),
        "later_commit_descendant_verified": True,
        "source_content_or_blob_identity_rechecked": False,
        "whole_day_or_official_schedule_complete_verified": False,
        "first_remote_receipt_verified": False,
        "official_t12_complete_verified": False,
        "pilot_formally_eligible": 0,
        "confirmation_formally_eligible": 0,
        "formal": False,
        "production_promotion_allowed": False,
        "warning": ("A later descendant main snapshot is not an official day universe; "
                    "equal race IDs do not certify unchanged source bytes, "
                    "candidate first receipt, timing or study eligibility."),
    }


def audit_git(original, later_sha, *, run=subprocess.run):
    """Read only git ancestry and exact forecast paths at one immutable commit."""
    original_sha = original.get("source_main_commit") if type(original) is dict else None
    if (type(original_sha) is not str or not SHA.fullmatch(original_sha)
            or type(later_sha) is not str or not SHA.fullmatch(later_sha)):
        raise ValueError("invalid_git_commit_identity")
    ancestor = run(["git", "merge-base", "--is-ancestor", original_sha, later_sha],
                   capture_output=True, text=True, check=False)
    if ancestor.returncode != 0:
        raise ValueError("later_snapshot_not_verified_descendant")
    inventory = run(["git", "ls-tree", "-r", "--name-only", later_sha,
                     "--", "four_mode_forecasts/"],
                    capture_output=True, text=True, check=False)
    if inventory.returncode != 0:
        raise ValueError("later_snapshot_tree_unavailable")
    day = original.get("capture_day_jst")
    paths = inventory.stdout.splitlines()
    if len(paths) > 100000:
        raise ValueError("unbounded_later_tree")
    candidates = [p for p in paths if p.startswith("four_mode_forecasts/" + str(day))]
    codes = []
    for p in candidates:
        match = PATH.fullmatch(p)
        if not match:
            raise ValueError("invalid_later_forecast_path")
        codes.append(match.group(1))
    return audit(original, later_sha, sorted(codes), descendant_verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Original nonformal frozen batch JSON")
    parser.add_argument("--later-main-sha", required=True, help="Exact descendant Git commit SHA")
    args = parser.parse_args()
    source = Path(args.manifest)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 3_000_000:
        raise ValueError("untrusted_original_manifest_file")
    report = audit_git(json.loads(source.read_text(encoding="utf-8")), args.later_main_sha)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
