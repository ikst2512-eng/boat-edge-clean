"""Research-only independent three-original racecard, beforeinfo and odds audit.

Completeness is NOT certification of final race entry or forecast usability.
"""
from datetime import datetime, timedelta
from scripts.audit_joint_official_receipts import audit_pair
from scripts.audit_official_racelist_receipt import audit_racelist_with_official_deadline


def audit_three_originals(racelist_dir, beforeinfo_dir, odds_dir):
    """Fail closed unless every original agrees on the race and official cutoff."""
    pair = audit_pair(beforeinfo_dir, odds_dir)
    card = audit_racelist_with_official_deadline(
        racelist_dir, beforeinfo_dir, pair["race_code"]
    )
    if card["race_code"] != pair["race_code"]:
        raise ValueError("three-source race identity mismatch")
    if card["official_deadline_jst"] != (
        datetime.fromisoformat(pair["cutoff_jst"]) + timedelta(minutes=12)
    ).isoformat():
        raise ValueError("three-source deadline mismatch")
    component_checks = {
        "racecard_original_hash_verified": bool(card["original_hash_verified"]),
        "racecard_six_registrations": bool(card["six_racers_verified"]),
        "racer_registration_ids_match": bool(card["racer_registration_identities_agree"]),
        "racecard_received_by_t12": bool(card["received_by_t12"]),
        "beforeinfo_received_by_t12": bool(card["beforeinfo_received_by_t12"]),
        "beforeinfo_six_unique_boats": bool(pair["component_checks"]["six_unique_boats"]),
        "exhibition_six_courses": len(card["exhibition_course_to_boat"]) == 6,
        "exhibition_times_six": bool(pair["component_checks"]["exhibition_time_six"]),
        "tilt_six": bool(pair["component_checks"]["tilt_six"]),
        "start_exhibition_six": bool(pair["component_checks"]["start_exhibition_six"]),
        "odds_120": bool(pair["component_checks"]["official_odds_120"]),
        "odds_received_by_t12": bool(pair["component_checks"]["odds_received_by_t12"]),
    }
    missing = [name for name, passed in component_checks.items() if not passed]
    return {
        "race_code": pair["race_code"],
        "official_deadline_jst": card["official_deadline_jst"],
        "cutoff_jst": pair["cutoff_jst"],
        "racelist_received_jst": card["racelist_received_jst"],
        "beforeinfo_received_jst": card["beforeinfo_received_jst"],
        "odds_received_jst": pair["odds_received_jst"],
        "registrations_by_lane": card["registrations_by_lane"],
        "exhibition_course_to_boat": card["exhibition_course_to_boat"],
        "three_originals_hash_verified": bool(
            card["original_hash_verified"] and pair["originals_hash_verified"]
        ),
        "component_checks": component_checks,
        "missing_components": missing,
        "all_research_components_observed_by_t12": not missing,
        # Exhibition courses do not establish final entry; never open production gate.
        "final_race_entry_verified": False,
        "full_t12_source_certified": False,
        "t12_eligible": False,
        "forecast_usable": False,
    }
