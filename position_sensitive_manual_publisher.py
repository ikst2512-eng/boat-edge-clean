"""Manually invoked, candidate-only GitHub writer for #1698 Draft.

NEVER scheduled, deployed, or called by CI with --publish. The default CLI
performs no network operations. A manual opt-in still cannot certify the
candidate FIRST remote receipt or any formal hit-rate/ROI improvement.

Writes only the separate position-sensitive evidence ledger. It must never
write to main, update existing bytes, change the frozen selector or touch
production collectors. Caller must review scopes and chronology first.
"""
import argparse
import base64
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
import re
import urllib.error
import urllib.request

from four_mode_position_sensitive_forward import (
    CODE, JST, freeze_candidate,
)
from position_sensitive_append_only_research import (
    PROPOSED_LEDGER_BRANCH, prepare_candidate,
)
from position_sensitive_receipt_intake import git_blob_sha

REPO = "ikst2512-eng/boat-edge-clean"
API = f"https://api.github.com/repos/{REPO}"
SCHEMA = "POSITION_SENSITIVE_MANUAL_RESEARCH_PUBLISHER_V1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
MIN_MARGIN_SECONDS = 90
MAX_BODY = 130000


def _clock_header(headers):
    if type(headers) is not dict:
        raise ValueError("invalid_github_http_headers")
    normalized = {}
    for k, v in headers.items():
        key = k.lower()
        if key in normalized:
            raise ValueError("ambiguous_github_http_header")
        normalized[key] = v
    if "age" in normalized:
        raise ValueError("cached_github_http_not_attestable")
    try:
        stamp = parsedate_to_datetime(normalized["date"])
    except (KeyError, ValueError, TypeError, IndexError) as exc:
        raise ValueError("missing_or_invalid_github_server_date") from exc
    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
        raise ValueError("github_date_not_utc")
    return stamp


def _check_status(response, expected):
    if (type(response) is not tuple or len(response) != 3 or
            type(response[0]) is not int):
        raise ValueError("invalid_github_api_response")
    status, headers, body = response
    if status not in expected:
        raise ValueError(f"github_http_{status}_not_success")
    when = _clock_header(headers)
    if type(body) is not bytes or not 0 < len(body) <= MAX_BODY:
        raise ValueError("github_response_missing_or_oversize")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("github_response_bad_json") from exc
    if type(payload) is not dict:
        raise ValueError("github_response_not_object")
    return when, payload


def _contents(response, path):
    when, data = _check_status(response, {200})
    if (data.get("path") != path or data.get("type") != "file"
            or data.get("encoding") != "base64"
            or type(data.get("content")) is not str):
        raise ValueError("github_contents_path_or_encoding_mismatch")
    try:
        raw = base64.b64decode(
            "".join(data["content"].splitlines()), validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("github_contents_base64_invalid") from exc
    if (not 0 < len(raw) <= 30000 or
            data.get("sha") != git_blob_sha(raw)):
        raise ValueError("github_contents_blob_mismatch")
    return when, raw


def manual_publish_one(code, api_call, local_now):
    """Manual, live-API capable, but NEVER independently first-receipt-attested.

    API operation callable signature: api_call("GET"/"PUT", url, payload_bytes)
    returning (status, headers, body). For GET, payload_bytes is None.

    The source is fetched from a PINNED main commit; the only mutation is
    candidate-only Contents PUT on the distinct evidence branch, with NO
    update SHA. A failed or late response is never recorded as success.
    """
    if (type(code) is not str or CODE.fullmatch(code) is None
            or not code[:8] >= "20261109" or not callable(api_call)
            or not callable(local_now)):
        raise ValueError("invalid_future_race_or_api")
    now = local_now()
    if type(now) is not datetime or now.utcoffset() != timedelta(hours=9):
        raise ValueError("local_clock_must_be_JST")
    if now.strftime("%Y%m%d") > code[:8]:
        raise ValueError("retroactive_race_publication_prohibited")
    original_ref = API + "/git/ref/heads/main"
    ref_date, ref = _check_status(api_call("GET", original_ref, None), {200})
    sha = (ref.get("object") or {}).get("sha")
    if (ref.get("ref") != "refs/heads/main"
            or (ref.get("object") or {}).get("type") != "commit"
            or type(sha) is not str or SHA40.fullmatch(sha) is None):
        raise ValueError("invalid_pinned_main_ref")
    original_path = f"four_mode_forecasts/{code}.json"
    original_url = API + "/contents/" + original_path + "?ref=" + sha
    original_date, original = _contents(
        api_call("GET", original_url, None), original_path)
    if original_date < ref_date:
        raise ValueError("remote_http_observation_clock_reversal")
    # Local freeze after the source fetch and before any candidate write.
    frozen_clock = local_now()
    snapshot = freeze_candidate(original, frozen_clock)
    candidate = (json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                            indent=2) + "\n").encode()
    prepared = prepare_candidate(original, candidate, local_now())
    cutoff = datetime.fromisoformat(prepared["cutoff_T_minus_12_jst"])
    observed = original_date.astimezone(JST)
    if not observed < frozen_clock < cutoff - timedelta(seconds=MIN_MARGIN_SECONDS):
        raise ValueError("original_remote_observation_too_late_or_ambiguous")
    # Pin the separate ledger head BEFORE create, so the new Git commit
    # must have this exact direct parent. A successful 201 is not by itself
    # proof of immutable branch ancestry or first remote receipt.
    ledger_ref_endpoint = API + "/git/ref/heads/" + PROPOSED_LEDGER_BRANCH
    ledger_ref_date, ledger_ref = _check_status(
        api_call("GET", ledger_ref_endpoint, None), {200})
    ledger_object = ledger_ref.get("object")
    ledger_sha_before = (
        ledger_object.get("sha") if type(ledger_object) is dict else None)
    if (ledger_ref.get("ref") != "refs/heads/" + PROPOSED_LEDGER_BRANCH
            or type(ledger_object) is not dict
            or ledger_object.get("type") != "commit"
            or type(ledger_sha_before) is not str
            or SHA40.fullmatch(ledger_sha_before) is None):
        raise ValueError("invalid_research_branch_preflight_ref")
    if (ledger_ref_date < original_date
            or ledger_ref_date.astimezone(JST) >=
            cutoff - timedelta(seconds=MIN_MARGIN_SECONDS)):
        raise ValueError("research_branch_ref_clock_invalid")
    path = prepared["path"]
    target = API + "/contents/" + path + "?ref=" + PROPOSED_LEDGER_BRANCH
    response = api_call("GET", target, None)
    if response[0] == 200:
        existing_date, existing = _contents(response, path)
        if existing != candidate:
            raise ValueError("immutable_candidate_collision")
        # Existence at GET time != first remote receipt. The content might
        # have been added before or after its own T12 deadline.
        raise ValueError("candidate_already_exists_no_new_receipt")
    if response[0] != 404:
        raise ValueError(f"github_preflight_http_{response[0]}_not_missing")
    # An authenticated GitHub 404 response is evidence of temporary absence,
    # never success. Must be timely, then PUT create-only before T12.
    missing_date = _clock_header(response[1]).astimezone(JST)
    if (missing_date < ledger_ref_date.astimezone(JST)
            or missing_date < frozen_clock or missing_date < observed):
        raise ValueError("candidate_absence_server_clock_regressed")
    if missing_date >= cutoff - timedelta(seconds=MIN_MARGIN_SECONDS):
        raise ValueError("candidate_absence_checked_too_late")
    if local_now() >= cutoff - timedelta(seconds=MIN_MARGIN_SECONDS):
        raise ValueError("local_create_window_closed")
    body = json.dumps({
        "message": "data: freeze immutable position-sensitive research candidate",
        "content": base64.b64encode(candidate).decode("ascii"),
        "branch": PROPOSED_LEDGER_BRANCH,
        # INTENTIONALLY no "sha": GitHub Contents API must create, not update.
    }, sort_keys=True).encode()
    write_endpoint = API + "/contents/" + path
    write_date, created = _check_status(
        api_call("PUT", write_endpoint, body), {201})
    if (type(created.get("content")) is not dict
            or created["content"].get("path") != path
            or created["content"].get("sha") != git_blob_sha(candidate)):
        raise ValueError("github_create_response_blob_mismatch")
    commit = created.get("commit")
    if (type(commit) is not dict or type(commit.get("sha")) is not str
            or SHA40.fullmatch(commit["sha"]) is None):
        raise ValueError("github_create_commit_id_missing")
    if write_date.astimezone(JST) <= missing_date:
        raise ValueError("github_create_response_clock_not_after_absence")
    if write_date.astimezone(JST) >= cutoff:
        raise ValueError("github_remote_create_response_after_T12")
    # Bind the exact new commit to the independently read *previous* ledger
    # head. Reject concurrent/mismatched parent, orphan or merge commits.
    metadata_endpoint = API + "/git/commits/" + commit["sha"]
    commit_meta_date, commit_meta = _check_status(
        api_call("GET", metadata_endpoint, None), {200})
    parents = commit_meta.get("parents")
    if (commit_meta.get("sha") != commit["sha"] or
            type(parents) is not list or len(parents) != 1 or
            type(parents[0]) is not dict or
            parents[0].get("sha") != ledger_sha_before):
        raise ValueError("created_commit_not_direct_child_of_ledger_head")
    if (commit_meta_date <= write_date or
            commit_meta_date.astimezone(JST) >= cutoff):
        raise ValueError("created_commit_metadata_clock_invalid")
    # After writing, read back the EXACT commit rather than a mutable branch.
    remote_endpoint = API + "/contents/" + path + "?ref=" + commit["sha"]
    observed_date, remote = _contents(
        api_call("GET", remote_endpoint, None), path)
    if (remote != candidate or observed_date <= commit_meta_date
            or observed_date.astimezone(JST) >= cutoff):
        raise ValueError("github_remote_candidate_not_early_or_byte_mismatch")
    return {
        "schema": SCHEMA,
        "status": "manual_create_and_remote_observation_preT12_nonformal",
        "race_code": code,
        "original_main_commit_sha": sha,
        "research_branch": PROPOSED_LEDGER_BRANCH,
        "candidate_path": path,
        "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
        "candidate_git_blob_sha1": git_blob_sha(candidate),
        "created_commit_sha": commit["sha"],
        "research_head_before_create_sha": ledger_sha_before,
        "created_commit_parent_matches_preflight": True,
        "created_commit_parent_externally_attested": False,
        "github_create_response_date_utc": write_date.isoformat(),
        "created_commit_metadata_date_utc": commit_meta_date.isoformat(),
        "github_observation_date_utc": observed_date.isoformat(),
        "cutoff_T_minus_12_jst": cutoff.isoformat(),
        "candidate_first_remote_receipt_independently_verified": False,
        "complete_run_inventory_verified": False,
        "official_T12_six_boats_120_odds_verified": False,
        "formal": False,
        "promotion_allowed": False,
        "model_improvement_proven": False,
        "production_changed": False,
        "warning": (
            "Manual candidate create + matching remote Contents GET is real "
            "remote existence evidence when executed with authentic API "
            "responses, but is NOT independently witnessed FIRST remote "
            "receipt. Status is never formal, even if HTTP 201."
        ),
    }


def github_api_call(method, url, payload):
    """Constrained token-authenticated GitHub HTTP adapter."""
    if method not in ("GET", "PUT"):
        raise ValueError("invalid_http_method")
    if not url.startswith(API + "/"):
        raise ValueError("outside_fixed_repository")
    if method == "PUT" and not re.fullmatch(
            re.escape(API + "/contents/position_sensitive_research/") +
            r"20[0-9]{10}\.json", url):
        raise ValueError("write_outside_candidate_namespace")
    if method == "GET" and not (
        url == API + "/git/ref/heads/main"
        or url == API + "/git/ref/heads/" + PROPOSED_LEDGER_BRANCH
        or re.fullmatch(
            re.escape(API + "/git/commits/") + r"[0-9a-f]{40}", url)
        or re.fullmatch(
            re.escape(API + "/contents/four_mode_forecasts/") +
            r"20[0-9]{10}\.json\?ref=[0-9a-f]{40}", url)
        or re.fullmatch(
            re.escape(API + "/contents/position_sensitive_research/") +
            r"20[0-9]{10}\.json\?ref=(?:[0-9a-f]{40}|" +
            re.escape(PROPOSED_LEDGER_BRANCH) + r")", url)
    ):
        raise ValueError("read_outside_allowed_namespace")
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError("missing_explicit_GH_TOKEN")
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
        "User-Agent": "boat-edge-manual-position-sensitive-shadow",
    }
    if method == "PUT":
        if type(payload) is not bytes:
            raise ValueError("missing_candidate_payload")
        headers["Content-Type"] = "application/json"
        # Re-validate immutable target branch and no SHA update parameter.
        data = json.loads(payload)
        if (type(data) is not dict
                or set(data) != {"message", "content", "branch"}
                or data.get("branch") != PROPOSED_LEDGER_BRANCH
                or type(data.get("content")) is not str):
            raise ValueError("mutation_not_create_only_on_research_branch")
    req = urllib.request.Request(url, data=payload, method=method,
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            return response.status, dict(response.headers.items()), response.read(MAX_BODY + 1)
    except urllib.error.HTTPError as exc:
        # 403, 404 and 409/422 are NEVER silently treated as a write success.
        return exc.code, dict(exc.headers.items()), exc.read(MAX_BODY + 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--race-code", help="Future immutable original V2 race code")
    p.add_argument("--publish", action="store_true",
                   help="Explicit manual opt-in to candidate-only remote CREATE")
    args = p.parse_args()
    if not args.publish:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "manual_publisher_disabled_no_network",
            "publication_count": 0, "formal": False,
            "promotion_allowed": False, "production_changed": False,
        }, sort_keys=True))
        return
    if not args.race_code:
        raise ValueError("future_race_code_required")
    print(json.dumps(manual_publish_one(
        args.race_code, github_api_call,
        lambda: datetime.now(JST)), sort_keys=True))


if __name__ == "__main__":
    main()
