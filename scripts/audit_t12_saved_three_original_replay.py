"""Real GitHub immutable three-official-original replay, research only.

Reads each stored source blob + manifest at a pinned Git commit using
reaudit_external_three_t12. Rejects incomplete/mutated blobs and mismatched
source reports. A stored third-original directory is never a certificate:
even fully complete original data lacks independent model consumption,
first remote forecast acceptance, and final entry attestation.
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from scripts.reaudit_external_three_t12 import reaudit_published

SCHEMA = "T12_PINNED_GITHUB_THREE_ORIGINAL_REPLAY_V1"
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
RACE = re.compile(r"20[0-9]{10}\Z")
OBS = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
JST = timedelta(hours=9)
REQUIRED_FAILURES = (
    "exhibition_six_courses",
    "exhibition_times_six",
    "tilt_six",
    "start_exhibition_six",
)


def _stamp(value, day):
    if not isinstance(value, str):
        raise ValueError("original receipt timestamp missing")
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError as e:
        raise ValueError("invalid original receipt timestamp") from e
    if stamp.utcoffset() != JST or stamp.strftime("%Y%m%d") != day:
        raise ValueError("original receipt timestamp cross-day or not JST")
    return stamp


def classify(data, race, obs_id, commit):
    """Classify *independently replayed* remote originals; never promote."""
    if (not isinstance(data, dict)
            or data.get("race_code") != race or data.get("observation_id") != obs_id
            or data.get("evidence_commit") != commit
            or data.get("status") != "independent_originals_reaudited"
            or data.get("original_files_found") != 6
            or data.get("full_t12_source_certified") is not False
            or data.get("forecast_usable") is not False):
        raise ValueError("untrusted or incomplete three-original remote replay")
    completed = data.get("research_complete")
    missing = data.get("missing_components")
    if (type(completed) is not bool or not isinstance(missing, list)
            or any(not isinstance(s, str) or not s for s in missing)
            or len(set(missing)) != len(missing)
            or completed != (len(missing) == 0)):
        raise ValueError("conflicting source-component completeness")
    day = race[:8]
    cutoff = _stamp(data.get("cutoff_jst"), day)
    receipt = _stamp(data.get("latest_original_received_jst"), day)
    margin = data.get("t12_receipt_margin_seconds")
    if (type(margin) not in (int, float)
            or not (-10**7 < margin < 10**7)
            or abs(margin - (cutoff-receipt).total_seconds()) > 0.001):
        raise ValueError("remote original timing margin mismatch")
    return {
        "schema": SCHEMA,
        "race_code": race,
        "observation_id": obs_id,
        "source_git_commit_sha": commit,
        "source_git_blob_and_manifest_hashes_reaudited": True,
        "three_official_original_files_present": True,
        "source_received_by_t12": receipt <= cutoff,
        "source_cutoff_jst": cutoff.isoformat(),
        "last_original_received_jst": receipt.isoformat(),
        "original_receipt_margin_seconds": round(margin, 3),
        "six_registration_and_exhibition_components_complete": completed,
        "missing_source_components": sorted(missing),
        "source_research_components_complete": completed,
        "qualified_three_source_candidates": int(completed and receipt <= cutoff),
        "model_original_bytes_consumption_independently_verified": False,
        "independent_first_forecast_git_remote_acceptance_verified": False,
        "final_entry_independently_verified": False,
        "new_formal_certifications": 0,
        "formal_accuracy_denominator": None,
        "formal": False,
        "t12_eligible": False,
        "forecast_usable": False,
        "accuracy_scoring_allowed": False,
        "note": (
            "Pinned original Git blobs were individually SHA-checked and "
            "semantically reaudited. Source receipts are still the original "
            "collector's self-recorded HTTP timestamps. No independent "
            "forecast model-input consumption, first remote acceptance, "
            "or final entry proof. No production/accuracy promotion."),
    }


def audit(repo, token, commit, race, obs_id, *, reauditor=reaudit_published):
    if (not isinstance(repo, str) or not REPO.fullmatch(repo)
            or any(p in (".", "..") for p in repo.split("/"))
            or not isinstance(token, str) or not token
            or not isinstance(commit, str) or not SHA40.fullmatch(commit)
            or not isinstance(race, str) or not RACE.fullmatch(race)
            or not 1 <= int(race[8:10]) <= 24
            or not 1 <= int(race[10:12]) <= 12
            or not isinstance(obs_id, str) or not OBS.fullmatch(obs_id)):
        raise ValueError("invalid pinned repository/observation identity or credentials")
    try:
        datetime.strptime(race[:8], "%Y%m%d")
    except ValueError as e:
        raise ValueError("invalid race calendar date") from e
    data = reauditor(repo, token, commit, race, obs_id)
    return classify(data, race, obs_id, commit)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--git-commit", required=True)
    p.add_argument("--race-code", required=True)
    p.add_argument("--observation-id", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = audit(a.repo, os.environ.get("GITHUB_TOKEN"),
                   a.git_commit, a.race_code, a.observation_id)
    file = Path(a.output)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print("T12_PINNED_THREE_ORIGINAL_REPLAY=" +
          json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
