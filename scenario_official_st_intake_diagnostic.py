"""Research-only intake diagnostic: full official triple vs frozen #1693 ST syntax.

No forecasts, substitutions, calibration, outcomes, remote writes, or cohort
admission. A complete triple source may still be unusable by a frozen model.
This observation can be run retrospectively; it NEVER grants T-12 eligibility.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta

from scripts.audit_three_official_t12_originals import audit_three_originals
from scenario_future_archived_receipts_to_candidate import _load_receipt

CHECKS = frozenset({
    "racecard_original_hash_verified", "racecard_six_registrations",
    "racer_registration_ids_match", "racecard_received_by_t12",
    "beforeinfo_received_by_t12", "beforeinfo_six_unique_boats",
    "exhibition_six_courses", "exhibition_times_six", "tilt_six",
    "start_exhibition_six", "odds_120", "odds_received_by_t12",
})
# Exact existing frozen #1693 lexical rule; do not edit its model/parser.
NUMERIC_ST = re.compile(r"(?:\.\d{1,2}|\d?\.\d{1,2})\Z")
FLAGGED_ST = re.compile(r"(?:F|L)\.\d{1,2}\Z")
RACE = re.compile(r"20\d{10}\Z")
BOATS = frozenset(str(i) for i in range(1, 7))
JST = timedelta(hours=9)


def _no_duplicate_keys(pairs):
    result = {}
    for key, val in pairs:
        if key in result:
            raise ValueError("duplicate_official_json_key")
        result[key] = val
    return result


def _jst(value):
    if type(value) is not str:
        raise ValueError("missing_archived_jst")
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid_archived_jst") from exc
    if dt.utcoffset() != JST:
        raise ValueError("archived_clock_not_jst")
    return dt


def diagnose_verified_source(audit, raw_beforeinfo, manifest):
    """Inspect ST syntax ONLY after the independent 3-original audit.

    Caller must independently establish the raw triple and manifests. This
    helper checks consistency but cannot authenticate an HTTP first receipt.
    """
    if (type(audit) is not dict or type(raw_beforeinfo) is not bytes
            or type(manifest) is not dict
            or type(audit.get("race_code")) is not str
            or not RACE.fullmatch(audit["race_code"])):
        raise ValueError("invalid_official_intake_contract")
    code = audit["race_code"]
    checks = audit.get("component_checks")
    if (type(checks) is not dict or set(checks) != CHECKS
            or any(type(x) is not bool for x in checks.values())):
        raise ValueError("invalid_official_12_check_contract")
    base = {
        "schema": "FOUR_MODE_OFFICIAL_ST_INPUT_DIAGNOSTIC_V1",
        "race_code": code, "frozen_parser": "1693_raw_semantic_replay",
        "official_source_http_origin_independently_attested": False,
        "official_first_remote_receipt_verified": False,
        "candidate_first_remote_receipt_verified": False,
        "model_executed": False, "candidate_created": False,
        "eligible_for_300_plus_300": False, "formal": False,
        "accuracy_improvement_proven": False, "production_changed": False,
    }
    # Distinguish upstream completeness from frozen model compatibility.
    # Never parse/score an incomplete three-original source as if ST were present.
    missing = sorted(k for k, v in checks.items() if not v)
    source_complete = (not missing and
        audit.get("three_originals_hash_verified") is True and
        audit.get("all_research_components_observed_by_t12") is True and
        audit.get("missing_components") == [] and
        audit.get("final_race_entry_verified") is False and
        audit.get("t12_eligible") is False and
        audit.get("forecast_usable") is False)
    if not source_complete:
        # A source audit claiming completeness while its components disagree
        # is inconsistent, not a candidate for a model test.
        if (audit.get("all_research_components_observed_by_t12") is True
                or audit.get("missing_components") == [] and missing):
            raise ValueError("inconsistent_official_source_completeness")
        return dict(base, classification="three_originals_incomplete",
                    missing_components=missing, source_complete_12_of_12=False,
                    frozen_st_lexically_compatible=None, flagged_st_by_boat={})
    if (manifest.get("race_code") != code or
            type(manifest.get("sha256")) is not str or
            hashlib.sha256(raw_beforeinfo).hexdigest() != manifest["sha256"] or
            manifest.get("bytes") != len(raw_beforeinfo) or
            manifest.get("received_at_jst") != audit.get("beforeinfo_received_jst")):
        raise ValueError("official_beforeinfo_manifest_not_identical")
    cutoff = _jst(audit.get("cutoff_jst"))
    before = _jst(manifest["received_at_jst"])
    latest = _jst(audit.get("latest_original_received_jst"))
    if (not before <= latest < cutoff
            or _jst(audit.get("official_deadline_jst")) - timedelta(minutes=12) != cutoff):
        raise ValueError("official_intake_invalid_T12_source_chronology")
    try:
        data = json.loads(raw_beforeinfo.decode("utf-8"),
                          object_pairs_hook=_no_duplicate_keys,
                          parse_constant=lambda x: (_ for _ in ()).throw(
                              ValueError("nonfinite_official_json")))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("official_beforeinfo_raw_invalid") from exc
    main = data.get("maindata") if type(data) is dict else None
    if (type(main) is not dict or str(main.get("hd")) != code[:8]
            or str(main.get("jcd")).zfill(2) != code[8:10]
            or str(main.get("rno")) != str(int(code[10:]))):
        raise ValueError("official_beforeinfo_wrong_race")
    rows = main.get("sttenjiinfolist")
    if type(rows) is not list or len(rows) != 6:
        raise ValueError("official_intake_start_six_missing")
    by_boat = {}
    courses = {}
    for row in rows:
        if type(row) is not dict:
            raise ValueError("official_intake_start_row_invalid")
        boat, course, raw = str(row.get("teino")), str(row.get("cs")), row.get("st")
        if (boat not in BOATS or boat in by_boat
                or course not in BOATS or course in courses
                or type(raw) is not str):
            raise ValueError("official_intake_start_identity_invalid")
        st = raw.strip()
        if not (NUMERIC_ST.fullmatch(st) or FLAGGED_ST.fullmatch(st)):
            raise ValueError("official_intake_unsupported_start_syntax")
        by_boat[boat] = st
        courses[course] = boat
    if (set(by_boat) != BOATS or set(courses) != BOATS
            or courses != audit.get("exhibition_course_to_boat")):
        raise ValueError("official_intake_start_course_mismatch")
    flags = {boat: by_boat[boat] for boat in sorted(BOATS)
             if FLAGGED_ST.fullmatch(by_boat[boat])}
    ok = not flags
    return dict(base,
                classification=("all_six_numeric_ST_lexically_compatible_only"
                                if ok else "complete_three_originals_F_L_ST_rejected_by_frozen_parser"),
                source_complete_12_of_12=True,
                missing_components=[],
                frozen_st_lexically_compatible=ok,
                flagged_st_by_boat=flags,
                flagged_st_count=len(flags),
                st_lexical_type_by_boat={
                    boat: ("flagged" if boat in flags else "numeric")
                    for boat in sorted(BOATS)},
                warning="Lexical readiness does NOT prove full parser/model success or prospective first receipt.")


def diagnose_archived_triple(card_dir, beforeinfo_dir, odds_dir):
    """Read-only archive audit. All three originals are independently checked."""
    audit = audit_three_originals(card_dir, beforeinfo_dir, odds_dir)
    # This existing loader also binds exact on-disk bytes to SHA/size manifest.
    raw, meta = _load_receipt(beforeinfo_dir, "beforeinfo.json")
    return diagnose_verified_source(audit, raw, meta)


def main():
    parser = argparse.ArgumentParser(description="Read-only official ST intake, no forecasts")
    parser.add_argument("--card-dir", required=True)
    parser.add_argument("--before-dir", required=True)
    parser.add_argument("--odds-dir", required=True)
    args = parser.parse_args()
    report = diagnose_archived_triple(args.card_dir, args.before_dir, args.odds_dir)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
