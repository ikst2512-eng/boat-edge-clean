"""Read-only source Git-blob drift check between original and descendant main.

For one future nonformal hole-pair batch, independently read both Git trees
without opening raw forecast contents or confirmed results. Audit original
race-ID coverage, pinned frozen source blob IDs, and same-race source changes.
Neither this evidence nor Git commit chronology proves external first receipt,
official T-12 inputs, whole-day completeness, or formal study eligibility.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from research.hole_pair_snapshot_id_drift_audit import (
    SHA, _ids, audit as audit_ids,
)

BLOB = re.compile(r"^(100644|100755) blob ([0-9a-f]{40})\t(four_mode_forecasts/(\d{12})\.json)$")
MAX_TREE_BYTES = 10_000_000
MAX_TREE_LINES = 100_000


def parse_tree(text, day):
    """Require canonical same-day file identities and ordinary Git blobs."""
    if type(text) is not str or len(text.encode("utf-8")) > MAX_TREE_BYTES:
        raise ValueError("untrusted_or_unbounded_git_tree")
    if type(day) is not str or not re.fullmatch(r"20[0-9]{6}", day):
        raise ValueError("invalid_capture_day")
    seen = {}
    lines = text.splitlines()
    if len(lines) > MAX_TREE_LINES:
        raise ValueError("unbounded_git_tree")
    for line in lines:
        if not line.startswith(("100644", "100755", "120000", "160000", "040000")):
            raise ValueError("untrusted_git_tree_entry")
        # Git ls-tree outputs all original-day and other-day forecasts.
        # Noncanonical paths *on the audited day* must not be ignored.
        path = line.split("\t", 1)[1] if "\t" in line else ""
        if not path.startswith("four_mode_forecasts/"):
            raise ValueError("out_of_scope_git_tree_entry")
        if not path.startswith("four_mode_forecasts/" + day):
            continue
        match = BLOB.fullmatch(line)
        if not match:
            raise ValueError("nonregular_or_malformed_same_day_forecast")
        code = match.group(4)
        _ids([code], day, "git_tree_race_code")
        if code in seen:
            raise ValueError("duplicated_git_tree_forecast")
        seen[code] = match.group(2)
    if len(seen) > 500:
        raise ValueError("unbounded_same_day_forecasts")
    return dict(sorted(seen.items()))


def audit_trees(batch, later_sha, original_tree, later_tree, *, descendant_verified=False):
    """No outcomes or candidate re-selection; all proof flags stay false."""
    if type(batch) is not dict:
        raise ValueError("invalid_original_manifest")
    day, original_sha = batch.get("capture_day_jst"), batch.get("source_main_commit")
    if (type(original_sha) is not str or not SHA.fullmatch(original_sha)
            or type(later_sha) is not str or not SHA.fullmatch(later_sha)
            or descendant_verified is not True):
        raise ValueError("untrusted_git_history")
    previous = parse_tree(original_tree, day)
    following = parse_tree(later_tree, day)
    report = audit_ids(batch, later_sha, sorted(following), descendant_verified=True)
    claimed_codes = batch["source_forecast_codes"]
    if sorted(previous) != claimed_codes:
        raise ValueError("original_manifest_source_ids_differ_from_git_tree")
    records = batch["records"]
    for record in records:
        code = record["race_code"]
        if (type(record.get("source_git_blob_sha1")) is not str
                or previous[code] != record["source_git_blob_sha1"]):
            raise ValueError("frozen_source_git_blob_claim_mismatch")
    changed = sorted(
        code for code in previous.keys() & following.keys()
        if previous[code] != following[code]
    )
    if original_sha == later_sha and changed:
        raise ValueError("immutable_commit_blob_drift_impossible")
    report.update({
        "schema": "HOLE_PAIR_SOURCE_BLOB_DRIFT_NONFORMAL_V1",
        "initial_source_tree_matches_manifest_ids": True,
        "initial_frozen_git_blob_claims_match_original_tree": True,
        "changed_same_race_source_git_blob_codes": changed,
        "changed_same_race_source_git_blob_count": len(changed),
        "changed_same_race_git_blob_pairs": {
            code: {
                "original_git_blob_sha1": previous[code],
                "later_git_blob_sha1": following[code],
            } for code in changed
        },
        "git_tree_path_and_sha1_verified": True,
        "raw_source_content_sha256_independently_verified": False,
        "first_remote_receipt_verified": False,
        "whole_day_or_official_schedule_complete_verified": False,
        "pilot_formally_eligible": 0,
        "confirmation_formally_eligible": 0,
        "formal": False,
        "production_promotion_allowed": False,
    })
    if changed:
        report["status"] = "same_race_source_blob_drift_quarantine_and_review"
    report["warning"] = (
        "Original Git tree and frozen SHA1 provenance checked, but this does "
        "not authenticate the manifest, prove raw SHA256, independent first "
        "remote acceptance, official pre-T12 inputs or full-day coverage; "
        "changed same-race source bytes must not silently replace the first candidate."
    )
    return report


def audit_git(batch, later_sha, *, run=subprocess.run):
    if type(batch) is not dict:
        raise ValueError("invalid_original_manifest")
    first_sha = batch.get("source_main_commit")
    if (type(first_sha) is not str or not SHA.fullmatch(first_sha)
            or type(later_sha) is not str or not SHA.fullmatch(later_sha)):
        raise ValueError("invalid_commit_ref")
    ancestry = run(
        ["git", "merge-base", "--is-ancestor", first_sha, later_sha],
        check=False, capture_output=True, text=True,
    )
    if ancestry.returncode != 0:
        raise ValueError("later_commit_not_verified_descendant")
    results = []
    for sha in (first_sha, later_sha):
        r = run(["git", "ls-tree", "-r", sha, "--", "four_mode_forecasts/"],
                check=False, capture_output=True, text=True)
        if r.returncode != 0:
            raise ValueError("unavailable_immutable_git_tree")
        results.append(r.stdout)
    return audit_trees(batch, later_sha, *results, descendant_verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--later-main-sha", required=True)
    args = parser.parse_args()
    path = Path(args.manifest)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 3_000_000:
        raise ValueError("untrusted_manifest_path")
    batch = json.loads(path.read_text(encoding="utf-8"))
    report = audit_git(batch, args.later_main_sha)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
