"""Read-only, cross-surface GitHub comment checkpoint of one REAL candidate.

A GitHub-created PR comment before T−12 can be an additional server-dated
public assertion of exact candidate bytes. It is EDITABLE and is NOT the
FIRST remote candidate receipt, even if the comment remains unedited.
No result access, GitHub write, collector, main or production interaction.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

from four_mode_position_sensitive_forward import CODE, _verify_snapshot, protocol
from position_sensitive_receipt_intake import git_blob_sha

REPO = "ikst2512-eng/boat-edge-clean"
ID = 6735313191
RACE = "202611091912"
LEDGER_REF = "refs/remotes/origin/position-sensitive-forward-evidence-ledger"
ORIGINAL_REF = "refs/remotes/origin/main"
PATH = "position_sensitive_research/" + RACE + ".json"
URL = "https://api.github.com/repos/" + REPO + "/issues/comments/" + str(ID)
SCHEMA = "POSITION_SENSITIVE_PUBLIC_COMMENT_CHECKPOINT_V1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")


def _timestamp(value):
    if type(value) is not str:
        raise ValueError("invalid_comment_timestamp")
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_comment_timestamp") from exc
    if when.utcoffset() != timedelta(0):
        raise ValueError("comment_timestamp_not_utc")
    return when


def _get_unique(body, prefix, pattern):
    # Each expected claim must occur once as an entire named Markdown line.
    matches = re.findall(
        r"(?m)^- " + re.escape(prefix) + r": [^\n]*?" +
        re.escape(chr(96)) + r"(" + pattern + r")" +
        re.escape(chr(96)), body)
    if len(matches) != 1:
        raise ValueError("missing_or_duplicate_witness_claim:" + prefix)
    return matches[0]


def audit_public_comment(original_bytes, candidate_bytes, first_add_commit,
                         comment):
    """Validate exact candidate and a caller-supplied GitHub comment payload.

    The caller must authenticate the response independently; this helper does
    not certify comment authenticity or immutability from a JSON fixture.
    """
    if (type(original_bytes) is not bytes or
            type(candidate_bytes) is not bytes or
            not 0 < len(original_bytes) <= 30000 or
            not 0 < len(candidate_bytes) <= 30000 or
            type(first_add_commit) is not str or
            SHA40.fullmatch(first_add_commit) is None):
        raise ValueError("invalid_snapshot_or_first_add")
    try:
        record = json.loads(candidate_bytes)
        if type(record) is not dict or record.get("race_code") != RACE:
            raise ValueError("wrong_research_race")
        checked = _verify_snapshot(record, original_bytes, protocol())
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("candidate_cannot_be_replayed") from exc
    if (type(comment) is not dict or comment.get("id") != ID
            or comment.get("html_url") !=
            "https://github.com/" + REPO +
            "/pull/1698#issuecomment-" + str(ID)
            or type(comment.get("user")) is not dict
            or comment["user"].get("login") != "ikst2512-eng"
            or type(comment.get("body")) is not str
            or not 0 < len(comment["body"]) <= 9000):
        raise ValueError("wrong_witness_comment_identity")
    created = _timestamp(comment.get("created_at"))
    updated = _timestamp(comment.get("updated_at"))
    cutoff = checked["deadline"] - timedelta(minutes=12)
    frozen = datetime.fromisoformat(record["candidate_locally_frozen_at_jst"])
    if (created != updated or
            not frozen < created < cutoff or
            created <= datetime.fromisoformat(record["original_generated_at_jst"])):
        raise ValueError("witness_comment_edited_or_not_strictly_preT12")
    body = comment["body"]
    expected = {
        "Race": RACE,
        "Candidate first-add commit visible on GitHub": first_add_commit,
        "Exact candidate Git blob SHA-1": git_blob_sha(candidate_bytes),
        "Exact candidate bytes SHA-256 (independent Actions replay/observation)":
            hashlib.sha256(candidate_bytes).hexdigest(),
    }
    for prefix, expected_value in expected.items():
        pat = r"20[0-9]{10}" if prefix == "Race" else r"[0-9a-f]{40,64}"
        if _get_unique(body, prefix, pat) != expected_value:
            raise ValueError("comment_body_candidate_digest_or_commit_mismatch")
    source_digests = re.findall(
        r"(?m)^- Original .+ embedded SHA-256: " +
        re.escape(chr(96)) + r"([0-9a-f]{64})" + re.escape(chr(96)), body)
    if (source_digests != [hashlib.sha256(original_bytes).hexdigest()] or
            body.count("position_sensitive_research/" + RACE + ".json") != 1 or
            body.count("2026-11-09T20:26:00+09:00") != 1):
        raise ValueError("comment_body_original_or_path_or_cutoff_mismatch")
    return {
        "schema": SCHEMA,
        "status": "github_public_comment_claim_time_before_T12_nonformal",
        "race_code": RACE,
        "comment_id": ID,
        "comment_created_at_utc": created.isoformat(),
        "comment_last_updated_at_utc": updated.isoformat(),
        "comment_currently_unedited": True,
        "candidate_git_first_add_commit_sha": first_add_commit,
        "candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "candidate_git_blob_sha1": git_blob_sha(candidate_bytes),
        "original_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "T_minus_12_jst": cutoff.isoformat(),
        "comment_is_immutable": False,
        "comment_is_independently_first_remote_candidate_receipt": False,
        "independent_candidate_first_remote_receipts_verified": 0,
        "official_beforeinfo_six_boats_odds120_verified": False,
        "complete_capture_run_inventory_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "GitHub public comment created_at is a server-dated separate "
            "checkpoint of published hash ASSERTIONS, not a cryptographic "
            "witness of actual first remote creation. Comments are editable; "
            "an unedited-on-current-GET status is not immutability. Git first "
            "add and GitHub Contents server observations are also not FIRST "
            "remote receipt. Never enroll as formally eligible."
        ),
    }


def run_git(*args):
    return subprocess.check_output(
        ["git", *args], timeout=30, stderr=subprocess.DEVNULL)


def github_comment_get():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
        "User-Agent": "boat-edge-cross-surface-readonly-comment",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(URL, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            if res.status != 200 or res.headers.get("Age") is not None:
                raise ValueError("untrusted_comment_api_http_or_cache")
            raw = res.read(20000)
            if len(raw) >= 20000:
                raise ValueError("comment_api_response_oversize")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise ValueError("comment_api_http_" + str(exc.code)) from exc


def audit_live():
    if not callable(run_git):
        raise ValueError("invalid_git")
    tip = run_git("rev-parse", "--verify", LEDGER_REF + "^{commit}").decode().strip()
    if SHA40.fullmatch(tip) is None:
        raise ValueError("missing_research_tip")
    # Repeat exact candidate first-add lookup on the separately fetched ledger.
    adds = run_git("log", "--format=%H", "--diff-filter=A",
                   tip, "--", PATH).decode().splitlines()
    if len(adds) != 1 or SHA40.fullmatch(adds[0]) is None:
        raise ValueError("candidate_first_add_missing_or_ambiguous")
    first_add_commit = adds[0]
    exact_first_add = run_git("show", first_add_commit + ":" + PATH)
    current = run_git("show", tip + ":" + PATH)
    if current != exact_first_add:
        raise ValueError("candidate_changed_since_first_add")
    original = run_git(
        "show", ORIGINAL_REF + ":four_mode_forecasts/" + RACE + ".json")
    data = github_comment_get()
    report = audit_public_comment(original, current, first_add_commit, data)
    report["observed_research_branch_tip"] = tip
    report["original_git_reference"] = ORIGINAL_REF
    report["comment_fetched_via_github_api"] = True
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.live:
        result = {
            "schema": SCHEMA,
            "status": "comment_audit_unstarted_no_remote_read",
            "independent_candidate_first_remote_receipts_verified": 0,
            "formal": False, "promotion_allowed": False,
            "production_changed": False,
        }
    else:
        result = audit_live()
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        if args.output.is_symlink() or args.output.exists():
            raise ValueError("output_must_be_new_non_symlink")
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
