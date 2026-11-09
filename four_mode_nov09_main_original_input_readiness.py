"""Read-only current-main Nov9 saved V2 input audit, with NO result or candidate scoring.

Read one pinned main commit through git show/ls-tree. Verify exact blob bytes and
the original V2 probability ordering before any later outcomes are considered.
Saving a forecast before T-12 is NOT official six-boat/120-odds provenance,
independent first remote candidate receipt, or a certified model result.
"""
import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from four_mode_top1_bias_input_audit import (
    verified_pre_result_snapshot, MODES, LENGTHS,
)

RACE_FILE = re.compile(r"four_mode_forecasts/(20[0-9]{10})\.json\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
BLOB = re.compile(r"[0-9a-f]{40}\Z")
SAFE_REF = re.compile(r"[A-Za-z0-9._/-]{1,150}\Z")
RESULT_KEYS = frozenset({
    "finish_order", "winning_ticket", "confirmed_result", "result",
    "payout", "confirmed_at_jst", "actual_trifecta", "candidate",
    "candidate_tickets", "candidate_mode_tickets",
})


def sha1_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def jst(value):
    if type(value) is not str:
        raise ValueError("timestamp_not_text")
    value = datetime.fromisoformat(value)
    if value.utcoffset() != timedelta(hours=9):
        raise ValueError("timestamp_not_jst")
    return value


def review_snapshot(entries, day, commit):
    """entries: exact (git path, sha1 Git blob ID, bytes) from ONE pinned tree."""
    if (type(day) is not str or not re.fullmatch(r"20[0-9]{6}", day)
            or type(commit) is not str or not COMMIT.fullmatch(commit)):
        raise ValueError("invalid_day_or_commit")
    files = list(entries)
    seen = set()
    errors = []
    head = {mode: Counter() for mode in MODES}
    beforeinfo = Counter()
    earned = 0
    before_cutoff = 0
    source_before_generation = 0
    rates_seen = set()
    for path, blobid, raw in files:
        code = ""
        try:
            if (not isinstance(path, str) or not RACE_FILE.fullmatch(path)
                    or not path.startswith("four_mode_forecasts/" + day)):
                raise ValueError("invalid_saved_path_or_day")
            code = RACE_FILE.fullmatch(path).group(1)
            if code in seen:
                raise ValueError("duplicate_race_path")
            seen.add(code)
            if (type(blobid) is not str or not BLOB.fullmatch(blobid)
                    or type(raw) is not bytes or not 0 < len(raw) <= 30000
                    or sha1_blob(raw) != blobid):
                raise ValueError("git_blob_content_mismatch")
            archive = json.loads(raw)
            if not isinstance(archive, dict) or RESULT_KEYS.intersection(archive):
                raise ValueError("result_or_candidate_leak_into_saved_original")
            rates, tickets = verified_pre_result_snapshot(archive, code)
            generated = jst(archive["generated_at_jst"])
            deadline = jst(archive["deadline_jst"])
            source_cards = jst(archive["source_cards_received_jst"])
            source_title = jst(archive["source_title_received_jst"])
            if not (source_cards <= generated and source_title <= generated):
                raise ValueError("source_timestamp_after_forecast_generation")
            digests = archive.get("source_sha256")
            if (type(digests) is not dict or
                    set(digests) != {"race_cards", "title"} or
                    any(type(v) is not str or re.fullmatch(r"[0-9a-f]{64}", v) is None
                        for v in digests.values())):
                raise ValueError("missing_input_source_digest")
            if type(archive.get("validated")) is not bool or archive["validated"] is not False:
                raise ValueError("unfounded_archived_validation_flag")
        except (ValueError, TypeError, KeyError, UnicodeError, OverflowError,
                json.JSONDecodeError) as exc:
            errors.append({"race_code": code or path[:120], "reason": str(exc)[:120]})
            continue
        earned += 1
        before_cutoff += int(generated < deadline - timedelta(minutes=12))
        source_before_generation += 1
        beforeinfo[str(archive.get("beforeinfo", "not_present"))] += 1
        rates_seen.add(tuple(rates))
        for mode in MODES:
            if len(tickets[mode]) != LENGTHS[mode]:
                raise AssertionError("budget_mismatch_after_replay")
            head[mode][tickets[mode][0].split("-")[0]] += 1
    return {
        "schema": "FOUR_MODE_CURRENT_MAIN_DAY_RESULT_BLIND_INPUT_AUDIT_V1",
        "day": day, "pinned_main_commit": commit,
        "source": "git_show_pinned_main_forecast_blobs_only",
        "file_count": len(files), "valid_v2_original_inputs": earned,
        "invalid_inputs": errors, "exact_git_blob_and_original_v2_rank_replay": True,
        "source_cards_and_title_before_generated": source_before_generation,
        "generated_before_deadline_minus_12_min": before_cutoff,
        "generated_before_deadline_but_after_t12": earned - before_cutoff,
        "beforeinfo_flags": dict(beforeinfo),
        "distinct_national_rate_vectors": len(rates_seen),
        "top1_head_counts_original": {mode: dict(head[mode]) for mode in MODES},
        "results_read": False, "outcome_metric_computed": False,
        "candidate_generated_or_modified": False,
        "official_beforeinfo_six_and_odds_120_from_original_verified": False,
        "independent_first_remote_candidate_receipt_verified": False,
        "complete_capture_run_inventory_verified": False,
        "formal": False, "formal_count": 0,
        "model_improvement_proven": False, "model_promotion_allowed": False,
        "warning": "Main original inputs only; no results/candidates, no official T-12, "
                   "no remote first-receipt witness or future paired admission.",
    }


def read_pinned_main(day, ref="refs/remotes/origin/main", cwd=None, git=None):
    if (type(ref) is not str or not SAFE_REF.fullmatch(ref)
            or ref.startswith("-") or ".." in ref
            or type(day) is not str or not re.fullmatch(r"20[0-9]{6}", day)):
        raise ValueError("unsafe_git_ref_or_day")
    def command(args):
        return subprocess.check_output(["git", *args], cwd=cwd, timeout=40)
    git = git or command
    commit = git(["rev-parse", "--verify", ref + "^{commit}"]).decode().strip()
    if not COMMIT.fullmatch(commit):
        raise ValueError("not_sha1_git_commit")
    tree = git(["ls-tree", "-r", "-z", commit, "--", "four_mode_forecasts/"])
    entries = []
    for record in tree.split(b"\0"):
        if not record:
            continue
        meta, path_raw = record.split(b"\t", 1)
        parts = meta.decode("ascii").split(" ")
        path = path_raw.decode("utf-8")
        if not RACE_FILE.fullmatch(path) or RACE_FILE.fullmatch(path).group(1)[:8] != day:
            continue
        if len(parts) != 3 or parts[0] != "100644" or parts[1] != "blob":
            raise ValueError("non_regular_original_file")
        raw = git(["show", commit + ":" + path])
        entries.append((path, parts[2], raw))
    return review_snapshot(entries, day, commit)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--day", default="20261109")
    p.add_argument("--git-ref", default="refs/remotes/origin/main")
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    report = read_pinned_main(a.day, a.git_ref)
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if a.output:
        a.output.write_text(payload, encoding="utf-8")
    print("FOUR_MODE_FUTURE_ORIGINAL_INPUT_READINESS=" + json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
