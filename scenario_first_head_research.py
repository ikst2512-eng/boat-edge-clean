"""Research-only first-place (head) reweighting for #1710 scenario boards.

The frozen #1698 conditional-second/third experiment preserves head mass.
This separate optional hypothesis changes P(first) across six boats while
P(second, third | first) is *exactly* preserved. It consumes externally
computed, explicit six-boat scores; it does not infer ST, wind, tide, entry,
official sources or post-result signals and cannot certify performance.
"""
from hashlib import sha256
import json
import math

from scenario_four_mode_bridge import _valid_board, TICKETS


def hypothetical_head_board(baseline, six_head_log_shifts, *, study_id):
    if (type(study_id) is not str
            or not study_id.startswith("EXPLORATORY_ONLY_")
            or len(study_id) > 100):
        raise ValueError("separate_research_identity_required")
    if (type(six_head_log_shifts) not in (list, tuple)
            or len(six_head_log_shifts) != 6
            or any(type(x) not in (int, float)
                   or not math.isfinite(x) or not -6 <= x <= 6
                   for x in six_head_log_shifts)):
        raise ValueError("six_finite_bounded_head_hypotheses_required")
    base = _valid_board(baseline)
    original = {
        h: math.fsum(value for ticket, value in base.items() if ticket[0] == h)
        for h in range(1, 7)
    }
    if any(value <= 0 for value in original.values()):
        raise ValueError("missing_baseline_first_boat_probability")
    logits = {
        h: math.log(original[h]) + float(six_head_log_shifts[h - 1])
        for h in range(1, 7)
    }
    peak = max(logits.values())
    scaled = {h: math.exp(value - peak) for h, value in logits.items()}
    total = math.fsum(scaled.values())
    head = {h: value / total for h, value in scaled.items()}
    changed = {
        ticket: value * head[ticket[0]] / original[ticket[0]]
        for ticket, value in base.items()
    }
    if (set(changed) != TICKETS
            or not math.isclose(math.fsum(changed.values()), 1.0,
                                abs_tol=1e-12)):
        raise ValueError("head_reweight_normalization_failed")
    for h in range(1, 7):
        if not math.isclose(
            math.fsum(changed[t] for t in TICKETS if t[0] == h),
            head[h], abs_tol=1e-12
        ):
            raise ValueError("head_mass_invariant_failed")
    raw = json.dumps([study_id, list(six_head_log_shifts)],
                     separators=(",", ":"))
    return {
        "schema": "EXPLORATORY_FIRST_HEAD_SCENARIO_V1",
        "study_id": study_id,
        "head_hypothesis_sha256": sha256(raw.encode()).hexdigest(),
        "source_input_claim": "caller_supplied_hypotheses_not_authenticated",
        "original_first_mass": {str(h): original[h] for h in range(1, 7)},
        "hypothesis_first_mass": {str(h): head[h] for h in range(1, 7)},
        "ranked_board": sorted(changed.items(), key=lambda x: (-x[1], x[0])),
        "second_third_conditional_distribution_preserved": True,
        "official_wind_tide_entry_used": False,
        "formal": False,
        "calibrated": False,
        "first_remote_receipt_verified": False,
        "result_read": False,
        "promotion_allowed": False,
        "production_changed": False,
    }
