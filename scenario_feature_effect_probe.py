"""Result-blind feature sensitivity probe for the #1710 scenario bridge.

An injected, pure research emitter is run against explicitly supplied
alternative inputs. This does not certify feature origin, causal importance,
weather/tide corrections, accuracy or official provenance. Crucially it
distinguishes 'field was supplied' from 'the output actually responded'.
"""
from copy import deepcopy
import json
import re

ALLOWED = frozenset({
    "national_win_rates", "local_win_rate", "average_st_s",
    "exhibition_st_s", "exhibition_time_s", "motor_2ren_pct",
    "exhibition_entry_course", "prestart_entry_course_observed",
    "two_course_wall_rate", "two_course_escape_assist_rate",
    "wind_speed_mps", "wind_from_true_deg", "start_heading_true_deg",
    "wave_height_cm", "tide_height_cm", "tide_phase", "tide_station",
    "venue_code", "prior_day_race_methods",
})
FORBIDDEN = frozenset({
    "result", "finish_order", "winning_ticket", "confirmed_result",
    "payout", "post_race_weather", "final_entry_course",
})
HEX = re.compile(r"[a-f0-9]{64}\Z")


def _snapshot(fields):
    if type(fields) is not dict or not fields or set(fields) - ALLOWED or set(fields) & FORBIDDEN:
        raise ValueError("invalid_or_outcome_contaminated_fields")
    try:
        raw = json.dumps(fields, sort_keys=True, allow_nan=False)
        parsed = json.loads(raw)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError("unserializable_or_nonfinite_features") from error
    if parsed != fields:
        raise ValueError("unstable_feature_roundtrip")
    return parsed


def _reference(result):
    if (type(result) is not dict
            or result.get("schema") != "ALL_MODE_SCENARIO_BRIDGE_EXPLORATORY_V1"
            or result.get("formal") is not False
            or result.get("promotion_allowed") is not False
            or result.get("production_changed") is not False
            or result.get("forecast_usable") is not False):
        raise ValueError("untrusted_research_emitter_output")
    digest = result.get("mixed_120_board_sha256")
    if type(digest) is not str or not HEX.fullmatch(digest):
        raise ValueError("missing_mixture_fingerprint")
    top10 = result.get("top10_reference")
    if (type(top10) is not list or len(top10) != 10
            or any(type(row) is not dict or
                   not isinstance(row.get("combo"), str)
                   for row in top10)):
        raise ValueError("invalid_top10_output")
    names = [row["combo"] for row in top10]
    if len(set(names)) != 10:
        raise ValueError("duplicate_top10_output")
    return digest, names


def probe_feature_effects(input_state, variants, emit):
    """Compare complete mixture fingerprint and TopK to explicit alternatives.

    *variants* is {feature_name: alternate_value}. Never infer a perturbation
    magnitude, never claim an official measured source, and never read results.
    """
    current = _snapshot(input_state)
    if (type(variants) is not dict or not variants
            or set(variants) - set(current) or set(variants) - ALLOWED):
        raise ValueError("variant_fields_must_be_present_and_allowed")
    if not callable(emit):
        raise ValueError("emitter_callback_required")
    original = _reference(emit(deepcopy(current)))
    checks = {}
    for key in sorted(variants):
        alternate = deepcopy(current)
        alternate[key] = variants[key]
        alternate = _snapshot(alternate)
        if alternate[key] == current[key]:
            raise ValueError("variant_value_same_as_baseline")
        after = _reference(emit(deepcopy(alternate)))
        checks[key] = {
            "full_120_board_changed": original[0] != after[0],
            "top1_changed": original[1][0] != after[1][0],
            "top5_membership_changed": set(original[1][:5]) != set(after[1][:5]),
            "top10_membership_changed": set(original[1]) != set(after[1]),
            "raw_input_present_proves_consumption": False,
            "actual_official_feature_used_verified": False,
            "accuracy_effect_verified": False,
        }
    return {
        "schema": "SCENARIO_FEATURE_ABLATION_EXPLORATORY_V1",
        "tested_hypotheses": checks,
        "all_features_tested": sorted(variants),
        "no_change_is_not_claimed_as_applied": True,
        "synthetic_or_unattested_inputs_only": True,
        "formal": False,
        "official_t12_certified": False,
        # The injected callback may be external; this probe cannot prove it
        # did not read outcomes. Do not advertise result-blind provenance.
        "confirmed_results_read": None,
        "external_emitter_result_blind_independently_verified": False,
        "promotion_allowed": False,
    }
