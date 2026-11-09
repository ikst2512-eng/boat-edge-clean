"""Read-only full-day ORIGINAL-to-candidate delivery-gap inventory for #1698.

This is a diagnosis of SAVED original V2 files, not all scheduled capture
opportunities or a first-remote-receipt audit. It never reads race outcomes,
publishes a candidate, dispatches a collector or changes the frozen selector.
"""
import argparse
import hashlib
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess

from four_mode_position_sensitive_forward import (
    CODE, DATE_START, DATE_END, _pre_result, _verify_snapshot, protocol,
)
from position_sensitive_append_only_research import _no_duplicate_keys

SCHEMA = "POSITION_SENSITIVE_ORIGINAL_TO_CANDIDATE_DELIVERY_GAP_V1"
MAIN_REF = "refs/remotes/origin/main"
LEDGER_REF = "refs/remotes/origin/position-sensitive-forward-evidence-ledger"
SOURCE_DIR = "four_mode_forecasts/"
CANDIDATE_DIR = "position_sensitive_research/"
LEDGER_README = CANDIDATE_DIR + "README.md"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
DAY = re.compile(r"20[0-9]{6}\Z")
MAX_FILES = 500
MAX_LEDGER = 600
MARGIN_SECONDS = 90


def _git(*args):
    return subprocess.check_output(
        ["git", *args], timeout=30, stderr=subprocess.DEVNULL)


def audit_delivery_gap(git, day, as_of):
    """Validate exact Git blob replays before reporting NOT-YET-SAVED originals.

    The two source refs are pinned to their observed local fetched commit
    tips. They are NOT independently authenticated remote first receipts.
    """
    if (not callable(git) or type(day) is not str or DAY.fullmatch(day) is None
            or not DATE_START[:10].replace("-", "") <= day <=
            DATE_END[:10].replace("-", "")
            or type(as_of) is not datetime or as_of.utcoffset() is None):
        raise ValueError("invalid_day_or_readonly_git_clock")
    main_sha = git("rev-parse", "--verify", MAIN_REF + "^{commit}").decode().strip()
    ledger_sha = git("rev-parse", "--verify", LEDGER_REF + "^{commit}").decode().strip()
    if SHA40.fullmatch(main_sha) is None or SHA40.fullmatch(ledger_sha) is None:
        raise ValueError("untrusted_git_ref")
    original_names = git(
        "ls-tree", "-r", "--name-only", main_sha, "--", SOURCE_DIR).decode().splitlines()
    ledger_names = git(
        "ls-tree", "-r", "--name-only", ledger_sha, "--", CANDIDATE_DIR).decode().splitlines()
    if len(ledger_names) != len(set(ledger_names)) or LEDGER_README not in ledger_names:
        raise ValueError("ledger_roster_missing_or_duplicate")
    other_ledger = [name for name in ledger_names if name != LEDGER_README]
    if len(other_ledger) > MAX_LEDGER:
        raise ValueError("candidate_roster_overflow")
    for path in other_ledger:
        if (not path.startswith(CANDIDATE_DIR) or not path.endswith(".json")
                or CODE.fullmatch(path[len(CANDIDATE_DIR):-5]) is None):
            raise ValueError("unapproved_research_candidate_path")
    candidates = {
        name[len(CANDIDATE_DIR):-5]: name for name in other_ledger
        if name[len(CANDIDATE_DIR):-5].startswith(day)
    }
    source_names = [
        name for name in original_names
        if name.startswith(SOURCE_DIR + day)
        and name.endswith(".json")
        and CODE.fullmatch(name[len(SOURCE_DIR):-5]) is not None
    ]
    if len(source_names) != len(set(source_names)) or len(source_names) > MAX_FILES:
        raise ValueError("original_roster_invalid_or_overflow")
    source_names.sort()
    if not set(candidates).issubset({
        name[len(SOURCE_DIR):-5] for name in source_names
    }):
        raise ValueError("candidate_without_original_on_pinned_main")
    p = protocol()
    eligible = {}
    invalid = []
    for path in source_names:
        code = path[len(SOURCE_DIR):-5]
        raw = git("show", main_sha + ":" + path)
        if type(raw) is not bytes or not 0 < len(raw) <= 30000:
            invalid.append({"race_code": code, "reason": "original_blob_invalid_size"})
            if code in candidates:
                raise ValueError("saved_candidate_original_invalid")
            continue
        try:
            source = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
            if type(source) is not dict:
                raise ValueError("original_not_object")
            _, deadline, generated, _ = _pre_result(raw, code, p)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            invalid.append({
                "race_code": code,
                "reason": str(exc)[:85] or type(exc).__name__,
            })
            if code in candidates:
                raise ValueError("candidate_original_failed_exact_replay") from exc
            continue
        eligible[code] = (raw, deadline, generated)
    rows = []
    for code, (raw, deadline, generated) in sorted(
        eligible.items(), key=lambda item: (item[1][1], item[0])
    ):
        cutoff = deadline - timedelta(minutes=12)
        saved = code in candidates
        if saved:
            candidate_bytes = git("show", ledger_sha + ":" + candidates[code])
            if type(candidate_bytes) is not bytes or not 0 < len(candidate_bytes) <= 30000:
                raise ValueError("candidate_size_invalid")
            try:
                candidate = json.loads(candidate_bytes, object_pairs_hook=_no_duplicate_keys)
                checked = _verify_snapshot(candidate, raw, p)
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                raise ValueError("saved_candidate_not_reproducible") from exc
            if checked["code"] != code:
                raise ValueError("candidate_original_code_mismatch")
            candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()
            status = "candidate_saved_exact_replay_no_first_receipt"
        elif generated > as_of:
            status = "original_recorded_generation_after_observation_clock"
        elif as_of < cutoff - timedelta(seconds=MARGIN_SECONDS):
            status = "missing_candidate_local_window_still_open"
        else:
            status = "missing_candidate_local_window_elapsed"
        rows.append({
            "race_code": code,
            "status": status,
            "deadline_jst": deadline.isoformat(),
            "T_minus_12_jst": cutoff.isoformat(),
            "candidate_saved": saved,
            "original_sha256": hashlib.sha256(raw).hexdigest(),
            "candidate_sha256": candidate_hash if saved else None,
            "independent_first_remote_receipt_verified": False,
        })
    status_counts = {
        label: sum(row["status"] == label for row in rows)
        for label in (
            "candidate_saved_exact_replay_no_first_receipt",
            "missing_candidate_local_window_still_open",
            "missing_candidate_local_window_elapsed",
            "original_recorded_generation_after_observation_clock",
        )
    }
    count = len(rows)
    saved = status_counts["candidate_saved_exact_replay_no_first_receipt"]
    # Stable digest of this EXACT pinned Git source/candidate roster, not a
    # remote immutability attestation. It lets auditors compare CI artifacts.
    roster_identity = {
        "day": day, "main_sha": main_sha, "ledger_sha": ledger_sha,
        "rows": rows, "invalid_original_files": invalid,
    }
    roster_digest = hashlib.sha256(
        json.dumps(roster_identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema": SCHEMA,
        "status": "pinned_local_git_original_to_candidate_gap_nonformal",
        "day_jst": day,
        "as_of_internal_runner_clock": as_of.isoformat(),
        "source": "currently_saved_original_V2_forecasts_only_NOT_all_scheduled_runs",
        "main_git_snapshot_sha": main_sha,
        "ledger_git_snapshot_sha": ledger_sha,
        "original_files_present_in_pinned_main": len(source_names),
        "eligible_original_exact_replays": count,
        "invalid_original_files": invalid,
        "candidate_files_on_day": len(candidates),
        "candidate_exact_original_replays": saved,
        "originals_missing_candidate": count - saved,
        "candidate_delivery_coverage_pct_of_eligible_original_files":
            round(100 * saved / count, 2) if count else None,
        "status_counts": status_counts,
        "per_race_complete_saved_original_roster": rows,
        "pinned_snapshot_roster_sha256": roster_digest,
        "open_missing_race_examples": [
            row["race_code"] for row in rows
            if row["status"] == "missing_candidate_local_window_still_open"
        ][:15],
        "elapsed_missing_race_examples": [
            row["race_code"] for row in rows
            if row["status"] == "missing_candidate_local_window_elapsed"
        ][:15],
        "candidate_first_remote_receipts_independently_verified": 0,
        "official_beforeinfo_exhibition_six_odds120_verified": False,
        "complete_capture_and_rescue_run_inventory_verified": False,
        "formal_forward_eligible_races": 0,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "Counts only original forecast files visible at ONE currently fetched "
            "main Git tip. Does NOT identify all scheduled opportunities or "
            "authenticate main first remote arrival, candidate first remote "
            "receipt, exact local clock, independent official six/120, or "
            "results. Missing candidates are an operational delivery gap, "
            "NOT a formally eligible denominator. No retrospective admission."
        ),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--day", default="20261109")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    report = audit_delivery_gap(_git, args.day, datetime.now(timezone.utc))
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        if args.output.is_symlink() or args.output.exists():
            raise ValueError("output_must_be_new_regular_file")
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
