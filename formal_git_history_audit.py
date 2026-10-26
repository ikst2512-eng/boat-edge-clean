"""Offline audit of separately retrieved Git history; cannot certify wall-clock time.

The history MUST be fetched by an independent trusted process, not from the forecast.
Commit author/committer timestamps are forgeable; this function can only flag
inconsistencies and NEVER grant Formal Fresh status.
"""
import re
from formal_candidate_validator import InvalidCandidate, _timestamp


def inspect_git_history(candidate, receipt, history):
    if not isinstance(history, list) or not history:
        raise InvalidCandidate("independent history absent")
    if not isinstance(candidate, dict) or not isinstance(receipt, dict):
        raise InvalidCandidate("candidate or receipt absent")
    path = receipt.get("artifact_path")
    if not isinstance(path, str) or not re.fullmatch(
            r"data/formal_predictions/20\d{6}-(?:0[1-9]|1\d|2[0-4])-(?:0[1-9]|1[0-2])\.json", path):
        raise InvalidCandidate("artifact path invalid")
    if path != f"data/formal_predictions/{candidate.get('race_key')}.json":
        raise InvalidCandidate("artifact path race mismatch")
    seen = set()
    additions = []
    for entry in history:
        if not isinstance(entry, dict):
            raise InvalidCandidate("history entry invalid")
        sha = entry.get("sha")
        action = entry.get("action")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha) or sha in seen:
            raise InvalidCandidate("history sha invalid or repeated")
        seen.add(sha)
        if action not in ("added", "modified", "removed"):
            raise InvalidCandidate("history action invalid")
        if entry.get("path") != path:
            raise InvalidCandidate("history path mismatch")
        if action == "added":
            additions.append(entry)
    if len(additions) != 1:
        raise InvalidCandidate("first addition not unique")
    if history[-1] != additions[0]:
        raise InvalidCandidate("history missing true first-addition boundary")
    if receipt.get("artifact_commit_sha") != additions[0]["sha"]:
        raise InvalidCandidate("receipt commit does not match first addition")
    for entry in history[:-1]:
        if entry["action"] != "added":
            raise InvalidCandidate("artifact mutated or removed")
    # Merely parse timestamps; they cannot prove independent UTC first appearance.
    _timestamp(additions[0].get("committed_at"))
    _timestamp(receipt.get("first_seen_at"))
    return {"history_consistent": True, "trusted_first_seen_proven": False,
            "independent_receipt_verified": False, "formal_approved": False}
