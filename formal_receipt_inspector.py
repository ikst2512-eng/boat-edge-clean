"""Offline receipt cross-check for candidate bytes. NOT an independent timestamp oracle.

Receipt data MUST be obtained independently by a future trusted integration.
A caller-provided receipt is untrusted. Success NEVER approves Formal Fresh.
No result access, network calls, or production API integration.
"""
import hashlib
import json
from datetime import datetime
from formal_candidate_validator import InvalidCandidate, _timestamp, validate_candidate, SHA256


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidCandidate("duplicate JSON key")
        result[key] = value
    return result


def inspect_receipt(candidate_bytes, receipt):
    if not isinstance(candidate_bytes, bytes) or len(candidate_bytes) > 100_000:
        raise InvalidCandidate("candidate bytes missing or oversized")
    try:
        candidate = json.loads(candidate_bytes.decode("utf-8"), object_pairs_hook=_unique_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(InvalidCandidate("nonfinite JSON")))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise InvalidCandidate("candidate JSON invalid") from exc
    shape = validate_candidate(candidate)
    if not isinstance(receipt, dict):
        raise InvalidCandidate("receipt absent")
    digest = hashlib.sha256(candidate_bytes).hexdigest()
    if receipt.get("artifact_sha256") != digest:
        raise InvalidCandidate("receipt bytes mismatch")
    if receipt.get("race_key") != shape["race_key"]:
        raise InvalidCandidate("receipt race mismatch")
    first_seen = _timestamp(receipt.get("first_seen_at"))
    cutoff = _timestamp(candidate["cutoff_at"])
    if first_seen > cutoff:
        raise InvalidCandidate("receipt after cutoff")
    if not isinstance(receipt.get("repository"), str) or not receipt["repository"]:
        raise InvalidCandidate("receipt origin missing")
    if not isinstance(receipt.get("artifact_commit_sha"), str) or len(receipt["artifact_commit_sha"]) != 40 or any(c not in "0123456789abcdef" for c in receipt["artifact_commit_sha"]):
        raise InvalidCandidate("receipt commit malformed")
    return {"race_key": shape["race_key"], "artifact_sha256": digest,
            "receipt_shape_consistent": True, "independent_receipt_verified": False,
            "formal_approved": False}
