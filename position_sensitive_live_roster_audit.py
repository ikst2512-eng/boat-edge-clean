"""Read-only whole-ledger live observation roster for #1698 candidate research.

No writer, scheduling, outcome access or formal first-receipt certification.
All candidates are enumerated from a single fetched Git commit, not a manually
selected race. After each T-12 cutoff, NEVER backdate a fresh API observation.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

from four_mode_position_sensitive_forward import (
    CODE, _verify_snapshot, protocol,
)
from position_sensitive_remote_observer import observe_candidate, github_get

SCHEMA = "POSITION_SENSITIVE_ALL_CANDIDATE_LIVE_HTTP_ROSTER_V1"
REMOTE_REF = "refs/remotes/origin/position-sensitive-forward-evidence-ledger"
ORIGINAL_REF = "refs/remotes/origin/main"
PREFIX = "position_sensitive_research/"
README = PREFIX + "README.md"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
MAX_CANDIDATES = 600


def run_git(*args):
    return subprocess.check_output(["git", *args], timeout=30,
                                   stderr=subprocess.DEVNULL)


def inspect_roster(git, observer, now, *, allow_live=False):
    """Read-only audit of a locked branch tip; no results and no publication.

    Observer must be the real GitHub HTTP observer to collect actual server
    observations. Synthetic observer success in tests is NOT real evidence.
    """
    if (not callable(git) or not callable(observer)
            or type(now) is not datetime or now.utcoffset() is None):
        raise ValueError("invalid_roster_dependencies")
    tip = git("rev-parse", "--verify", REMOTE_REF + "^{commit}").decode().strip()
    if HEX40.fullmatch(tip) is None:
        raise ValueError("remote_ref_not_pinned")
    names = git("ls-tree", "-r", "--name-only", tip, "--", PREFIX).decode().splitlines()
    if README not in names or len(names) != len(set(names)):
        raise ValueError("missing_bootstrap_or_duplicate_paths")
    files = [name for name in names if name != README]
    if len(files) > MAX_CANDIDATES:
        raise ValueError("too_many_candidate_files")
    for path in files:
        if (not path.startswith(PREFIX) or not path.endswith(".json")
                or not CODE.fullmatch(path[len(PREFIX):-5])):
            raise ValueError("unapproved_candidate_path")

    verified = []
    # Validate the COMPLETE candidate roster and original bytes before any
    # observer call. No winner, payout or confirmed_results files are read.
    policy = protocol()
    for path in sorted(files):
        code = path[len(PREFIX):-5]
        exact = git("show", tip + ":" + path)
        original = git("show", ORIGINAL_REF + ":four_mode_forecasts/" + code + ".json")
        if type(exact) is not bytes or not 0 < len(exact) <= 30000:
            raise ValueError("invalid_candidate_blob")
        try:
            record = json.loads(exact)
            if type(record) is not dict or record.get("race_code") != code:
                raise ValueError("candidate_identity_invalid")
            snapshot = _verify_snapshot(record, original, policy)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ValueError("candidate_original_exact_replay_failed:" + code) from exc
        deadline = snapshot["deadline"]
        cutoff = deadline - timedelta(minutes=12)
        verified.append((code, original, exact, cutoff))
    rows = []
    for code, original, exact, cutoff in verified:
        row = {
            "race_code": code, "candidate_sha256": hashlib.sha256(exact).hexdigest(),
            "original_sha256": hashlib.sha256(original).hexdigest(),
            "T_minus_12_jst": cutoff.isoformat(),
            "original_and_candidate_ticket_replay": True,
            "independent_first_remote_receipt_verified": False,
            "formal": False, "promotion_allowed": False,
        }
        if now >= cutoff:
            row["status"] = "deadline_cutoff_elapsed_no_new_observation_attempt"
        elif not allow_live:
            row["status"] = "predeadline_read_only_live_observation_not_enabled"
        else:
            observed = observer(code, original)
            if (type(observed) is not dict or
                    observed.get("status") !=
                    "github_candidate_existing_preT12_observation_not_first_receipt"
                    or observed.get("observed_branch_commit_sha") != tip or
                    observed.get("candidate_sha256") != row["candidate_sha256"] or
                    observed.get("original_forecast_sha256") != row["original_sha256"] or
                    observed.get("independent_candidate_first_remote_receipt_verified") is not False or
                    observed.get("formal") is not False or
                    observed.get("promotion_allowed") is not False):
                raise ValueError("candidate_remote_observation_or_tip_mismatch:" + code)
            row["status"] = "remote_existence_observed_preT12_not_first_receipt"
            row["observed_at_utc"] = observed["server_observed_utc"]
        rows.append(row)
    status_counts = {key: sum(row["status"] == key for row in rows) for key in (
        "deadline_cutoff_elapsed_no_new_observation_attempt",
        "predeadline_read_only_live_observation_not_enabled",
        "remote_existence_observed_preT12_not_first_receipt",
    )}
    return {
        "schema": SCHEMA,
        "status": "whole_remote_ledger_snapshot_observed_nonformal",
        "fetched_research_branch_tip": tip,
        "candidate_files": len(files),
        "candidate_original_exact_replays": len(verified),
        "status_counts": status_counts,
        "rows": rows,
        "candidate_first_remote_receipts_independently_verified": 0,
        "complete_capture_and_rescue_run_inventory_verified": False,
        "official_T12_beforeinfo_six_and_120_odds_verified": False,
        "all_candidate_observations_externally_first_arrival_attested": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "Only candidate files at one Git tip were inspected. Even live "
            "GitHub server Date proves existence at observation, NOT first "
            "remote receipt or absence of past branch force rewrite. "
            "Elapsed cutoff races are never re-observed as predeadline. "
            "Current Git branch history and independent official 6/120 "
            "and capture-run inventory are separate necessary gates."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="opt-in READ-ONLY GitHub HTTP GET for races still before T12")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = inspect_roster(
        run_git, lambda code, original: observe_candidate(code, original, github_get),
        datetime.now(timezone.utc), allow_live=args.live)
    raw = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        if args.output.is_symlink() or args.output.exists():
            raise ValueError("output_must_be_new_regular_file")
        args.output.write_text(raw, encoding="utf-8")
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
