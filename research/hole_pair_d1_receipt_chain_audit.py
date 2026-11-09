"""Audit a candidate/D1-receipt correspondence without granting formal status.

Research-only, no network, source/results reads, deployments or GitHub writes.
A self-reported D1 receipt can prove neither provider authenticity nor original
first external receipt. Candidate-declared cutoff is NOT an official deadline.
This module is intentionally incapable of declaring an eligible formal race.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re

from hole_pair_remote_receipt_evidence import _validate_frozen, canonical_bytes

RECEIPT_SCHEMA = "HOLE_PAIR_D1_FIRST_ACCEPTANCE_V1"
UTC = timezone.utc
FIELDS = frozenset({
    "schema", "race_code", "candidate_sha256", "declared_cutoff_utc",
    "first_received_at_utc", "already_recorded", "timestamp_origin",
    "independent_server_acceptance_observed",
    "independent_first_receipt_verified", "official_t12_complete_verified",
    "formal", "production_promotion_allowed", "warning",
})
TIMESTAMP_ORIGIN = "D1 SQLite server clock at successful immutable insertion"
# The Worker serializes both cutoff_utc and D1 SQLite's first clock as .mmmZ.
# A textually different value may be a forged/reformatted receipt claim.
D1_UTC_DATE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\Z")
WORKER_WARNING = (
    "D1 first-insert time is not an independently signed external witness "
    "or official deadline certification."
)
WORKER_REQUIRED_CANDIDATE_KEYS = frozenset({
    "schema", "method", "status", "race_code", "model_version",
    "deadline_jst", "t_minus_12_jst", "local_start_jst", "local_finish_jst",
    "source_sha256", "source_git_blob_sha1", "locked_selector_git_blobs",
    "method_source_sha256", "candidates", "candidates_sha256",
    "formal", "prospective_validation", "independent_first_receipt_verified",
    "production_forecast_changed",
})
WORKER_MODEL_VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
WORKER_LOCKED_SELECTOR_BLOBS = {
    "hole_third_choice_research.py": "579edc1ae846489d447307fbf03b35fc7d4c09b9",
    "hole_pair_diversification_research.py": "56f06c10f6d07e03b2e37624ecf57dc6de7d8748",
    "hole_top5_safe_bundle_research.py": "a43f53d898ac73829e7f2b24f81624d69d26d74a",
    "hole_pair_third_bundle_research.py": "88c4ed506588a24bb593d104b5d0f59c7502d73a",
}
WORKER_FROZEN_WARNING = (
    "Candidate frozen by a local clock only. No independently verified "
    "first receipt; cannot report formal accuracy."
)
GIT_BLOB_SHA1 = re.compile(r"[0-9a-f]{40}\Z")


def _enforce_worker_candidate_contract(record):
    """Reject records that the exact pinned Worker could not have accepted.

    This validates *claims and shape*, not actual Git source authenticity.
    """
    if type(record) is not dict or not (
            set(record) == WORKER_REQUIRED_CANDIDATE_KEYS or
            set(record) == WORKER_REQUIRED_CANDIDATE_KEYS | {"warning"}):
        raise ValueError("candidate_not_accepted_by_worker_contract")
    blob = record["source_git_blob_sha1"]
    if (type(blob) is not str or not GIT_BLOB_SHA1.fullmatch(blob)
            or record["model_version"] != WORKER_MODEL_VERSION
            or type(record["locked_selector_git_blobs"]) is not dict
            or record["locked_selector_git_blobs"] != WORKER_LOCKED_SELECTOR_BLOBS
            or ("warning" in record and
                record["warning"] != WORKER_FROZEN_WARNING)):
        raise ValueError("candidate_not_accepted_by_worker_contract")




def _utc(iso):
    if type(iso) is not str or not D1_UTC_DATE.fullmatch(iso):
        raise ValueError("invalid_claimed_utc_timestamp")
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError as exc:
        raise ValueError("invalid_claimed_utc_timestamp") from exc
    if dt.utcoffset() != timedelta(0):
        raise ValueError("invalid_claimed_utc_timestamp")
    # Require a canonical D1/Worker representation, not just an equivalent
    # offset or a Python-parseable but noncanonical timestamp.
    canonical = dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"
    if iso != canonical:
        raise ValueError("invalid_claimed_utc_timestamp")
    return dt.astimezone(UTC)


def audit_one(record, d1_receipt=None):
    """Validate claimed immutable bytes and chronology, never authentication."""
    code, cutoff = _validate_frozen(record)
    _enforce_worker_candidate_contract(record)
    digest = sha256(canonical_bytes(record)).hexdigest()
    response = {
        "schema": "HOLE_PAIR_D1_RECEIPT_CHAIN_AUDIT_V1",
        "race_code": code,
        "candidate_record_sha256": digest,
        "status": "no_receiver_receipt",
        "claimed_receiver_receipt_consistent": False,
        "receiver_receipt_authenticated": False,
        "independent_first_receipt_verified": False,
        "official_t12_complete_verified": False,
        "original_source_independently_verified": False,
        "formally_eligible": False,
        "formal": False,
        "model_improvement_proven": False,
        "production_promotion_allowed": False,
    }
    if d1_receipt is None:
        return response
    if type(d1_receipt) is not dict or set(d1_receipt) != FIELDS:
        raise ValueError("unknown_receipt_fields_or_forged_proof")
    if (d1_receipt["schema"] != RECEIPT_SCHEMA
            or d1_receipt["race_code"] != code
            or d1_receipt["candidate_sha256"] != digest
            or d1_receipt["timestamp_origin"] != TIMESTAMP_ORIGIN
            or type(d1_receipt["already_recorded"]) is not bool
            or d1_receipt["independent_server_acceptance_observed"] is not True
            or d1_receipt["warning"] != WORKER_WARNING
            or any(d1_receipt[key] is not False for key in (
                "independent_first_receipt_verified", "official_t12_complete_verified",
                "formal", "production_promotion_allowed"))):
        raise ValueError("conflicting_d1_receipt_identity_or_claim")
    finish = datetime.fromisoformat(record["local_finish_jst"]).astimezone(UTC)
    first = _utc(d1_receipt["first_received_at_utc"])
    declared = _utc(d1_receipt["declared_cutoff_utc"])
    if declared != cutoff.astimezone(UTC):
        raise ValueError("declared_cutoff_mismatch")
    # Consistency only: a faked provider response can still pass this test.
    # Require conservative margins at both edges; no same-second credit.
    if first <= finish + timedelta(seconds=1):
        raise ValueError("receipt_precedes_candidate_or_same_second")
    if first + timedelta(seconds=2) >= declared:
        raise ValueError("late_or_ambiguous_receiver_receipt")
    response.update({
        "status": "self_reported_d1_timestamp_consistent_not_independent_proof",
        "claimed_receiver_receipt_consistent": True,
        "already_recorded": d1_receipt["already_recorded"],
        "claimed_first_received_at_utc": first.isoformat(),
        "declared_cutoff_utc": declared.isoformat(),
    })
    return response


def audit_batch(records, receipts):
    """Reject duplicate, orphan or invalid records before any outcome lookup."""
    if type(records) is not list or type(receipts) is not dict or len(records) > 500:
        raise ValueError("untrusted_candidate_receipt_batch")
    rows, seen = [], set()
    for record in records:
        code, cutoff = _validate_frozen(record)
        if code in seen:
            raise ValueError("duplicate_frozen_race")
        seen.add(code)
        rows.append((cutoff, code, audit_one(record, receipts.get(code))))
    if any(type(key) is not str for key in receipts) or set(receipts) - seen:
        raise ValueError("orphan_or_invalid_receiver_receipt")
    rows.sort(key=lambda row: (row[0], row[1]))
    return {
        "schema": "HOLE_PAIR_D1_RECEIPT_CHAIN_BATCH_AUDIT_V1",
        "examined": len(rows),
        "self_reported_clock_consistent": sum(
            row[2]["claimed_receiver_receipt_consistent"] for row in rows),
        "missing_receiver_receipt": sum(
            row[2]["status"] == "no_receiver_receipt" for row in rows),
        "independent_first_receipt_verified": 0,
        "official_t12_complete_verified": 0,
        "formally_eligible": 0,
        "formal": False,
        "production_promotion_allowed": False,
        "rows": [row[2] for row in rows],
    }
