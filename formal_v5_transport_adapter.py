"""Adapter for legacy prospective v5 candidate data; NEVER formal approval.

The v5 capture payload does not carry authenticated model/input digests or a
Git commit identity. Do not invent them or promote its validated=true flag.
"""
from datetime import datetime
import hashlib
import json
import math
from itertools import permutations
from formal_candidate_validator import InvalidCandidate

LEGAL = {"-".join(t) for t in permutations("123456", 3)}


def _unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise InvalidCandidate("duplicate JSON key")
        obj[key] = value
    return obj


def inspect_v5_transport(raw_bytes):
    """Check transport shape, return a non-approvable descriptive summary."""
    if not isinstance(raw_bytes, bytes) or not raw_bytes or len(raw_bytes) > 100000:
        raise InvalidCandidate("invalid candidate length")
    try:
        doc = json.loads(raw_bytes.decode("utf-8"), object_pairs_hook=_unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(InvalidCandidate("nonfinite")))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise InvalidCandidate("invalid transport JSON") from exc
    if not isinstance(doc, dict):
        raise InvalidCandidate("transport not an object")
    code = doc.get("race_code")
    if not isinstance(code, str) or len(code) != 12 or not code.isascii() or not code.isdigit():
        raise InvalidCandidate("race code malformed")
    try:
        datetime.strptime(code[:8], "%Y%m%d")
    except ValueError as exc:
        raise InvalidCandidate("date malformed") from exc
    venue, race = int(code[8:10]), int(code[10:12])
    if not (1 <= venue <= 24 and 1 <= race <= 12):
        raise InvalidCandidate("venue or race malformed")
    probs = doc.get("probabilities")
    if not isinstance(probs, dict) or set(probs) != LEGAL:
        raise InvalidCandidate("120 complete probabilities required")
    if any(type(v) not in (float, int) or not math.isfinite(v) or not 0 <= v <= 1 for v in probs.values()):
        raise InvalidCandidate("invalid probability")
    if abs(math.fsum(probs.values()) - 1) > 1e-8:
        raise InvalidCandidate("probabilities not normalized")
    forbidden = {"freeze_proof", "formal_approved", "model_authenticity_verified",
                 "independent_receipt_verified", "input_provenance_verified",
                 "independent_github_arrival_verified", "result_unlock_token"}
    if any(field in doc for field in forbidden):
        raise InvalidCandidate("untrusted embedded approval or provenance claim")
    return {"race_key": f"{code[:8]}-{venue:02d}-{race:02d}",
            "transport_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "candidate_shape_valid": True, "model_authenticity_verified": False,
            "input_provenance_verified": False, "independent_receipt_verified": False,
            "formal_approved": False}
