"""Fail-closed research-only join of THREE replayed official originals and frozen forecast.

The CLI replays raw racelist, beforeinfo and odds via existing independent
auditors, hashes their archived original manifests, then compares each frozen
source digest and receipt chronology. Even a fully matched research chain is
NOT independent proof of first GitHub remote acceptance or final race entry.
Never enable formal scoring or production forecasts from this report.
"""
import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

JST = timedelta(hours=9)
SHA = re.compile(r"[a-f0-9]{64}\Z")
COMPONENTS = (
    "racecard_original_hash_verified",
    "racecard_six_registrations",
    "racer_registration_ids_match",
    "racecard_received_by_t12",
    "beforeinfo_received_by_t12",
    "beforeinfo_six_unique_boats",
    "exhibition_six_courses",
    "exhibition_times_six",
    "tilt_six",
    "start_exhibition_six",
    "odds_120",
    "odds_received_by_t12",
)
SOURCE_KEYS = ("racelist", "beforeinfo", "odds")


def _jst(raw, day):
    if not isinstance(raw, str):
        raise ValueError("missing timestamp")
    try:
        value = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if value.utcoffset() != JST or value.strftime("%Y%m%d") != day:
        raise ValueError("non-JST or cross-day timestamp")
    return value


def inspect(three, frozen, original_sha256):
    """Research diagnostics: all checked originals must be provided by raw re-audit."""
    if not isinstance(three, dict) or not isinstance(frozen, dict):
        raise ValueError("three-source audit and frozen forecast must be objects")
    race = three.get("race_code")
    if (not isinstance(race, str) or not re.fullmatch(r"20[0-9]{10}", race)
            or int(race[8:10]) not in range(1, 25)
            or int(race[10:12]) not in range(1, 13)):
        raise ValueError("invalid audited official race")
    if frozen.get("race_code") != race:
        raise ValueError("official three-source and forecast race identity mismatch")
    if not isinstance(original_sha256, dict) or set(original_sha256) != set(SOURCE_KEYS):
        raise ValueError("three independently audited original SHA256 digests required")
    if any(not isinstance(original_sha256[k], str)
           or not SHA.fullmatch(original_sha256[k]) for k in SOURCE_KEYS):
        raise ValueError("invalid original SHA256 digest")
    fields = [frozen[key] for key in ("generated_at", "generated_at_jst")
              if frozen.get(key) is not None]
    if len(fields) != 1:
        raise ValueError("exactly one frozen generation timestamp required")
    day = race[:8]
    generated = _jst(fields[0], day)
    cutoff = _jst(three.get("cutoff_jst"), day)
    official_deadline = _jst(three.get("official_deadline_jst"), day)
    if official_deadline != cutoff + timedelta(minutes=12):
        raise ValueError("official deadline and T12 cutoff mismatch")
    receipts = {key: _jst(three.get(key + "_received_jst"), day)
                for key in SOURCE_KEYS}
    latest = max(receipts.values())
    raw_components = three.get("component_checks")
    components = isinstance(raw_components, dict) and all(
        raw_components.get(key) is True for key in COMPONENTS
    )
    all_originals_before_t12 = all(value <= cutoff for value in receipts.values())
    hash_verified = three.get("three_originals_hash_verified") is True
    official_source_kind = frozen.get("input_source_kind") == "official_three_originals"
    forecast_hashes = frozen.get("official_original_sha256")
    lineage_matches = (official_source_kind and isinstance(forecast_hashes, dict)
                       and set(forecast_hashes) == set(SOURCE_KEYS)
                       and all(forecast_hashes[key] == original_sha256[key]
                               for key in SOURCE_KEYS))
    generated_after_raw_sources = generated > latest
    forecast_before_t12 = generated <= cutoff
    missing = []
    if not hash_verified:
        missing.append("three_originals_hash_not_verified")
    if not components:
        missing.append("official_three_original_component_evidence_incomplete")
    if not all_originals_before_t12:
        missing.append("official_three_original_receipt_after_t12")
    if not generated_after_raw_sources:
        missing.append("frozen_forecast_not_generated_strictly_after_all_three_sources")
    if not forecast_before_t12:
        missing.append("frozen_forecast_after_t12")
    if not lineage_matches:
        missing.append("frozen_forecast_not_sha_linked_to_three_official_originals")
    # Archive readback, git commit timestamps and a self-reported first_seen
    # cannot prove externally observed initial GitHub remote acceptance.
    missing.extend((
        "independent_first_git_remote_receipt_unverified",
        "final_race_entry_not_independently_verified",
    ))
    research_chain_ready = all((
        hash_verified, components, all_originals_before_t12,
        generated_after_raw_sources, forecast_before_t12, lineage_matches,
        three.get("all_research_components_observed_by_t12") is True,
    ))
    return {
        "race_code": race,
        "official_deadline_jst": official_deadline.isoformat(),
        "official_t12_cutoff_jst": cutoff.isoformat(),
        "official_original_receipts_jst": {k: v.isoformat() for k, v in receipts.items()},
        "latest_official_original_received_jst": latest.isoformat(),
        "frozen_generated_at_jst": generated.isoformat(),
        "source_to_forecast_margin_seconds": round((generated-latest).total_seconds(), 3),
        "forecast_to_t12_margin_seconds": round((cutoff-generated).total_seconds(), 3),
        "all_three_original_hashes_verified": hash_verified,
        "all_twelve_official_components_verified": bool(components),
        "all_three_originals_received_by_t12": all_originals_before_t12,
        "forecast_generated_after_all_three_originals": generated_after_raw_sources,
        "forecast_generated_by_t12": forecast_before_t12,
        "forecast_source_kind": frozen.get("input_source_kind"),
        "frozen_forecast_original_hashes_match": bool(lineage_matches),
        "research_only_three_source_forecast_chain_ready": bool(research_chain_ready),
        "missing_requirements": missing,
        "independent_first_git_remote_receipt_verified": False,
        "final_race_entry_verified": False,
        "full_t12_source_certified": False,
        "formal": False,
        "t12_eligible": False,
        "forecast_usable": False,
        "accuracy_scoring_allowed": False,
        "scope": "three_originals_replayed_via_immutable_manifests_research_only",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--racelist-dir", required=True)
    parser.add_argument("--beforeinfo-dir", required=True)
    parser.add_argument("--odds-dir", required=True)
    parser.add_argument("--frozen-forecast", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    from scripts.audit_three_official_t12_originals import audit_three_originals
    three = audit_three_originals(
        args.racelist_dir, args.beforeinfo_dir, args.odds_dir
    )
    sha = {
        "racelist": json.loads((Path(args.racelist_dir) / "manifest.json").read_text(
            encoding="utf-8"))["sha256"],
        "beforeinfo": json.loads((Path(args.beforeinfo_dir) / "manifest.json").read_text(
            encoding="utf-8"))["sha256"],
        "odds": json.loads((Path(args.odds_dir) / "manifest.json").read_text(
            encoding="utf-8"))["sha256"],
    }
    forecast = json.loads(Path(args.frozen_forecast).read_text(encoding="utf-8"))
    report = inspect(three, forecast, sha)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("T12_THREE_ORIGINAL_FROZEN=" + json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
