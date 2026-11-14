"""Result-blind, research-only attack -> beneficiary feature matrix (#1708/#1710).

Builds 120 ticket-level interaction covariates from *caller-claimed* pre-deadline
evidence. These are NOT probabilities, scenario weights, verified original data
or permission to change V127/V133/CLEAN production rankings. An independent,
time-proven collector and prospective calibration are still required.
"""
from datetime import datetime, timedelta
from hashlib import sha256
from itertools import permutations
import json
import math
import re

MODEL = "EXPLORATORY_ONLY_ATTACK_BENEFIT_FEATURES_V2"
JST = timedelta(hours=9)
SHA = re.compile(r"^[0-9a-f]{64}$")
RATES = {"motor_2ren_pct", "meeting_2ren_pct", "two_escape_assist_pct",
         "makuri_pct", "makuri_sashi_pct", "sashi_pct"}
SECONDS = {"average_st_s", "meeting_st_s"}
SIGNALS = RATES | SECONDS
# Win-method rates use actual-course starts, NOT shares of winner methods.
# Escape-assist requires a separately declared eligible 2C/1C sample: the
# original vendor's exclusions must be verified before loading any rate.
# 逃がし率 and 逃がし2着率 must never be conflated.
DENOMINATORS = {
    "motor_2ren_pct": "motor_starts",
    "meeting_2ren_pct": "meeting_starts",
    "two_escape_assist_pct": "eligible_course2_1c_escape_trials",
    "makuri_pct": "actual_course_starts",
    "makuri_sashi_pct": "actual_course_starts",
    "sashi_pct": "actual_course_starts",
    "average_st_s": "start_observations",
    "meeting_st_s": "meeting_start_observations",
}
TAGS = {"turn_positive", "turn_negative", "straight_positive",
        "straight_negative", "start_positive", "start_negative"}
BLOCKED = {"result", "payout", "finish_order", "winning_ticket",
           "confirmed_result", "final_entry", "post_race_weather", "outcome"}


def _reject_nested_outcomes(value):
    """Reject post-race payload keys even inside source/feature/comment wrappers.

    Caller-supplied provenance is not independent first-seen proof. Ignoring an
    unknown nested key silently could permit finish-order leakage into a
    subsequently exported research record; reject it before building features.
    """
    if isinstance(value, dict):
        if BLOCKED.intersection(value):
            raise ValueError("nested_post_race_or_final_entry_leakage_denied")
        for child in value.values():
            _reject_nested_outcomes(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_nested_outcomes(child)


def _clock(raw):
    if type(raw) is not str:
        raise ValueError("timestamp_required")
    try:
        value = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("invalid_timestamp") from exc
    if value.utcoffset() != JST:
        raise ValueError("timestamp_must_be_JST")
    return value


def _receipt(source, generated):
    if type(source) is not dict or not {"source_sha256", "received_at_jst", "source_url"} <= set(source):
        raise ValueError("feature_source_receipt_required")
    if (type(source["source_sha256"]) is not str
            or not SHA.fullmatch(source["source_sha256"])
            or type(source["source_url"]) is not str
            or not source["source_url"].startswith(("https://", "http://"))):
        raise ValueError("invalid_feature_provenance")
    if _clock(source["received_at_jst"]) > generated:
        raise ValueError("post_generation_feature_receipt")
    return {k: source[k] for k in ("source_sha256", "received_at_jst", "source_url")}


def _signal(raw, name, generated):
    if raw is None:
        return None
    if (type(raw) is not dict or "value" not in raw or "sample_size" not in raw
            or raw.get("denominator_kind") != DENOMINATORS[name]):
        raise ValueError("numeric_feature_value_and_denominator_kind_required")
    _receipt(raw, generated)
    val, sample = raw["value"], raw["sample_size"]
    if (type(sample) is not int or not 1 <= sample <= 1_000_000
            or type(val) not in (float, int) or not math.isfinite(val)):
        raise ValueError("invalid_numeric_feature_or_sample")
    if name in RATES:
        if not 0 <= val <= 100:
            raise ValueError("rate_out_of_bounds")
        numerator = raw.get("success_count")
        if (type(numerator) is not int or not 0 <= numerator <= sample
                or abs(100.0 * numerator / sample - float(val)) > 0.051):
            raise ValueError("rate_numerator_denominator_inconsistent")
    if name in SECONDS and not 0 <= val <= 0.5:
        raise ValueError("start_out_of_bounds")
    return {"value": float(val) / 100 if name in RATES else float(val),
            "sample_size": sample,
            "denominator_kind": DENOMINATORS[name],
            "success_count": raw["success_count"] if name in RATES else None,
            "source_sha256": raw["source_sha256"]}


def _comment(raw, generated):
    if raw is None:
        return None
    if (type(raw) is not dict or raw.get("annotation_method") != "manual_verified_quote"
            or type(raw.get("quote")) is not str or not raw["quote"].strip()
            or type(raw.get("tags")) is not list or len(raw["tags"]) != len(set(raw["tags"]))
            or set(raw["tags"]) - TAGS):
        raise ValueError("manual_comment_quote_and_allowed_tags_required")
    _receipt(raw, generated)
    return {"tags": sorted(raw["tags"]), "source_sha256": raw["source_sha256"]}


def _rate(rows, course, name):
    signal = rows[course]["signals"].get(name)
    return None if signal is None else signal["value"]


def _interaction(engaged, *values):
    # Zero means the specified position pattern does not occur; None means an
    # engaged pattern lacks its pre-race evidence. Never zero-fill missing data.
    if not engaged:
        return 0.0
    if any(v is None for v in values):
        return None
    result = math.prod(values)
    return round(result, 12)


def _comment_direction(row, kind):
    comment = row["comment"]
    if comment is None:
        return None
    tags = set(comment["tags"])
    return int(kind + "_positive" in tags) - int(kind + "_negative" in tags)


def build_attack_benefit_matrix(record):
    """Enumerate all 120 ordered outcomes with course-aware attack/benefit covariates.

    'Two escape assist' is an escape-assist proxy, NOT a verified wall/block
    probability. Rate products are interaction *features*, NOT probabilities.
    Course numbers are START EXHIBITION positions, NOT later actual entry.
    """
    if type(record) is not dict or record.get("schema") != "SCENARIO_PRE_RACE_FEATURE_CLAIMS_V1":
        raise ValueError("research_record_schema_required")
    _reject_nested_outcomes(record)
    generated = _clock(record.get("generated_at_jst"))
    deadline = _clock(record.get("deadline_at_jst"))
    # Preserve the user's research T-12 boundary. A computed feature vector
    # at T-11 must never be used as an eligible T-12 input in a future study.
    # This is an untrusted caller clock check, not an attested Git receipt.
    if generated >= deadline:
        raise ValueError("post_deadline_recomputation_denied")
    if generated >= deadline - timedelta(minutes=12):
        raise ValueError("post_T12_feature_generation_denied")
    race_code = record.get("race_code")
    if type(race_code) is not str or not re.fullmatch(r"20\d{10}", race_code):
        raise ValueError("race_code_required")
    entry_source = _receipt(record.get("exhibition_entry_source"), generated)
    racers = record.get("racers")
    if type(racers) is not list or len(racers) != 6:
        raise ValueError("six_racers_required")
    by_boat, by_course, feature_sources = {}, {}, {}
    for raw in racers:
        if type(raw) is not dict or BLOCKED.intersection(raw):
            raise ValueError("post_race_racer_data_denied")
        boat, course = raw.get("boat"), raw.get("exhibition_course")
        if (type(boat) is not int or type(course) is not int
                or boat not in range(1, 7) or course not in range(1, 7)
                or boat in by_boat or course in by_course):
            raise ValueError("duplicate_or_invalid_exhibition_course")
        inputs = raw.get("signals")
        if type(inputs) is not dict or set(inputs) - SIGNALS or BLOCKED.intersection(inputs):
            raise ValueError("unregistered_numeric_features_denied")
        signals = {key: _signal(inputs.get(key), key, generated) for key in sorted(SIGNALS)}
        comment = _comment(raw.get("comment"), generated)
        row = {"boat": boat, "course": course, "signals": signals, "comment": comment}
        by_boat[boat] = row
        by_course[course] = row
        feature_sources[str(boat)] = {
            name: item["source_sha256"] for name, item in signals.items() if item is not None
        }
        if comment is not None:
            feature_sources[str(boat)]["comment"] = comment["source_sha256"]
    if set(by_boat) != set(range(1, 7)) or set(by_course) != set(range(1, 7)):
        raise ValueError("incomplete_exhibition_course_permutation")

    # Map all race-specific scenarios by COURSE, not by a fixed boat number.
    c = {course: by_course[course]["boat"] for course in range(1, 7)}
    features = []
    for h, s, t in permutations(range(1, 7), 3):
        head = by_boat[h]
        head_sig = head["signals"]
        vals = {
            "head_motor_2ren": _rate(by_course, head["course"], "motor_2ren_pct"),
            "second_motor_2ren": _rate(by_course, by_boat[s]["course"], "motor_2ren_pct"),
            "third_motor_2ren": _rate(by_course, by_boat[t]["course"], "motor_2ren_pct"),
            "head_meeting_2ren": _rate(by_course, head["course"], "meeting_2ren_pct"),
            "second_meeting_2ren": _rate(by_course, by_boat[s]["course"], "meeting_2ren_pct"),
            "third_meeting_2ren": _rate(by_course, by_boat[t]["course"], "meeting_2ren_pct"),
            "head_average_st_s": _rate(by_course, head["course"], "average_st_s"),
            "head_meeting_st_s": _rate(by_course, head["course"], "meeting_st_s"),
            "head_comment_turn": _comment_direction(head, "turn"),
            "second_comment_turn": _comment_direction(by_boat[s], "turn"),
            "third_comment_turn": _comment_direction(by_boat[t], "turn"),
            "head_comment_straight": _comment_direction(head, "straight"),
            "second_comment_straight": _comment_direction(by_boat[s], "straight"),
            "third_comment_straight": _comment_direction(by_boat[t], "straight"),
            "head_comment_start": _comment_direction(head, "start"),
            "escape_two_escape_assist_proxy": _interaction(
                h == c[1], _rate(by_course, 2, "two_escape_assist_pct")),
            "two_sashi_head": _interaction(h == c[2], _rate(by_course, 2, "sashi_pct")),
            "third_makuri_head": _interaction(h == c[3], _rate(by_course, 3, "makuri_pct")),
            "third_makuri_sashi_head": _interaction(
                h == c[3], _rate(by_course, 3, "makuri_sashi_pct")),
            "third_attack_four_sashi_head": _interaction(
                h == c[4] and s == c[3],
                _rate(by_course, 3, "makuri_pct"), _rate(by_course, 4, "sashi_pct")),
            "third_attack_five_makuri_sashi_head": _interaction(
                h == c[5] and s == c[3],
                _rate(by_course, 3, "makuri_pct"), _rate(by_course, 5, "makuri_sashi_pct")),
            "third_attack_four_sashi_second": _interaction(
                h == c[3] and s == c[4],
                _rate(by_course, 3, "makuri_pct"), _rate(by_course, 4, "sashi_pct")),
            "third_attack_five_makuri_sashi_second": _interaction(
                h == c[3] and s == c[5],
                _rate(by_course, 3, "makuri_pct"), _rate(by_course, 5, "makuri_sashi_pct")),
            "third_attack_five_makuri_sashi_third": _interaction(
                h == c[3] and t == c[5],
                _rate(by_course, 3, "makuri_pct"), _rate(by_course, 5, "makuri_sashi_pct")),
            "third_attack_two_escape_assist_obstacle_proxy": _interaction(
                h == c[3], _rate(by_course, 3, "makuri_pct"),
                _rate(by_course, 2, "two_escape_assist_pct")),
            # Compound 2C escape-assist x 3C attack x 4C/5C benefit.
            # Signs are NOT predetermined: a high escape-assist rate may
            # obstruct a 3C attack, but it can also leave a sashi gap.
            # These are interaction covariates, not hit probabilities.
            "one_survives_three_attack_four_sashi_second": _interaction(
                h == c[1] and s == c[4],
                _rate(by_course, 2, "two_escape_assist_pct"),
                _rate(by_course, 3, "makuri_pct"),
                _rate(by_course, 4, "sashi_pct")),
            "three_attacks_two_escape_assist_four_second": _interaction(
                h == c[3] and s == c[4],
                _rate(by_course, 2, "two_escape_assist_pct"),
                _rate(by_course, 3, "makuri_pct"),
                _rate(by_course, 4, "sashi_pct")),
            "three_attacks_two_escape_assist_five_second": _interaction(
                h == c[3] and s == c[5],
                _rate(by_course, 2, "two_escape_assist_pct"),
                _rate(by_course, 3, "makuri_pct"),
                _rate(by_course, 5, "makuri_sashi_pct")),
            "third_attack_four_sashi_third": _interaction(
                h == c[3] and t == c[4],
                _rate(by_course, 3, "makuri_pct"),
                _rate(by_course, 4, "sashi_pct")),
            "fourth_attack_five_makuri_sashi_third": _interaction(
                h == c[4] and t == c[5],
                _rate(by_course, 4, "makuri_pct"),
                _rate(by_course, 5, "makuri_sashi_pct")),
            "fourth_attack_six_makuri_sashi_third": _interaction(
                h == c[4] and t == c[6],
                _rate(by_course, 4, "makuri_pct"),
                _rate(by_course, 6, "makuri_sashi_pct")),
            "fourth_attack_five_makuri_sashi_second": _interaction(
                h == c[4] and s == c[5],
                _rate(by_course, 4, "makuri_pct"), _rate(by_course, 5, "makuri_sashi_pct")),
            "fourth_attack_six_makuri_sashi_second": _interaction(
                h == c[4] and s == c[6],
                _rate(by_course, 4, "makuri_pct"), _rate(by_course, 6, "makuri_sashi_pct")),
        }
        features.append({"ticket": f"{h}-{s}-{t}", "features": vals})
    fingerprint = {
        "race_code": race_code, "generated_at_jst": record["generated_at_jst"],
        "entry_sha256": entry_source["source_sha256"],
        "boat_to_exhibition_course": {str(b): by_boat[b]["course"] for b in range(1, 7)},
        "signal_source_sha256": feature_sources,
        "signal_values": {str(b): by_boat[b]["signals"] for b in range(1, 7)},
        "comment_tags": {str(b): by_boat[b]["comment"] for b in range(1, 7)},
    }
    digest = sha256(json.dumps(fingerprint, sort_keys=True,
                               separators=(",", ":")).encode()).hexdigest()
    return {
        "model_id": MODEL, "race_code": race_code,
        "feature_matrix_sha256": digest,
        "course_to_boat": {str(k): v for k, v in c.items()},
        "rows": features,
        "count": len(features),
        "source_tier": "caller_claimed_not_independently_authenticated",
        "entry_kind": "start_exhibition_not_actual_final_course",
        "predicted_probabilities": False,
        "fitted_coefficients": False,
        "comment_NLP_used": False,
        "official_receipt_verified": False,
        "first_remote_receipt_verified": False,
        "result_read": False,
        "production_changed": False,
        "promotion_allowed": False,
    }
