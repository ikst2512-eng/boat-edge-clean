"""Nonformal, fail-closed audit of prospective hole-pair remote readback evidence.

A GitHub GET Date header proves neither first remote acceptance nor first
availability, even if the bytes match and the GET is pre-cutoff. No code path
here sets formal or independent_first_receipt_verified to true. The provider's
actual independent, append-only first-acceptance proof and official six-boat
/ 120-odds evidence must be implemented and validated separately.
No network, token, result file, collector or production write is performed.
"""
import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
LOCKED_METHOD_SHA256 = "ea30508cd899b10336754cfeec69c69c73f18e09fba421016d6cddc69b9cabcb"
ARMS = ("baseline", "same_pair_two_thirds", "two_pairs_one_third")
CODE = re.compile(r"20[0-9]{10}\Z")
TICKET = re.compile(r"[1-6]-[1-6]-[1-6]\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
OBSERVATION_KEYS = frozenset({
    "kind", "race_code", "candidate_record_sha256", "remote_bytes",
    "github_blob_sha1", "server_observed_at_utc"
})


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _date_time(value, expected_offset):
    dt = datetime.fromisoformat(value)
    if dt.utcoffset() != expected_offset:
        raise ValueError("clock_timezone_or_format_invalid")
    return dt


def _valid_ticket(ticket):
    return (type(ticket) is str and TICKET.fullmatch(ticket) is not None
            and len(set(ticket.split("-"))) == 3)


def _validate_frozen(record):
    if type(record) is not dict:
        raise ValueError("invalid_frozen_record")
    code = record.get("race_code")
    if type(code) is not str or CODE.fullmatch(code) is None or code[:8] < "20261109":
        raise ValueError("not_future_protocol_eligible")
    try:
        date(int(code[:4]), int(code[4:6]), int(code[6:8]))
        venue, race = int(code[8:10]), int(code[10:12])
        if not 1 <= venue <= 24 or not 1 <= race <= 12:
            raise ValueError("invalid_venue_or_race")
    except ValueError as exc:
        raise ValueError("invalid_race_identity") from exc
    if (record.get("schema") != "HOLE_PAIR_FUTURE_FREEZE_V1"
            or record.get("status") != "locally_frozen_unverified"
            or record.get("method") != "HOLE_PAIR_NOV06_LOCKED_RESEARCH_V1"
            or record.get("method_source_sha256") != LOCKED_METHOD_SHA256
            or any(record.get(k) is not False for k in (
                "formal", "prospective_validation",
                "independent_first_receipt_verified",
                "production_forecast_changed"))):
        raise ValueError("untrusted_candidate_claim_or_method")
    if (type(record.get("source_sha256")) is not str
            or HEX64.fullmatch(record["source_sha256"]) is None):
        raise ValueError("untrusted_original_source_fingerprint")
    choices = record.get("candidates")
    if type(choices) is not dict or set(choices) != set(ARMS):
        raise ValueError("missing_candidate_policy")
    if record.get("candidates_sha256") != hashlib.sha256(
            json.dumps(choices, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")).hexdigest():
        raise ValueError("candidate_digest_mismatch")
    baseline = choices["baseline"]
    if (type(baseline) is not list or len(baseline) != 10
            or len(set(baseline)) != 10 or not all(map(_valid_ticket, baseline))):
        raise ValueError("invalid_baseline_ticket_budget")
    pairs = {tuple(t.split("-")[:2]) for t in baseline}
    for name in ARMS:
        picks = choices[name]
        if (type(picks) is not list or len(picks) != 10 or len(set(picks)) != 10
                or not all(map(_valid_ticket, picks)) or picks[:5] != baseline[:5]
                or not pairs.issubset({tuple(t.split("-")[:2]) for t in picks})):
            raise ValueError("top5_or_pair_coverage_violation")
    start = _date_time(record["local_start_jst"], timedelta(hours=9))
    finish = _date_time(record["local_finish_jst"], timedelta(hours=9))
    cutoff = _date_time(record["t_minus_12_jst"], timedelta(hours=9))
    deadline = _date_time(record["deadline_jst"], timedelta(hours=9))
    if (deadline.date().strftime("%Y%m%d") != code[:8]
            or start > finish or finish >= cutoff
            or cutoff != deadline - timedelta(minutes=12)):
        raise ValueError("candidate_timeline_invalid")
    return code, cutoff


def inspect(record, observation=None):
    """Check recorded bytes/clock only; NEVER infer independent first receipt.

    observation is an untrusted readback *claim* unless a separate verifier
    proves its authenticated server origin. Do not use this for formal scoring.
    """
    code, cutoff = _validate_frozen(record)
    receipt = {
        "schema": "HOLE_PAIR_REMOTE_RECEIPT_OBSERVATION_AUDIT_V1",
        "race_code": code,
        "status": "no_remote_candidate_observation",
        "candidate_record_sha256": hashlib.sha256(canonical_bytes(record)).hexdigest(),
        "candidate_integrity_checked": True,
        "remote_bytes_and_reported_clock_consistent": False,
        "independent_first_receipt_verified": False,
        "official_t12_complete_verified": False,
        "formal": False,
        "production_promotion_allowed": False,
    }
    if observation is None:
        return receipt
    if type(observation) is not dict or set(observation) != OBSERVATION_KEYS:
        raise ValueError("untrusted_observation_fields_or_claim")
    if (observation["kind"] != "github_api_readback_not_first_receipt"
            or observation["race_code"] != code):
        raise ValueError("observation_identity_or_claim_invalid")
    raw = observation["remote_bytes"]
    if type(raw) is not bytes or len(raw) > 100_000 or raw != canonical_bytes(record):
        raise ValueError("remote_candidate_bytes_conflict")
    if (observation["candidate_record_sha256"] != receipt["candidate_record_sha256"]
            or observation["github_blob_sha1"] != hashlib.sha1(
                b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
            ).hexdigest()):
        raise ValueError("remote_sha256_or_git_blob_conflict")
    observed = _date_time(observation["server_observed_at_utc"], timedelta(0))
    # Readback cannot truthfully precede creation of the exact frozen bytes.
    finish = _date_time(record["local_finish_jst"], timedelta(hours=9))
    if observed <= finish + timedelta(seconds=1):
        raise ValueError("reported_observation_precedes_candidate_finish")
    if observed + timedelta(seconds=1) < cutoff:
        receipt["status"] = "pre_t12_readback_consistent_not_first_receipt"
        receipt["remote_bytes_and_reported_clock_consistent"] = True
    else:
        receipt["status"] = "readback_late_or_same_second"
    # Even a valid-looking GitHub server Date is ONLY a later observation.
    # Reported clock is not independently authenticated by this pure function.
    return receipt


def inspect_batch(records, observations):
    """Reject incomplete/duplicate input universe before processing outcomes."""
    if (type(records) is not list or type(observations) is not dict
            or len(records) > 500):
        raise ValueError("untrusted_roster")
    seen = set()
    output = []
    for record in records:
        code, _ = _validate_frozen(record)
        if code in seen:
            raise ValueError("duplicate_frozen_race")
        seen.add(code)
        output.append(inspect(record, observations.get(code)))
    if set(observations) - seen:
        raise ValueError("orphan_remote_observation")
    return {
        "schema": "HOLE_PAIR_REMOTE_RECEIPT_BATCH_AUDIT_V1",
        "examined": len(records),
        "pre_t12_readback_consistent": sum(
            x["remote_bytes_and_reported_clock_consistent"] for x in output),
        "independent_first_receipt_verified": 0,
        "formally_eligible": 0,
        "formal": False,
        "rows": output
    }
