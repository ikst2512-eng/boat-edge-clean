"""Structural validation only for *untrusted* formal prediction candidates.

Passing this module NEVER grants formal status, proves provenance, or unlocks results.
No network, filesystem, outcomes, or research model imports.
"""
from datetime import datetime
from itertools import permutations
import math
import re

LEGAL = {"-".join(t) for t in permutations("123456", 3)}
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
RACE = re.compile(r"(20[0-9]{6})-(0[1-9]|1[0-9]|2[0-4])-(0[1-9]|1[0-2])\Z")


class InvalidCandidate(ValueError):
    pass


def _timestamp(value):
    if not isinstance(value, str):
        raise InvalidCandidate("timestamp missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidCandidate("timestamp invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InvalidCandidate("timezone required")
    return parsed


def validate_candidate(candidate):
    """Return validated *shape* (never approval); raise on any malformed content."""
    if not isinstance(candidate, dict):
        raise InvalidCandidate("candidate must be an object")
    key = candidate.get("race_key")
    if not isinstance(key, str) or not RACE.fullmatch(key):
        raise InvalidCandidate("race key invalid")
    try:
        datetime.strptime(key[:8], "%Y%m%d")
    except ValueError as exc:
        raise InvalidCandidate("date invalid") from exc
    if candidate.get("source_kind") != "formal_candidate":
        raise InvalidCandidate("source kind invalid")
    for field in ("model_sha256", "input_sha256"):
        digest = candidate.get(field)
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise InvalidCandidate(field + " invalid")
    git_sha = candidate.get("git_sha")
    if not isinstance(git_sha, str) or not re.fullmatch(r"[a-f0-9]{40}", git_sha):
        raise InvalidCandidate("git sha invalid")
    created = _timestamp(candidate.get("generated_at"))
    cutoff = _timestamp(candidate.get("cutoff_at"))
    deadline = _timestamp(candidate.get("official_deadline_at"))
    if not created < cutoff < deadline:
        raise InvalidCandidate("not frozen before cutoff")
    # Structural safety check only: proof of actual publication and receipt is separate.
    if (deadline - cutoff).total_seconds() < 12 * 60:
        raise InvalidCandidate("cutoff less than 12 minutes before deadline")
    raw = candidate.get("ranked_120")
    if not isinstance(raw, list) or len(raw) != 120:
        raise InvalidCandidate("exactly 120 combinations required")
    seen = set()
    total = 0.0
    prev = float("inf")
    for row in raw:
        if not isinstance(row, dict):
            raise InvalidCandidate("row invalid")
        combo, prob = row.get("combo"), row.get("probability")
        if not isinstance(combo, str) or combo not in LEGAL or combo in seen:
            raise InvalidCandidate("invalid or duplicate combo")
        if type(prob) not in (int, float) or not math.isfinite(prob) or not 0 <= prob <= 1:
            raise InvalidCandidate("probability invalid")
        if prob > prev + 1e-12:
            raise InvalidCandidate("ranking not descending")
        prev = prob
        total += prob
        seen.add(combo)
    if seen != LEGAL or abs(total - 1.0) > 1e-8:
        raise InvalidCandidate("incomplete or non-normalized probabilities")
    return {"race_key": key, "shape_valid": True, "formal_approved": False,
            "independent_receipt_verified": False}
