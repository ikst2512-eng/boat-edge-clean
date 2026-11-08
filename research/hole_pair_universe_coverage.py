"""Read-only, strict race-ID coverage audit for new hole-pair research batches.

Counts alone cannot prove that each immutable-main forecast was either frozen
or excluded with an explicit reason. This validator never opens results or
promotes a candidate to formal T-12 eligibility. Its universe is *only* the
explicitly supplied main snapshot, not an exhaustive race-day schedule.
"""
import json
import re
from collections import Counter
from datetime import date

from hole_pair_remote_receipt_evidence import _validate_frozen

RACE = re.compile(r"20[0-9]{10}\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
DAY = re.compile(r"20[0-9]{6}\Z")
EXCLUSION_REASONS = frozenset({
    "after_t_minus_12",
    "source_not_generated_before_freeze",
    "archive_unavailable_or_invalid",
    "invalid_deadline",
    "calculation_crossed_t_minus_12",
})
SCHEMA = "HOLE_PAIR_SOURCE_SNAPSHOT_COVERAGE_V1"

# Closed schema: the future candidate must be exact result-blind freeze()
# output plus the Git blob fingerprint added by the research batch. No
# realized outcome, winner, post-result annotation or arbitrary extension.
FROZEN_REQUIRED_FIELDS = frozenset({
    "schema", "method", "status", "race_code", "model_version",
    "deadline_jst", "t_minus_12_jst", "local_start_jst", "local_finish_jst",
    "source_sha256", "source_git_blob_sha1", "locked_selector_git_blobs",
    "method_source_sha256", "candidates", "candidates_sha256",
    "formal", "prospective_validation", "independent_first_receipt_verified",
    "production_forecast_changed",
})
FROZEN_OPTIONAL_FIELDS = frozenset({"warning"})
FROZEN_WARNING = (
    "Candidate frozen by a local clock only. No independently "
    "verified first receipt; cannot report formal accuracy."
)
LOCKED_SELECTOR_BLOBS = {
    "hole_third_choice_research.py": "579edc1ae846489d447307fbf03b35fc7d4c09b9",
    "hole_pair_diversification_research.py": "56f06c10f6d07e03b2e37624ecf57dc6de7d8748",
    "hole_top5_safe_bundle_research.py": "a43f53d898ac73829e7f2b24f81624d69d26d74a",
    "hole_pair_third_bundle_research.py": "88c4ed506588a24bb593d104b5d0f59c7502d73a",
}


def reject_outcome_contaminated_schema(record):
    if type(record) is not dict or not (
            FROZEN_REQUIRED_FIELDS <= set(record)
            and not set(record) - (FROZEN_REQUIRED_FIELDS | FROZEN_OPTIONAL_FIELDS)):
        raise ValueError("unexpected_frozen_record_fields")
    if (record["model_version"] != "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
            or record["locked_selector_git_blobs"] != LOCKED_SELECTOR_BLOBS
            or ("warning" in record and record["warning"] != FROZEN_WARNING)):
        raise ValueError("untrusted_frozen_record_metadata")
    return True


def race_day(code, expected_day):
    if type(code) is not str or not RACE.fullmatch(code):
        raise ValueError("invalid_race_code")
    if code[:8] != expected_day:
        raise ValueError("race_outside_snapshot_day")
    y, m, d = int(code[:4]), int(code[4:6]), int(code[6:8])
    try:
        date(y, m, d)
    except ValueError as exc:
        raise ValueError("invalid_race_calendar_date") from exc
    if not (1 <= int(code[8:10]) <= 24 and 1 <= int(code[10:12]) <= 12):
        raise ValueError("invalid_venue_or_race_number")
    return code


def reconcile(capture_day, source_main_sha, source_codes, frozen_records,
              excluded_codes):
    """Reconcile exact ID membership, not merely matching aggregate counts."""
    if (type(capture_day) is not str or not DAY.fullmatch(capture_day)
            or capture_day < "20261109"):
        raise ValueError("capture_day_outside_future_protocol")
    if type(source_main_sha) is not str or not SHA40.fullmatch(source_main_sha):
        raise ValueError("missing_immutable_main_snapshot")
    if (type(source_codes) is not list or type(frozen_records) is not list
            or type(excluded_codes) is not dict
            or len(source_codes) > 500 or len(frozen_records) > 500
            or len(set(source_codes)) != len(source_codes)):
        raise ValueError("invalid_or_duplicate_source_inventory")
    source = set(race_day(code, capture_day) for code in source_codes)
    if source_codes != sorted(source):
        raise ValueError("source_inventory_not_canonical_sorted")
    if set(excluded_codes) - EXCLUSION_REASONS:
        raise ValueError("unrecognized_exclusion_reason")
    taken, frozen, exclusion_summary = set(), [], Counter()
    for record in frozen_records:
        reject_outcome_contaminated_schema(record)
        code, cutoff = _validate_frozen(record)
        race_day(code, capture_day)
        sha1 = record.get("source_git_blob_sha1")
        if type(sha1) is not str or not SHA40.fullmatch(sha1):
            raise ValueError("untrusted_original_source_git_blob")
        if code in taken:
            raise ValueError("duplicate_frozen_or_excluded_race")
        taken.add(code)
        frozen.append((cutoff, code))
    for reason, codes in excluded_codes.items():
        if (type(codes) is not list or len(codes) > 500
                or codes != sorted(codes)):
            raise ValueError("noncanonical_exclusion_roster")
        for code in codes:
            race_day(code, capture_day)
            if code in taken:
                raise ValueError("duplicate_frozen_or_excluded_race")
            taken.add(code)
            exclusion_summary[reason] += 1
    if source != taken:
        raise ValueError(
            "source_forecast_race_coverage_mismatch_missing_"
            + str(len(source - taken))
            + "_orphan_" + str(len(taken - source))
        )
    frozen.sort(key=lambda p: (p[0], p[1]))
    if len(frozen) + sum(exclusion_summary.values()) != len(source):
        raise ValueError("source_inventory_count_mismatch")
    return {
        "schema": SCHEMA,
        "capture_day_jst": capture_day,
        "source_main_commit": source_main_sha,
        "snapshot_forecasts_examined": len(source),
        "frozen_locally_unverified": len(frozen),
        "excluded_by_reason": dict(sorted(exclusion_summary.items())),
        "excluded_race_codes_by_reason": {
            key: list(excluded_codes[key]) for key in sorted(excluded_codes)
        },
        "frozen_codes_by_candidate_cutoff_order": [code for _, code in frozen],
        "source_snapshot_race_coverage_complete": True,
        "entire_day_or_official_schedule_complete_verified": False,
        "independent_first_receipt_verified": False,
        "official_t12_complete_verified": False,
        "pilot_formally_eligible": 0,
        "confirmation_formally_eligible": 0,
        "formal": False,
        "production_promotion_allowed": False,
        "warning": (
            "All IDs in one declared immutable main snapshot were classified. "
            "This is not proof that the snapshot covers all races in the day, "
            "that a receiver first accepted any candidate before the official "
            "T-12 cutoff, or that any record is formally eligible."
        ),
    }


def canonical_json(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
