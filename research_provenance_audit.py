"""Audit a pre-race research prediction envelope without trusting its timestamps alone.

This module only validates metadata and digests. Independent Git first-seen
history or a trusted append-only service must establish actual pre-cutoff
existence before a forecast may be counted as prospective.
"""
import hashlib
import json
import re
from datetime import datetime

SHA = re.compile(r"^[0-9a-f]{40,64}$")
RACE = re.compile(r"^20[0-9]{10}$")


def canonical_digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def audit_envelope(envelope):
    """Returns audit status; never labels self-reported evidence 'verified'."""
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be object")
    race = envelope.get("race_code")
    if not isinstance(race, str) or not RACE.fullmatch(race):
        raise ValueError("invalid race code")
    for field in ("baseline", "candidate"):
        record = envelope.get(field)
        if not isinstance(record, dict):
            raise ValueError(f"{field} missing")
        if not isinstance(record.get("model_sha"), str) or not SHA.fullmatch(record["model_sha"]):
            raise ValueError(f"{field} model_sha invalid")
        if not isinstance(record.get("input_sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", record["input_sha256"]):
            raise ValueError(f"{field} input digest invalid")
        if not isinstance(record.get("probabilities"), dict):
            raise ValueError(f"{field} probabilities missing")
        if record.get("probabilities_sha256") != canonical_digest(record["probabilities"]):
            raise ValueError(f"{field} probability digest mismatch")
        issued = datetime.fromisoformat(record["generated_at"])
        source = datetime.fromisoformat(record["source_received_at"])
        cutoff = datetime.fromisoformat(envelope["cutoff_jst"])
        if any(t.tzinfo is None or t.utcoffset() is None for t in (issued, source, cutoff)):
            raise ValueError("naive timestamp")
        if source > issued or issued >= cutoff:
            raise ValueError("late source or forecast")
    return {"race_code": race, "metadata_consistent": True,
            "prospective_verified": False,
            "reason": "independent immutable first-seen evidence not supplied"}


def make_comparison(envelope):
    """Constructs a paired-evaluation row; does not mark it eligible for scoring."""
    status = audit_envelope(envelope)
    from research_paired_evaluation import validate
    result = {
        "race_code": envelope["race_code"],
        "generated_at": max(envelope[x]["generated_at"] for x in ("baseline", "candidate")),
        "cutoff_jst": envelope["cutoff_jst"], "actual": envelope["actual"],
        "baseline": envelope["baseline"]["probabilities"],
        "candidate": envelope["candidate"]["probabilities"],
    }
    validate(result)
    return result, status
