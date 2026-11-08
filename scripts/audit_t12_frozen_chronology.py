"""Independent read-only chronology join: archived official pair vs immutable forecast.

Input "pair" must be the result of audit_joint_official_receipts.audit_pair,
which replays original bytes, manifests, URLs, race identity, and timestamps.
Chronological ordering is necessary but never sufficient for formal T-12
certification. This script never writes to forecast storage or enables scoring.
"""
import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path


def _jst(value):
    if not isinstance(value, str):
        raise ValueError("missing JST timestamp")
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid JST timestamp") from exc
    if stamp.utcoffset() != timedelta(hours=9):
        raise ValueError("timestamp must have explicit +09:00 offset")
    return stamp


def inspect(pair, frozen):
    """Return source/forecast order diagnostics, never a formal certificate."""
    if not isinstance(pair, dict) or not isinstance(frozen, dict):
        raise ValueError("pair and forecast must be objects")
    race = pair.get("race_code")
    if not isinstance(race, str) or not re.fullmatch(r"20[0-9]{10}", race):
        raise ValueError("invalid audited source race")
    if frozen.get("race_code") != race:
        raise ValueError("frozen forecast and source race identity mismatch")
    generated_fields = [
        frozen[key] for key in ("generated_at", "generated_at_jst")
        if frozen.get(key) is not None
    ]
    if len(generated_fields) != 1:
        raise ValueError("exactly one frozen generation timestamp is required")
    generated = _jst(generated_fields[0])
    cutoff = _jst(pair.get("cutoff_jst"))
    before = _jst(pair.get("before_received_jst"))
    odds = _jst(pair.get("odds_received_jst"))
    if any(stamp.strftime("%Y%m%d") != race[:8]
           for stamp in (generated, cutoff, before, odds)):
        raise ValueError("cross-day original/forecast timestamp")
    last_source = max(before, odds)
    hash_verified = pair.get("originals_hash_verified") is True
    two_sources_complete = pair.get("both_complete_before_t12") is True
    sources_before_t12 = before <= cutoff and odds <= cutoff
    # Same-timestamp evidence cannot establish source-before-generation order.
    # The 2026-11-05 first-commit audit likewise rejects same-second ambiguity.
    generated_after_sources = generated > last_source
    generated_before_t12 = generated <= cutoff

    missing = []
    if not hash_verified:
        missing.append("two_originals_not_hash_verified")
    if not two_sources_complete:
        missing.append("two_originals_incomplete")
    if not sources_before_t12:
        missing.append("official_original_received_after_t12")
    if not generated_after_sources:
        missing.append("official_original_received_after_frozen_forecast")
    if not generated_before_t12:
        missing.append("frozen_forecast_generated_after_t12")
    if frozen.get("beforeinfo") == "optional_not_in_snapshot":
        missing.append("official_beforeinfo_absent_from_frozen_snapshot")
    # Pair evidence never carries an independently verified official racelist.
    # A generation timestamp alone does not prove raw official source linkage,
    # independent first GitHub remote receipt, or final entry declaration.
    missing.extend([
        "official_racelist_original_not_in_two_source_archive",
        "official_originals_not_linked_to_frozen_model_inputs",
        "independent_first_git_remote_receipt_unverified",
        "final_entry_not_verified",
    ])
    return {
        "race_code": race,
        "frozen_generated_jst": generated.isoformat(),
        "official_beforeinfo_received_jst": before.isoformat(),
        "official_odds_received_jst": odds.isoformat(),
        "latest_official_pair_received_jst": last_source.isoformat(),
        "official_t12_cutoff_jst": cutoff.isoformat(),
        "last_source_minus_generation_seconds":
            round((last_source - generated).total_seconds(), 3),
        "source_pair_sha_verified": hash_verified,
        "two_source_complete_before_t12": two_sources_complete,
        "source_receipts_before_t12": sources_before_t12,
        "forecast_generated_after_official_pair": generated_after_sources,
        "forecast_generated_before_t12": generated_before_t12,
        "missing_requirements": missing,
        "formal": False,
        "full_t12_source_certified": False,
        "t12_eligible": False,
        "forecast_usable": False,
        "accuracy_scoring_allowed": False,
        "scope": "independent_two_original_replay_vs_frozen_forecast_only",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-dir", required=True)
    parser.add_argument("--odds-dir", required=True)
    parser.add_argument("--frozen-forecast", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    from scripts.audit_joint_official_receipts import audit_pair
    pair = audit_pair(args.before_dir, args.odds_dir)
    frozen = json.loads(Path(args.frozen_forecast).read_text(encoding="utf-8"))
    result = inspect(pair, frozen)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("T12_FROZEN_CHRONOLOGY=" + json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
