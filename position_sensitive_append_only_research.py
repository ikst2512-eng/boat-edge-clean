"""Optional, research-only write-once adapter for the frozen #1698 candidate.

This does not run on any schedule, make network calls, or install a publisher.
All GitHub operations are caller-supplied and MUST target a separately
approved research-only branch, never main or an existing collection ledger.

A create-only/read-back operation protects bytes against accidental overwrite.
It does NOT establish independent first remote receipt or official T-12 proof.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json

from four_mode_position_sensitive_forward import _clock, _verify_snapshot, protocol
from position_sensitive_receipt_intake import git_blob_sha

PROPOSED_LEDGER_BRANCH = "position-sensitive-forward-evidence-ledger"
PRODUCTION_BRANCHES = {"main", "master"}
SCHEMA = "POSITION_SENSITIVE_FORWARD_APPEND_ONLY_RESEARCH_V1"
EXPECTED_SNAPSHOT_KEYS = frozenset({
    "schema", "race_code", "status", "research_only", "formal",
    "production_forecast_changed", "candidate_first_remote_receipt_verified",
    "protocol_git_blob_sha1", "candidate_selector_git_blob_sha1",
    "original_forecast_sha256", "original_generated_at_jst", "deadline_jst",
    "candidate_locally_frozen_at_jst", "baseline", "candidate",
})


def _no_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate_json_key")
        out[k] = v
    return out


def prepare_candidate(original_bytes, candidate_bytes, local_now_jst):
    """Validate all 4 same-race ticket boards before *any* remote operation.

    The local clock enforces a conservative gate, not remote attestation.
    """
    if (type(original_bytes) is not bytes or type(candidate_bytes) is not bytes
            or not 0 < len(original_bytes) <= 30000
            or not 0 < len(candidate_bytes) <= 30000):
        raise ValueError("unsafe_candidate_or_original_size")
    # Explicitly reject JSON with duplicate keys, rather than allowing the
    # last duplicate to overwrite a prediction, timestamp, or status field.
    original = json.loads(original_bytes, object_pairs_hook=_no_duplicate_keys)
    candidate = json.loads(candidate_bytes, object_pairs_hook=_no_duplicate_keys)
    if type(original) is not dict or type(candidate) is not dict:
        raise ValueError("invalid_candidate_json")
    if set(candidate) != EXPECTED_SNAPSHOT_KEYS:
        raise ValueError("unexpected_snapshot_field_or_outcome")
    verified = _verify_snapshot(candidate, original_bytes, protocol())
    now = _clock(local_now_jst)
    frozen = _clock(candidate["candidate_locally_frozen_at_jst"])
    cutoff = verified["deadline"] - timedelta(minutes=12)
    # Freeze, local preflight, then remote create: all strictly before T-12.
    # Local success alone can never establish remote publication chronology.
    if not frozen < now < cutoff:
        raise ValueError("local_publication_window_closed_or_ambiguous")
    code = verified["code"]
    path = f"position_sensitive_research/{code}.json"
    return {
        "schema": SCHEMA,
        "branch": PROPOSED_LEDGER_BRANCH,
        "path": path,
        "race_code": code,
        "original_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "candidate_git_blob_sha1": git_blob_sha(candidate_bytes),
        "cutoff_T_minus_12_jst": cutoff.isoformat(),
        "local_now_jst": now.isoformat(),
        "candidate_bytes": candidate_bytes,
        "candidate_selector_verified": True,
        "remote_receipt_verified": False,
        "formal": False,
        "promotion_allowed": False,
        "production_changed": False,
    }


def publish_write_once(original_bytes, candidate_bytes, local_now_jst,
                       branch, remote_read, remote_create):
    """Optional dependency-injected create-only branch writer.

    CONTRACT for real adapters, NOT verified by this function:
    remote_read(branch, path) -> exact raw bytes or None;
    remote_create(branch, path, bytes) performs atomic *create with no sha*,
    rejects any pre-existing path, and never overwrites/force-pushes.

    Do not use a mutable update_file, an upsert, or main. Even a successful
    write is not a first remote receipt. Remote time is NOT supplied here.
    """
    prepared = prepare_candidate(original_bytes, candidate_bytes, local_now_jst)
    if (type(prepared) is not dict or prepared.get("schema") != SCHEMA
            or prepared.get("branch") != PROPOSED_LEDGER_BRANCH
            or branch != PROPOSED_LEDGER_BRANCH
            or branch in PRODUCTION_BRANCHES
            or type(prepared.get("candidate_bytes")) is not bytes
            or not callable(remote_read) or not callable(remote_create)):
        raise ValueError("unsafe_or_unapproved_research_branch_adapter")
    raw = prepared["candidate_bytes"]
    if (hashlib.sha256(raw).hexdigest() != prepared.get("candidate_sha256")
            or git_blob_sha(raw) != prepared.get("candidate_git_blob_sha1")
            or prepared.get("path") !=
            f"position_sensitive_research/{prepared.get('race_code')}.json"):
        raise ValueError("prepared_bytes_or_path_tampered")
    # Defense in depth: do not quietly allow a stale local preparation to
    # become a valid claim if an adapter doesn't provide an observed time.
    # A real caller must separately attest a server Date before the cutoff.
    path = prepared["path"]
    existing = remote_read(branch, path)
    if existing is None:
        # May fail under concurrency; fail closed rather than using update.
        remote_create(branch, path, raw)
        state = "create_only_storage_call_returned"
    elif type(existing) is bytes and existing == raw:
        state = "identical_candidate_already_present"
    else:
        raise ValueError("immutable_candidate_collision")
    after = remote_read(branch, path)
    if type(after) is not bytes or after != raw:
        raise ValueError("write_once_candidate_readback_mismatch")
    return {
        "schema": SCHEMA,
        "status": state + "_unattested",
        "branch": branch,
        "path": path,
        "race_code": prepared["race_code"],
        "candidate_sha256": prepared["candidate_sha256"],
        "candidate_git_blob_sha1": prepared["candidate_git_blob_sha1"],
        "first_remote_candidate_receipt_verified": False,
        "github_server_observation_verified": False,
        "official_beforeinfo_exhibition_six_odds120_verified": False,
        "actions_run_inventory_complete": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
        "warning": (
            "A create/readback return does not prove remote chronology or "
            "independent first remote receipt. Caller adapters are not "
            "authenticated by this function. No official T12 six/120 "
            "or results were inspected."
        ),
    }


if __name__ == "__main__":
    print(json.dumps({
        "schema": SCHEMA,
        "status": "adapter_uninstalled_no_live_publisher",
        "proposed_research_branch": PROPOSED_LEDGER_BRANCH,
        "actual_candidate_publications": 0,
        "formal": False,
        "promotion_allowed": False,
        "production_changed": False,
    }, sort_keys=True))
