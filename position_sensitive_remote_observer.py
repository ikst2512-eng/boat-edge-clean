"""Read-only GitHub server-Date witness for an ALREADY published #1698 candidate.

No publication, no schedule, no use of results. GitHub response Date shows
an observation of existence, NOT the first remote receipt. This standalone
tool cannot certify independence, branch history immutability or official T-12.
"""
import argparse
import base64
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

from four_mode_position_sensitive_forward import CODE, _verify_snapshot, protocol
from position_sensitive_receipt_intake import git_blob_sha

SCHEMA = "POSITION_SENSITIVE_REMOTE_HTTP_OBSERVATION_V1"
REPO = "ikst2512-eng/boat-edge-clean"
BRANCH = "position-sensitive-forward-evidence-ledger"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
ROOT_URL = "https://api.github.com/repos/" + REPO
MAX_BODY = 120_000


def _header(headers, name):
    if not hasattr(headers, "items"):
        raise ValueError("malformed_remote_headers")
    matches = [v for k, v in headers.items() if k.lower() == name.lower()]
    if len(matches) > 1:
        raise ValueError("ambiguous_remote_header:" + name)
    return matches[0] if matches else None


def _get_json(fetch, url):
    """Require a real HTTP 200 and an uncached, UTC GitHub server Date header."""
    response = fetch(url)
    if (type(response) is not tuple or len(response) != 3 or
            type(response[0]) is not int or response[0] != 200):
        raise ValueError("github_http_not_200")
    status, headers, raw = response
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BODY:
        raise ValueError("github_remote_response_oversize_or_empty")
    if _header(headers, "Age") is not None:
        raise ValueError("github_cached_response_unattestable")
    stamp = _header(headers, "Date")
    if type(stamp) is not str:
        raise ValueError("github_date_missing")
    try:
        when = parsedate_to_datetime(stamp)
    except (ValueError, TypeError, IndexError) as exc:
        raise ValueError("github_date_invalid") from exc
    if when.tzinfo is None or when.utcoffset() != timedelta(0):
        raise ValueError("github_date_not_utc")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("github_json_invalid") from exc
    if type(data) is not dict:
        raise ValueError("github_json_not_object")
    return when, data


def observe_candidate(code, exact_original_bytes, fetch):
    """Inspect *actual network responses* via injected fetch operation.

    If fetch is mocked, these are synthetic tests, not independent evidence.
    Never infer first-remote-arrival from a single observation or Git commit.
    """
    if (type(code) is not str or CODE.fullmatch(code) is None or
            type(exact_original_bytes) is not bytes or
            not 0 < len(exact_original_bytes) <= 30000 or not callable(fetch)):
        raise ValueError("invalid_observation_inputs")
    ref_url = ROOT_URL + "/git/ref/heads/" + BRANCH
    ref_time, ref = _get_json(fetch, ref_url)
    commit = ref.get("object") if type(ref.get("object")) is dict else {}
    sha = commit.get("sha")
    if (ref.get("ref") != "refs/heads/" + BRANCH or
            commit.get("type") != "commit" or
            type(sha) is not str or SHA40.fullmatch(sha) is None):
        raise ValueError("github_research_ref_invalid")
    path = f"position_sensitive_research/{code}.json"
    contents_url = ROOT_URL + "/contents/" + path + "?ref=" + sha
    when, data = _get_json(fetch, contents_url)
    if (when < ref_time or
            data.get("type") != "file" or data.get("path") != path or
            data.get("encoding") != "base64" or
            type(data.get("content")) is not str):
        raise ValueError("github_candidate_content_identity_invalid")
    try:
        candidate_bytes = base64.b64decode(
            "".join(data["content"].splitlines()), validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("github_candidate_base64_invalid") from exc
    if (not 0 < len(candidate_bytes) <= 30000 or
            data.get("sha") != git_blob_sha(candidate_bytes)):
        raise ValueError("github_candidate_blob_digest_invalid")
    try:
        candidate = json.loads(candidate_bytes)
        if type(candidate) is not dict or candidate.get("race_code") != code:
            raise ValueError("github_candidate_race_mismatch")
        vetted = _verify_snapshot(candidate, exact_original_bytes, protocol())
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ValueError("github_candidate_replay_failed") from exc
    cutoff = vetted["deadline"] - timedelta(minutes=12)
    frozen = datetime.fromisoformat(candidate["candidate_locally_frozen_at_jst"])
    if not frozen < when < cutoff:
        raise ValueError("github_candidate_observation_after_T12_or_before_freeze")
    return {
        "schema": SCHEMA,
        "status": "github_candidate_existing_preT12_observation_not_first_receipt",
        "race_code": code,
        "repository": REPO,
        "branch": BRANCH,
        "observed_branch_commit_sha": sha,
        "candidate_path": path,
        "candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "candidate_git_blob_sha1": git_blob_sha(candidate_bytes),
        "original_forecast_sha256": hashlib.sha256(exact_original_bytes).hexdigest(),
        "server_observed_utc": when.isoformat(),
        "deadline_minus_12_jst": cutoff.isoformat(),
        "within_supplied_server_observation_window": True,
        "independent_candidate_first_remote_receipt_verified": False,
        "original_first_remote_receipt_verified": False,
        "branch_history_rewrite_excluded": False,
        "run_inventory_complete": False,
        "official_beforeinfo_exhibition_six_odds120_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "Live Contents GET/Date only attests observed existence at server "
            "response time, not FIRST remote arrival. Remote branch was read "
            "at a pinned commit. This tool does not prove its independence, "
            "whole-run provenance, original first-add, upstream official six/120, "
            "or confirmed outcome. Never promote from this observation."
        ),
    }


def github_get(url):
    """Exact fixed GitHub API endpoints; network read only."""
    if not (url.startswith(ROOT_URL + "/git/ref/heads/" + BRANCH)
            or url.startswith(ROOT_URL + "/contents/position_sensitive_research/")):
        raise ValueError("unexpected_github_endpoint")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
        "User-Agent": "boat-edge-position-sensitive-read-only",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=12) as res:
            return res.status, dict(res.headers.items()), res.read(MAX_BODY + 1)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), b""


def main():
    p = argparse.ArgumentParser(description="Research-only candidate observation")
    p.add_argument("--code")
    p.add_argument("--original", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.code is None and args.original is None:
        print(json.dumps({
            "schema": SCHEMA, "status": "not_invoked_no_candidate_observation",
            "independent_candidate_first_remote_receipt_verified": False,
            "formal": False, "promotion_allowed": False,
            "production_changed": False,
        }, sort_keys=True))
        return
    if args.code is None or args.original is None:
        raise ValueError("both_race_and_exact_original_required")
    if (args.original.is_symlink() or not args.original.is_file()
            or args.original.stat().st_size > 30000):
        raise ValueError("invalid_original_file")
    record = observe_candidate(args.code, args.original.read_bytes(), github_get)
    raw = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        if args.output.is_symlink():
            raise ValueError("output_symlink_forbidden")
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(raw)
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
