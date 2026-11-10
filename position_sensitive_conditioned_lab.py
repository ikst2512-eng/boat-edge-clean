"""Isolated, UNREGISTERED evidence-conditioned 2nd/3rd research laboratory.

Not imported by production. Not part of the frozen #1698 300+300 candidate.
No external sources, outcomes, odds, or forecast archives are read.
Numerical coefficients are hypotheses, NEVER calibrated hit probabilities.
"""
from itertools import permutations
import math

FIELDS = {
    # (unit scale, favorable sign, min, max); scales are NOT predictive weights.
    "local_win_rate": (1.0, 1, 0.0, 20.0),
    "average_st_s": (0.05, -1, 0.0, 1.0),
    "exhibition_st_s": (0.05, -1, -0.5, 1.0),
    "exhibition_time_s": (0.1, -1, 5.0, 10.0),
    "motor_2ren_pct": (15.0, 1, 0.0, 100.0),
    "entry_course": (1.0, -1, 1.0, 6.0),
    # Interactions require an independently grounded true-north course bearing.
    "headwind_x_entry": (1.0, 1, -100.0, 100.0),
    "wave_x_entry": (1.0, 1, -100.0, 100.0),
}
DIRECT = tuple(k for k in FIELDS if not k.endswith("_x_entry"))
CONTEXT = {"wind_speed_mps", "wind_from_true_deg",
           "start_heading_true_deg", "wave_height_cm"}
TICKETS = set(permutations(range(1, 7), 3))


def _number(value, low, high, label):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError("invalid_" + label)
    return float(value)


def _board(base):
    if not isinstance(base, (list, tuple)) or len(base) != 120:
        raise ValueError("incomplete_baseline_board")
    rows = {}
    for item in base:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError("invalid_baseline_row")
        ticket, p = item
        if (not isinstance(ticket, (tuple, list)) or len(ticket) != 3
                or any(type(v) is not int for v in ticket)
                or tuple(ticket) not in TICKETS):
            raise ValueError("invalid_baseline_ticket")
        key = tuple(ticket)
        if key in rows:
            raise ValueError("duplicate_baseline_ticket")
        rows[key] = _number(p, 0.0, 1.0, "baseline_probability")
    if set(rows) != TICKETS or abs(sum(rows.values()) - 1) > 1e-9:
        raise ValueError("baseline_not_normalized")
    if any(v <= 0 for v in rows.values()):
        raise ValueError("baseline_zero_mass_not_supported")
    return rows


def _params(coefficients, study_id):
    if not isinstance(study_id, str) or not study_id.startswith("EXPLORATORY_ONLY_") or len(study_id) > 80:
        raise ValueError("new_study_identity_required")
    if not isinstance(coefficients, dict) or not coefficients:
        raise ValueError("explicit_exploratory_parameters_required")
    if set(coefficients) - set(FIELDS):
        raise ValueError("unregistered_feature_name")
    out = {}
    for name, positions in coefficients.items():
        if not isinstance(positions, dict) or set(positions) != {"second", "third"}:
            raise ValueError("invalid_position_coefficients")
        out[name] = {position: _number(positions[position], -2, 2, "coefficient")
                     for position in ("second", "third")}
    return out


def _features(evidence, active):
    if type(evidence) is not dict or set(evidence) != {"boats", "context"}:
        raise ValueError("invalid_or_outcome_contaminated_evidence")
    boats, context = evidence["boats"], evidence["context"]
    if type(boats) is not list or len(boats) != 6 or type(context) is not dict:
        raise ValueError("invalid_feature_coverage")
    if set(context) - CONTEXT:
        raise ValueError("unapproved_context")
    boat_fields = set(DIRECT) | {"boat"}
    by_id = {}
    for boat in boats:
        if type(boat) is not dict or set(boat) - boat_fields or type(boat.get("boat")) is not int:
            raise ValueError("invalid_boat_fields")
        number = boat["boat"]
        if number not in range(1, 7) or number in by_id:
            raise ValueError("duplicate_or_invalid_boat")
        by_id[number] = boat
    if set(by_id) != set(range(1, 7)):
        raise ValueError("not_six_boats")
    vectors = {}
    required = set(active) & set(DIRECT)
    if {"headwind_x_entry", "wave_x_entry"} & set(active):
        required.add("entry_course")
    for field in required:
        scale, sign, low, high = FIELDS[field]
        vals = [_number(by_id[i].get(field), low, high, field) for i in range(1, 7)]
        if field == "entry_course" and sorted(vals) != [1., 2., 3., 4., 5., 6.]:
            raise ValueError("entry_course_not_permutation")
        vectors[field] = [sign * v / scale for v in vals]
    if "headwind_x_entry" in active:
        v = _number(context.get("wind_speed_mps"), 0, 40, "wind_speed")
        direction = _number(context.get("wind_from_true_deg"), 0, 360, "wind_from")
        heading = _number(context.get("start_heading_true_deg"), 0, 360, "start_heading")
        headwind = v * math.cos(math.radians(direction - heading))
        vectors["headwind_x_entry"] = [headwind * (3.5 - by_id[i]["entry_course"]) / 5
                                          for i in range(1, 7)]
    if "wave_x_entry" in active:
        wave = _number(context.get("wave_height_cm"), 0, 300, "wave_height")
        vectors["wave_x_entry"] = [wave * (3.5 - by_id[i]["entry_course"]) / 10
                                     for i in range(1, 7)]
    return vectors


def experimental_conditional_board(baseline, evidence, coefficients, study_id):
    """Unverified lab-only hypothesis: preserve every P(first=h) exactly.

    Conditional tilt: log P(s,t|h) ∝ log P0(s,t|h)
      + sum_f theta2_f*(z_f(s)-mean(z_f(not h)))
      + sum_f theta3_f*(z_f(t)-mean(z_f(not h,s))).
    A zero coefficient does not require that field, preventing fabricated fills.
    """
    base = _board(baseline)
    weights = _params(coefficients, study_id)
    active = {k for k, positions in weights.items() if any(positions.values())}
    vectors = _features(evidence, active)
    result = {}
    for h in range(1, 7):
        group = [(t, p) for t, p in base.items() if t[0] == h]
        mass = sum(p for _, p in group)
        logs = []
        for (head, second, third), p in group:
            delta = 0.0
            for field in active:
                z = vectors[field]
                avg2 = sum(z[j-1] for j in range(1, 7) if j != h) / 5
                avg3 = sum(z[j-1] for j in range(1, 7) if j not in (h, second)) / 4
                delta += weights[field]["second"] * (z[second-1] - avg2)
                delta += weights[field]["third"] * (z[third-1] - avg3)
            logs.append((head, second, third, math.log(p) + delta))
        peak = max(x[3] for x in logs)
        scaled = [(x[:3], math.exp(x[3] - peak)) for x in logs]
        normalizer = sum(p for _, p in scaled)
        for ticket, value in scaled:
            result[ticket] = mass * value / normalizer
    if set(result) != TICKETS or abs(sum(result.values()) - 1) > 1e-9:
        raise ValueError("invalid_conditional_mass")
    for h in range(1, 7):
        if abs(sum(v for t, v in base.items() if t[0] == h) -
               sum(v for t, v in result.items() if t[0] == h)) > 1e-12:
            raise ValueError("head_probability_changed")
    return {
        "status": "unregistered_hypothesis_numeric_sensitivity_only",
        "study_id": study_id,
        "active_features": sorted(active),
        "unused_supplied_features_are_not_assumed_verified": True,
        "requires_independent_new_preregistration": True,
        "formal": False,
        "calibrated_probabilities": False,
        "verified_predeadline_official_inputs": False,
        "verified_candidate_first_remote_receipt": False,
        "confirmed_results_read": False,
        "production_changed": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
        "ranked_board": sorted(result.items(), key=lambda x: (-x[1], x[0])),
    }


def inspect_feature_readiness(evidence):
    """Classify structural per-race coverage without authenticating any source.

    No unofficial, missing or invalid value is filled in. A feature shown as
    available is NOT proved official, pre-T-12, or predictive.
    """
    _features(evidence, set())  # Reject bad roster and outcome-bearing schema first.
    available = []
    missing_or_invalid = {}
    for field in FIELDS:
        try:
            _features(evidence, {field})
        except ValueError as exc:
            missing_or_invalid[field] = str(exc)
        else:
            available.append(field)
    return {
        "status": "structural_coverage_not_official_source_certification",
        "structurally_present_features": sorted(available),
        "missing_or_invalid_features": missing_or_invalid,
        "feature_values_imputed": False,
        "official_bytes_and_predeadline_receipts_verified": False,
        "first_remote_receipt_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "promotion_allowed": False,
    }
