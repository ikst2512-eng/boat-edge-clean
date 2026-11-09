"""Result-blind read-only publication evidence for a saved four-mode capture log.

A GitHub Actions capture job can be green with ZERO newly published forecasts.
Read a provided exact Actions log and cross-check an alleged publication commit
against a pinned fetched main Git history. This module never downloads results,
writes to a repo, publishes a candidate or certifies remote FIRST receipt.

Logs are merely independently SUPPLIED evidence; the caller must authenticate
their run/job origin and log bytes. Current Git ancestry is NOT immutable
history or a first-remote-receipt witness.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

from four_mode_position_sensitive_forward import CODE, DATE_START, DATE_END
from position_sensitive_append_only_research import _no_duplicate_keys

SCHEMA = "POSITION_SENSITIVE_ORIGINAL_PUBLISH_LOG_FIRST_ADD_V1"
MAIN_REF = "refs/remotes/origin/main"
SOURCE_DIR = "four_mode_forecasts/"
STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z) (.*)$")
SHA = re.compile(r"[0-9a-f]{40}\Z")
PUSH = re.compile(r"Published four-mode commit: ([0-9a-f]{40}) new archives: ([0-9]+)\Z")
ADDED = re.compile(r"A\t(four_mode_forecasts/20[0-9]{10}\.json)\Z")
MAX_LOG_BYTES = 2_000_000
MAX_NEW_FORECASTS = 500
DAY = re.compile(r"20[0-9]{6}\Z")
LABELS = {
    "staging": "Four-mode staging diagnostic: ",
    "published": "Published four-mode commit: ",
    "none": "No new cutoff-safe four-mode candidates",
    "stages": "Four-mode execution stages: ",
    "verdict": "FOUR_MODE_EVIDENCE_VERDICT=",
}


def _json(text, label):
    try:
        obj = json.loads(text, object_pairs_hook=_no_duplicate_keys)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("bad_capture_stdout_json:" + label) from exc
    if type(obj) is not dict:
        raise ValueError("capture_stdout_not_object:" + label)
    return obj


def _events(log):
    if (type(log) is not bytes or not 0 < len(log) <= MAX_LOG_BYTES):
        raise ValueError("capture_job_log_missing_or_oversized")
    try:
        lines = log.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("capture_job_log_not_utf8") from exc
    events = {}
    for line in lines:
        match = STAMP.fullmatch(line)
        if match is None:
            continue
        try:
            when = datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid_log_utc_timestamp") from exc
        if when.utcoffset() != timezone.utc.utcoffset(when):
            raise ValueError("not_utc_actions_log")
        body = match.group(2)
        for label, prefix in LABELS.items():
            if body == prefix or body.startswith(prefix):
                if label in events:
                    raise ValueError("duplicated_capture_stdout_marker:" + label)
                events[label] = (when, body[len(prefix):])
    if not all(label in events for label in ("staging", "stages", "verdict")):
        raise ValueError("capture_stdout_evidence_missing")
    if ("published" in events) == ("none" in events):
        raise ValueError("ambiguous_capture_publication_status")
    order = ["staging", "published" if "published" in events else "none",
             "stages", "verdict"]
    if not all(events[a][0] < events[b][0] for a, b in zip(order, order[1:])):
        raise ValueError("capture_event_time_regression")
    return events


def _pinned_commit_file_additions(git, commit, day):
    tip = git("rev-parse", "--verify", MAIN_REF+"^{commit}").decode().strip()
    if SHA.fullmatch(tip) is None:
        raise ValueError("untrusted_main_snapshot")
    parents = git("rev-list", "--parents", "-n", "1", commit).decode().split()
    if (len(parents) != 2 or parents[0] != commit
            or SHA.fullmatch(parents[1]) is None):
        raise ValueError("capture_publication_not_one_parent_commit")
    try:
        git("merge-base", "--is-ancestor", commit, tip)
    except subprocess.CalledProcessError as exc:
        raise ValueError("capture_publication_not_in_main_history") from exc
    entries = git("diff-tree", "--no-commit-id", "--name-status",
                  "-r", commit).decode().splitlines()
    names = []
    for entry in entries:
        m = ADDED.fullmatch(entry)
        if m is None:
            raise ValueError("capture_publication_contains_other_changes")
        path = m.group(1)
        code = path[len(SOURCE_DIR):-5]
        if CODE.fullmatch(code) is None or code[:8] != day or path in names:
            raise ValueError("foreign_duplicate_or_wrong_day_original_file")
        names.append(path)
    if not 0 < len(names) <= MAX_NEW_FORECASTS:
        raise ValueError("no_valid_new_original_files")
    return tip, parents[1], names


def audit_log(day, run_id, log, git):
    """Return a nonformal audit; requires externally authenticated log input."""
    if (type(day) is not str or DAY.fullmatch(day) is None
            or not DATE_START[:10].replace("-", "") <= day <=
            DATE_END[:10].replace("-", "")
            or type(run_id) is not int or run_id <= 0 or not callable(git)):
        raise ValueError("invalid_forward_day_or_run")
    events = _events(log)
    staging = _json(events["staging"][1], "staging")
    stages = _json(events["stages"][1], "stages")
    verdict = _json(events["verdict"][1], "verdict")
    valid = staging.get("staged_valid")
    untracked = staging.get("new_untracked_json")
    excluded = staging.get("excluded")
    if (type(valid) is not int or type(untracked) is not int
            or not 0 <= valid <= untracked <= MAX_NEW_FORECASTS
            or type(excluded) is not dict or
            any(type(v) is not int or v < 0 for v in excluded.values())
            or stages.get("source_capture") != "success"
            or stages.get("receipt_staging") != "success"
            or verdict.get("schema") != "FOUR_MODE_FINAL_EVIDENCE_VERDICT_V1"
            or verdict.get("status") != "passed"
            or type(verdict.get("detail")) is not dict):
        raise ValueError("untrusted_capture_staging_or_verdict")
    remote_tip, parent, names, commit = None, None, [], None
    if "published" in events:
        m = PUSH.fullmatch(LABELS["published"]+events["published"][1])
        if m is None:
            raise ValueError("malformed_published_commit_stdout")
        commit, number = m.group(1), int(m.group(2))
        if (valid <= 0 or number != valid
                or stages.get("publication") != "pushed_to_main"
                or verdict["detail"].get("status") != "published_with_durable_early_observation"
                or verdict["detail"].get("evidence_required") is not True
                or verdict["detail"].get("published") != valid):
            raise ValueError("published_commit_and_staging_disagree")
        remote_tip, parent, names = _pinned_commit_file_additions(git, commit, day)
        if len(names) != number:
            raise ValueError("actual_main_commit_first_add_count_mismatch")
        label = "original_first_add_in_current_main_history_not_first_remote_receipt"
    else:
        if (valid != 0 or untracked != 0
                or excluded or stages.get("publication") != "no_eligible_candidates"
                or verdict["detail"].get("status") != "no_new_forecasts"
                or verdict["detail"].get("evidence_required") is not False
                or "published" in verdict["detail"]):
            raise ValueError("zero_publication_disagrees_with_staging")
        label = "capture_job_succeeded_with_zero_new_original_forecasts"
    return {
        "schema": SCHEMA,
        "status": label,
        "day_jst": day,
        "run_id": run_id,
        "logged_staged_new_originals": valid,
        "first_added_originals_in_current_main_history": len(names),
        "first_added_paths": names,
        "reported_publication_commit_sha": commit,
        "reported_publication_parent_sha": parent,
        "main_snapshot_sha": remote_tip,
        "job_log_received_from_authentic_run_independently_verified": False,
        "current_main_git_first_add_is_first_remote_receipt": False,
        "capture_success_proves_research_candidate_publication": False,
        "candidate_first_remote_receipts_verified": 0,
        "complete_run_inventory_verified": False,
        "official_T12_beforeinfo_six_odds120_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "Exact original first additions on a current Git main view are "
            "different from independently witnessed FIRST remote receipt. "
            "A supplied capture job log must have independent run/job "
            "identity authentication, and a zero-new job is not a new "
            "prediction publication. No results or candidate scores used."
        ),
    }


def _git(*args):
    return subprocess.check_output(
        ["git", *args], timeout=30, stderr=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--day")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--job-log", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.job_log is None:
        record = {
            "schema": SCHEMA,
            "status": "no_authenticated_capture_job_log_supplied",
            "candidate_first_remote_receipts_verified": 0,
            "formal": False,
            "promotion_allowed": False,
            "production_changed": False,
        }
    else:
        if (args.day is None or args.run_id is None
                or args.job_log.is_symlink() or
                not args.job_log.is_file() or
                args.job_log.stat().st_size > MAX_LOG_BYTES):
            raise ValueError("missing_forward_day_run_id_or_valid_log")
        record = audit_log(
            args.day, args.run_id, args.job_log.read_bytes(), _git)
    raw = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2)+"\n"
    if args.output:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("audit_output_must_not_overwrite")
        args.output.write_text(raw, encoding="utf-8")
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
