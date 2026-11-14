"""Fail-closed, offline GitHub observation intake for frozen position shadow.

Input HTTP receipts must be externally acquired and independently authenticated.
This module ONLY checks internal agreement of supplied bytes and Date headers.
A GitHub Contents GET observed before cutoff is NOT the FIRST remote receipt.
No result, payout, live capture, publication, or GitHub write is performed.
"""
import base64
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import re

from four_mode_position_sensitive_forward import _verify_snapshot, protocol

JST = timezone(timedelta(hours=9))
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
REPO = "ikst2512-eng/boat-edge-clean"
SCHEMA = "FOUR_MODE_POSITION_SENSITIVE_OFFLINE_RECEIPT_INTAKE_V1"


def git_blob_sha(raw):
    if type(raw) is not bytes or not raw:
        raise ValueError("invalid_blob")
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _observe(proof, expected_bytes, expected_path, latest, earliest):
    """Validate a supplied *example* of a GitHub Contents API response.

    This function cannot authenticate that the supplied response actually
    came from GitHub. An independently executed verifier is required later.
    """
    if (type(proof) is not dict or proof.get("repository") != REPO
            or proof.get("url_path") != expected_path
            or type(proof.get("http_status")) is not int
            or proof["http_status"] != 200
            or proof.get("http_age_header_present") is not False
            or type(proof.get("github_api_date_header")) is not str
            or type(proof.get("github_commit_sha")) is not str
            or SHA40.fullmatch(proof["github_commit_sha"]) is None):
        raise ValueError("untrusted_or_failed_github_observation")
    try:
        date = parsedate_to_datetime(proof["github_api_date_header"])
    except (ValueError, TypeError, IndexError) as exc:
        raise ValueError("invalid_remote_date_header") from exc
    if (date.tzinfo is None or date.utcoffset() != timedelta(0)
            or not earliest < date < latest):
        raise ValueError("remote_observation_not_strictly_in_pre_T12_window")
    payload = proof.get("github_contents_response")
    if (type(payload) is not dict or payload.get("path") != expected_path
            or payload.get("type") != "file" or payload.get("encoding") != "base64"
            or payload.get("sha") != git_blob_sha(expected_bytes)
            or type(payload.get("content")) is not str):
        raise ValueError("remote_response_identity_drift")
    try:
        raw = base64.b64decode("".join(payload["content"].splitlines()), validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("invalid_remote_base64") from exc
    if raw != expected_bytes:
        raise ValueError("remote_body_hash_or_bytes_mismatch")
    return {
        "observed_at_utc": date.isoformat(),
        "github_commit_sha": proof["github_commit_sha"],
        "git_blob_sha1": git_blob_sha(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "within_supplied_observation_time_window": True,
    }


def assess_receipt_readiness(original_bytes, candidate_bytes,
                             original_observation=None, candidate_observation=None):
    """Read-only consistency audit. NEVER returns a formal eligibility claim."""
    if (type(original_bytes) is not bytes or type(candidate_bytes) is not bytes
            or not 0 < len(original_bytes) <= 30000
            or not 0 < len(candidate_bytes) <= 30000):
        raise ValueError("invalid_original_or_candidate_bytes")
    p = protocol()
    s = json.loads(candidate_bytes)
    if type(s) is not dict:
        raise ValueError("invalid_candidate")
    verified = _verify_snapshot(s, original_bytes, p)
    code = verified["code"]
    deadline = verified["deadline"]
    cutoff = deadline - timedelta(minutes=12)
    frozen = datetime.fromisoformat(s["candidate_locally_frozen_at_jst"])
    original_at = datetime.fromisoformat(s["original_generated_at_jst"])
    out = {
        "schema": SCHEMA,
        "status": "local_candidate_valid_external_evidence_missing",
        "race_code": code,
        "deadline_jst": deadline.isoformat(),
        "cutoff_T_minus_12_jst": cutoff.isoformat(),
        "original_forecast_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "candidate_source_blob_verified_against_frozen_selector": True,
        "candidate_local_freeze_before_T12": True,
        "original_remote_observation": None,
        "candidate_remote_observation": None,
        "observations_are_externally_authenticated": False,
        "first_remote_candidate_receipt_verified": False,
        "official_beforeinfo_exhibition_six_odds120_verified": False,
        "complete_actions_run_inventory_verified": False,
        "source_independence_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
    }
    if original_observation is not None:
        out["original_remote_observation"] = _observe(
            original_observation, original_bytes,
            f"four_mode_forecasts/{code}.json",
            frozen.astimezone(timezone.utc),
            original_at.astimezone(timezone.utc))
    if candidate_observation is not None:
        out["candidate_remote_observation"] = _observe(
            candidate_observation, candidate_bytes,
            f"position_sensitive_research/{code}.json",
            cutoff.astimezone(timezone.utc),
            frozen.astimezone(timezone.utc))
    if out["original_remote_observation"] and out["candidate_remote_observation"]:
        out["status"] = "two_supplied_pre_T12_observations_self_consistent_nonformal"
    elif out["original_remote_observation"] or out["candidate_remote_observation"]:
        out["status"] = "one_supplied_pre_T12_observation_incomplete_nonformal"
    out["warning"] = (
        "This validates only caller-supplied GitHub HTTP response consistency. "
        "The responses, GitHub Date headers, commit ancestry, first-add history, "
        "complete run roster, official six/120 and independent results have NOT "
        "been authenticated by this code. Even two early-looking observations "
        "are NOT a first remote receipt. Do not use for 300+300 formal cohort "
        "or production promotion."
    )
    return out


if __name__ == "__main__":
    print(json.dumps({
        "schema": SCHEMA,
        "status": "no_actual_future_candidate_or_remote_observation_supplied",
        "formal": False,
        "verified_future_candidate_receipts": 0,
        "promotion_allowed": False,
        "production_changed": False,
    }, sort_keys=True))
