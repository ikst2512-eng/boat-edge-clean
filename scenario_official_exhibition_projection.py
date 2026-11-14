"""Research-only adapter for #1693's original-byte semantic replay output.

This module does NOT copy parsers from #1693 or pull official sources.
It accepts an injected, independently maintained raw-replay function and
projects available six-boat *exhibition* features. The replay callback's
success is NOT proof of authenticated HTTP origin, first remote Git receipt,
method consumption, or any effect on predictive accuracy. No official wind,
actual race entry, motor or tide features are invented.
"""
import base64
import binascii
import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from itertools import permutations

CODE = re.compile(r"20[0-9]{10}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
NORMALIZED_FIELDS = frozenset({
    "race_code", "source_sha256", "racelist_registration_ids",
    "beforeinfo_registration_ids", "exhibition_courses",
    "exhibition_times", "exhibition_st", "exhibition_tilts", "odds_3t",
})
REPLAY_STAGES = frozenset({
    "preflight_raw_byte_sha_and_clock_structure",
    "official_racelist_six_registration_parser",
    "official_beforeinfo_six_exhibition_start_parser",
    "official_120_odds_html_parser",
    "declared_normalized_features_match_raw_reparse",
})
BLOCKED = frozenset({
    "result", "finish_order", "winning_ticket", "confirmed_result",
    "confirmed_at_jst", "payout", "winning_combo",
    "post_race_weather", "final_entry_course",
    "production_forecast",
})


def _jst(value):
    if type(value) is not str:
        raise ValueError("invalid_jst_timestamp")
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid_jst_timestamp") from exc
    if dt.utcoffset() != timedelta(hours=9):
        raise ValueError("not_jst_timestamp")
    return dt


def _guard_no_post_result(data):
    if type(data) is dict:
        if set(data) & BLOCKED:
            raise ValueError("forbidden_post_result_or_formal_claim")
        for value in data.values():
            _guard_no_post_result(value)
    elif type(data) is list:
        for item in data:
            _guard_no_post_result(item)


def _values_six(values, low, high, label):
    if (type(values) is not list or len(values) != 6
            or any(type(x) not in (float, int) or not math.isfinite(x)
                   or not low <= x <= high for x in values)):
        raise ValueError("invalid_six_" + label)
    return list(values)


def project_exhibition_research(source_bundle, candidate, replay_callback):
    """Project exactly what the existing raw replay has claimed to parse.

    The callback must be #1693-compatible raw-semantic-replay and is
    deliberately injected so there is no duplicate parser or dependency
    on an unmerged Draft. The callback's authenticity is not certified.
    """
    if (type(source_bundle) is not dict
            or type(candidate) is not dict
            or not callable(replay_callback)):
        raise ValueError("source_candidate_and_raw_replay_required")
    _guard_no_post_result(source_bundle)
    _guard_no_post_result(candidate)
    if source_bundle.get("formal") is True or candidate.get("formal") is True:
        raise ValueError("forged_formal_source_or_candidate")
    if source_bundle.get("schema") != "FOUR_MODE_FUTURE_OFFICIAL_INPUT_LINEAGE_PREFLIGHT_V1":
        raise ValueError("wrong_existing_lineage_contract")
    code = source_bundle.get("race_code")
    if (type(code) is not str or not CODE.fullmatch(code)
            or not 1 <= int(code[8:10]) <= 24
            or not 1 <= int(code[10:12]) <= 12
            or candidate.get("race_code") != code):
        raise ValueError("same_valid_race_identity_required")
    deadline = _jst(source_bundle.get("deadline_jst"))
    created = _jst(candidate.get("generated_at_jst"))
    if (deadline.strftime("%Y%m%d") != code[:8]
            or candidate.get("deadline_jst") != source_bundle["deadline_jst"]
            or not created < deadline - timedelta(minutes=12)):
        raise ValueError("post_t12_or_mismatched_deadline")
    normalized = source_bundle.get("normalized_source_claim")
    if type(normalized) is not dict or set(normalized) != NORMALIZED_FIELDS:
        raise ValueError("unexpected_normalized_source_schema")
    _guard_no_post_result(normalized)
    if normalized["race_code"] != code:
        raise ValueError("normalized_cross_race")
    hashes = normalized["source_sha256"]
    if (type(hashes) is not dict or set(hashes) !=
            {"racelist", "beforeinfo", "odds120"}
            or any(type(v) is not str or not SHA.fullmatch(v)
                   for v in hashes.values())):
        raise ValueError("invalid_official_source_digest_claim")
    if candidate.get("consumed_source_sha256") != hashes:
        raise ValueError("candidate_source_identity_mismatch")
    fingerprint = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if candidate.get("consumed_normalized_claim_sha256") != fingerprint:
        raise ValueError("candidate_feature_identity_mismatch")
    originals = source_bundle.get("originals")
    if type(originals) is not dict or set(originals) != set(hashes):
        raise ValueError("three_originals_required")
    received = []
    for kind in sorted(hashes):
        item = originals[kind]
        if (type(item) is not dict
                or item.get("sha256") != hashes[kind]
                or type(item.get("raw_base64")) is not str):
            raise ValueError("original_digest_or_bytes_missing")
        try:
            raw = base64.b64decode(item["raw_base64"], validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("malformed_original_bytes") from exc
        if not raw or len(raw) > 1_000_000 or hashlib.sha256(raw).hexdigest() != hashes[kind]:
            raise ValueError("original_bytes_do_not_match_claimed_digest")
        when = _jst(item.get("received_at_jst"))
        if not when < deadline - timedelta(minutes=12):
            raise ValueError("source_not_received_before_t12")
        received.append(when)
    if not max(received) < created:
        raise ValueError("forecast_precedes_source_receipt")
    ids = normalized["racelist_registration_ids"]
    if (type(ids) is not list or len(ids) != 6
            or len(set(ids)) != 6
            or any(type(x) is not str or not re.fullmatch(r"[0-9]{4,6}", x)
                   for x in ids)
            or ids != normalized["beforeinfo_registration_ids"]):
        raise ValueError("six_boat_registrations_not_aligned")
    courses = normalized["exhibition_courses"]
    if (type(courses) is not list or
            any(type(x) is not int for x in courses)
            or sorted(courses) != list(range(1, 7))):
        raise ValueError("exhibition_course_not_permutation")
    times = _values_six(normalized["exhibition_times"], 0, 20,
                        "exhibition_time")
    st = _values_six(normalized["exhibition_st"], -1, 2,
                     "exhibition_st")
    tilts = _values_six(normalized["exhibition_tilts"], -5, 5, "tilt")
    odds = normalized["odds_3t"]
    expected_odds = {"-".join(map(str, t)) for t in permutations(range(1, 7), 3)}
    if (type(odds) is not dict or set(odds) != expected_odds
            or any(type(value) not in (int, float)
                   or not math.isfinite(value) or value <= 0
                   for value in odds.values())):
        raise ValueError("odds_120_structurally_missing")

    replay = replay_callback(source_bundle, candidate)
    if (type(replay) is not dict
            or replay.get("schema") != "FOUR_MODE_OFFICIAL_RAW_SEMANTIC_REPLAY_V1"
            or replay.get("race_code") != code
            or replay.get("formal") is not False
            or replay.get("model_promotion_allowed") is not False
            or replay.get("raw_official_provenance_independently_attested") is not False
            or replay.get("actual_model_output_independently_replayed") is not False
            or replay.get("first_remote_candidate_acceptance_independently_verified") is not False
            or replay.get("status") !=
            "raw_bytes_semantically_reparsed_and_declared_features_match_RESEARCH_ONLY"
            or type(replay.get("verified_stages")) is not list
            or not REPLAY_STAGES.issubset(replay["verified_stages"])):
        raise ValueError("incompatible_or_untrusted_replay_response")

    boats = [{
        "boat": i + 1,
        "registration_id": ids[i],
        "exhibition_course_only": courses[i],
        "exhibition_time_s": times[i],
        "exhibition_st_s": st[i],
        "exhibition_tilt": tilts[i],
    } for i in range(6)]
    return {
        "schema": "SCENARIO_EXHIBITION_PROJECTION_RESEARCH_V1",
        "race_code": code,
        "source_sha256": dict(hashes),
        "normalized_source_sha256": fingerprint,
        "exhibition_features_by_boat": boats,
        "exhibition_features_sha256": hashlib.sha256(
            json.dumps(boats, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "structural_source_to_candidate_order": True,
        "structural_raw_semantic_replay_reported": True,
        "missing_research_features": [
            "actual_entry_course", "motor_2ren_pct",
            "wind_speed_mps", "wind_from_true_deg",
            "start_heading_true_deg", "wave_height_cm",
            "tide_station", "tide_height_cm", "tide_phase",
            "two_course_escape_assist_rate", "two_course_wall_rate",
        ],
        "feature_values_imputed": False,
        "exhibition_is_actual_final_entry": False,
        "raw_http_origin_independently_attested": False,
        "replay_callback_authenticity_independently_proven": False,
        "candidate_first_remote_receipt_verified": False,
        "model_consumed_these_features_verified": False,
        "all_scenario_effect_coefficients_calibrated": False,
        "formal": False,
        "accuracy_effect_proven": False,
        "promotion_allowed": False,
        "production_changed": False,
    }
