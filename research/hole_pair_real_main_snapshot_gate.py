"""Result-blind original-Git-byte source snapshot for hole-pair research.

Read exactly one immutable source commit. Never freeze/reselect tickets, open
results, fetch official data, access network, or grant formal eligibility.
The snapshot beforeinfo field is NOT authoritative official-source proof.
"""
import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from research.hole_pair_source_blob_drift_audit import parse_tree

SHA = re.compile(r"[0-9a-f]{40}\Z")
DAY = re.compile(r"20\d{6}\Z")
JST = timedelta(hours=9)
MODEL = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
SCHEMA = "HOLE_PAIR_ACTUAL_MAIN_SOURCE_READINESS_NONFORMAL_V1"


def _jst(s, day):
    if type(s) is not str:
        raise ValueError("missing_original_jst_clock")
    try:
        v = datetime.fromisoformat(s)
    except ValueError as ex:
        raise ValueError("invalid_original_jst_clock") from ex
    if v.utcoffset() != JST or v.strftime("%Y%m%d") != day:
        raise ValueError("original_jst_clock_wrong_day_or_timezone")
    return v


def audit(day, source_commit, reference_clock, tree_text, read_blob):
    """Verify listed original Git blob SHA1, then inspect source metadata only."""
    if (type(day) is not str or not DAY.fullmatch(day) or day < "20261109"
            or type(source_commit) is not str or not SHA.fullmatch(source_commit)):
        raise ValueError("untrusted_source_commit_or_day")
    if not callable(read_blob):
        raise ValueError("missing_git_blob_reader")
    ref = _jst(reference_clock, day)
    originals = parse_tree(tree_text, day)
    rows, counts = [], Counter()
    for code, blob in originals.items():
        raw = read_blob(blob)
        if type(raw) is not bytes or not 0 < len(raw) <= 30_000:
            raise ValueError("invalid_original_git_blob_bytes")
        git_hash = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
        ).hexdigest()
        if git_hash != blob:
            raise ValueError("original_git_blob_sha1_mismatch")
        try:
            record = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError) as ex:
            raise ValueError("malformed_original_json") from ex
        if (type(record) is not dict or record.get("race_code") != code
                or record.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"
                or record.get("model_version") != MODEL
                or record.get("status") != "provisional"
                or type(record.get("modes")) is not dict):
            raise ValueError("unexpected_original_model_or_identity")
        deadline = _jst(record.get("deadline_jst"), day)
        generated = _jst(record.get("generated_at_jst"), day)
        cutoff = deadline - timedelta(minutes=12)
        before = record.get("beforeinfo")
        if before == "optional_not_in_snapshot":
            content_flag = "optional_beforeinfo_not_in_snapshot"
            counts["optional_beforeinfo_absent_from_forecast"] += 1
        else:
            # Never infer a positive official-source verification from fields.
            content_flag = "beforeinfo_field_present_or_unknown_not_officially_verified"
            counts["beforeinfo_field_not_officially_verified"] += 1
        if generated < cutoff:
            counts["locally_generated_before_declared_t12"] += 1
        else:
            counts["not_generated_before_declared_t12"] += 1
        if ref < cutoff:
            counts["declared_t12_still_future_at_reference"] += 1
        else:
            counts["declared_t12_elapsed_at_reference"] += 1
        rows.append({
            "race_code": code,
            "source_git_blob_sha1": blob,
            "source_sha256_from_verified_git_bytes": hashlib.sha256(raw).hexdigest(),
            "local_generated_jst_claim": record["generated_at_jst"],
            "local_declared_deadline_jst": record["deadline_jst"],
            "local_declared_t_minus_12_jst": cutoff.isoformat(),
            "beforeinfo_snapshot_status": content_flag,
            "generated_before_local_declared_t12": generated < cutoff,
            "declared_t12_open_at_reference": ref < cutoff,
            "official_complete_six_boat_beforeinfo_verified": False,
            "official_complete_120_way_odds_verified": False,
            "independent_first_candidate_receipt_verified": False,
            "formal_candidate": False,
        })
    return {
        "schema": SCHEMA,
        "capture_day_jst": day,
        "immutable_source_commit": source_commit,
        "reference_clock_jst": ref.isoformat(),
        "original_git_blob_sha1_verified_count": len(rows),
        "original_source_sha256_computed_count": len(rows),
        "original_main_forecast_ids_examined": len(rows),
        "optional_beforeinfo_absent_from_forecast": counts["optional_beforeinfo_absent_from_forecast"],
        "beforeinfo_field_not_officially_verified": counts["beforeinfo_field_not_officially_verified"],
        "locally_generated_before_declared_t12": counts["locally_generated_before_declared_t12"],
        "not_generated_before_declared_t12": counts["not_generated_before_declared_t12"],
        "declared_t12_still_future_at_reference": counts["declared_t12_still_future_at_reference"],
        "declared_t12_elapsed_at_reference": counts["declared_t12_elapsed_at_reference"],
        "same_race_official_t12_origins_authenticated": 0,
        "first_independent_signed_candidate_receipts_authenticated": 0,
        "whole_day_official_schedule_verified": False,
        "prospective_pilot_formally_eligible": 0,
        "prospective_confirmation_formally_eligible": 0,
        "formal": False,
        "production_promotion_allowed": False,
        "result_files_read": False,
        "rows": rows,
        "warning": (
            "This checks only exact Git source snapshot. Missing beforeinfo in "
            "a forecast does not prove it was absent from other archives. "
            "Local generation timing does not authenticate external candidate "
            "acceptance or a real official deadline. No scoring allowed."
        ),
    }


def git_audit(day, sha, reference_clock):
    """Read only an immutable local Git tree; never fetch mutable refs."""
    if type(sha) is not str or not SHA.fullmatch(sha):
        raise ValueError("untrusted_source_commit")
    def run(*args, text=False):
        r = subprocess.run(["git", *args], check=False,
                           capture_output=True, text=text)
        if r.returncode:
            raise ValueError("required_immutable_git_object_unavailable")
        return r.stdout
    actual = run("rev-parse", "--verify", sha + "^{commit}", text=True).strip()
    if actual != sha:
        raise ValueError("git_commit_identity_not_pinned")
    tree = run("ls-tree", "-r", sha, "--", "four_mode_forecasts/", text=True)
    return audit(day, sha, reference_clock, tree, lambda oid: run("cat-file", "blob", oid))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--day", required=True)
    p.add_argument("--source-commit", required=True)
    p.add_argument("--reference-clock-jst", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    report = git_audit(a.day, a.source_commit, a.reference_clock_jst)
    target = Path(a.output)
    if target.is_symlink() or target.exists():
        raise ValueError("output_already_exists_or_symlink")
    target.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
    print("REAL_MAIN_SOURCE_AUDIT", json.dumps({
        k: v for k, v in report.items() if k not in ("rows", "warning")
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
