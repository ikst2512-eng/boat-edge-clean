"""Research-only fail-closed assessor for the separate #1698 paired reference report.

No outcomes read; this audits aggregate stats returned by the existing
result-last forward scorer. It does NOT authenticate external results,
original publication, pre-T12 first remote receipt, or official six/120.
It cannot authorize promotion, even if a synthetic example looks positive.
"""
import json
from pathlib import Path

from four_mode_position_sensitive_forward import MODES, TOPS

EXPECTED_PHASES = ("pilot", "confirmation")
SCHEMA = "FOUR_MODE_POSITION_SENSITIVE_REFERENCE_SCORE_V1"
GUARD_SCHEMA = "FOUR_MODE_POSITION_SENSITIVE_PAIRED_REFERENCE_GUARD_V1"


def assess_reference_score(score):
    """Reject forged/inconsistent totals, never mistake Top5 narrow for Top10."""
    if type(score) is not dict or score.get("schema") != SCHEMA:
        raise ValueError("invalid_reference_schema")
    for flag in ("formal", "promotion_allowed", "model_improvement_proven",
                 "candidate_first_remote_receipt_verified",
                 "complete_capture_inventory_verified",
                 "official_T12_beforeinfo_six_and_odds_120_verified"):
        if score.get(flag) is not False:
            raise ValueError("reference_must_be_unverified:" + flag)
    if score.get("status") != "reference_only_unverified_first_remote_receipt":
        raise ValueError("reference_must_be_local_only")
    if (type(score.get("eligible_frozen_candidate_slots")) is not int or
            not 0 <= score["eligible_frozen_candidate_slots"] <= 600):
        raise ValueError("invalid_total_cohort")
    pilot_slots = score.get("pilot_reserved_slots")
    confirm_slots = score.get("confirmation_reserved_slots")
    if (type(pilot_slots) is not int or type(confirm_slots) is not int or
            pilot_slots != min(score["eligible_frozen_candidate_slots"], 300) or
            confirm_slots != max(score["eligible_frozen_candidate_slots"] - 300, 0)):
        raise ValueError("invalid_phase_allocation")
    counts = score.get("confirmed_result_counts")
    if type(counts) is not dict or any(k not in EXPECTED_PHASES for k in counts):
        raise ValueError("invalid_confirmed_count_map")
    for phase, slots in (("pilot", pilot_slots), ("confirmation", confirm_slots)):
        c = counts.get(phase, 0)
        if type(c) is not int or not 0 <= c <= slots:
            raise ValueError("invalid_confirmed_denominator")
    pending = score.get("pending_race_codes")
    invalid = score.get("invalid_result_race_codes")
    if (type(pending) is not list or type(invalid) is not list or
            any(type(x) is not str for x in pending + invalid) or
            len(set(pending + invalid)) != len(pending) + len(invalid) or
            sum(counts.values()) + len(pending) + len(invalid) !=
            score["eligible_frozen_candidate_slots"]):
        raise ValueError("missing_duplicate_or_substituted_race_slot")

    phases = score.get("by_phase_mode_topn")
    if type(phases) is not dict or set(phases) != set(EXPECTED_PHASES):
        raise ValueError("invalid_phase_stats")
    out = {}
    for phase in EXPECTED_PHASES:
        rows = phases[phase]
        if type(rows) is not dict or set(rows) != set(MODES):
            raise ValueError("missing_mode_scores")
        denominator = counts.get(phase, 0)
        out[phase] = {}
        for mode, budget in MODES.items():
            if type(rows[mode]) is not dict or set(rows[mode]) != set(map(str, TOPS)):
                raise ValueError("invalid_topn_scores")
            out[phase][mode] = {}
            previous_hits = None
            for top in TOPS:
                k = str(top)
                raw = rows[mode][k]
                if type(raw) is not dict:
                    raise ValueError("invalid_metric_row")
                for label in ("baseline", "candidate", "gained", "lost",
                              "reference_denominator"):
                    if type(raw.get(label)) is not int:
                        raise ValueError("invalid_metric_counter:" + label)
                b, c, g, l = (raw[x] for x in ("baseline", "candidate", "gained", "lost"))
                if (raw["reference_denominator"] != denominator or
                        min(b, c, g, l) < 0 or
                        max(b, c, g, l) > denominator or
                        c - b != g - l or
                        g > denominator - b or l > b or
                        b + g > denominator or c + l > denominator):
                    raise ValueError("paired_counts_inconsistent")
                if top <= budget:
                    if (previous_hits is not None and
                            (b < previous_hits[0] or c < previous_hits[1])):
                        raise ValueError("nonmonotone_topn_hit_counts")
                    previous_hits = (b, c)
                if top > budget:
                    # The unmodified reference scorer slices [:10] from an
                    # actual five-ticket narrow list. Its counts duplicate
                    # Top5, NOT a ten-ticket comparison. Reject disagreement.
                    if mode != "narrow" or top != 10:
                        raise ValueError("unsupported_topn")
                    alias = rows[mode]["5"]
                    if any(raw[x] != alias[x] for x in
                           ("baseline", "candidate", "gained", "lost",
                            "reference_denominator")):
                        raise ValueError("invalid_narrow_top10_alias")
                    out[phase][mode][k] = {
                        "applicable": False, "reason": "ticket_budget_is_5",
                        "mode_ticket_budget": budget,
                    }
                    continue
                out[phase][mode][k] = {
                    "applicable": True,
                    "reference_denominator": denominator,
                    "baseline_hit_count": b,
                    "candidate_hit_count": c,
                    "gained_hits": g,
                    "lost_hits": l,
                    "net_hit_difference": g - l,
                    "baseline_hit_pct": round(100 * b / denominator, 3)
                    if denominator else None,
                    "candidate_hit_pct": round(100 * c / denominator, 3)
                    if denominator else None,
                    "observed_delta_percentage_points":
                        round(100 * (g - l) / denominator, 3)
                        if denominator else None,
                    "observed_net_regression": (g < l) if denominator else None,
                }

    confirmation_complete = (pilot_slots == 300 and confirm_slots == 300
                             and counts.get("pilot", 0) == 300
                             and counts.get("confirmation", 0) == 300
                             and not pending and not invalid)
    confirmed_regressions = []
    if confirmation_complete:
        for mode, budget in MODES.items():
            for k in ("5", "10"):
                if int(k) > budget:
                    continue
                metric = out["confirmation"][mode][k]
                if metric["observed_net_regression"] is True:
                    confirmed_regressions.append({
                        "mode": mode, "topn": int(k),
                        "net_hit_difference": metric["net_hit_difference"],
                    })
    return {
        "schema": GUARD_SCHEMA,
        "status": "reference_only_unverified_not_formal",
        "formal": False, "promotion_allowed": False,
        "model_improvement_proven": False,
        "independent_first_remote_receipt_verified": False,
        "official_T12_evidence_verified": False,
        "pilot_reserved_slots": pilot_slots,
        "confirmation_reserved_slots": confirm_slots,
        "confirmed_result_counts": {p: counts.get(p, 0) for p in EXPECTED_PHASES},
        "all_600_reference_results_present": confirmation_complete,
        "reference_confirmatory_top5_top10_net_loss_observed":
            (bool(confirmed_regressions) if confirmation_complete else None),
        "reference_confirmatory_regressions": confirmed_regressions,
        "by_phase_mode_topn": out,
        "warning": (
            "Reference-only observations, never formal evidence. Net Top5/10 "
            "loss blocks promotion; zero/positive net alone NEVER proves "
            "non-inferiority. Independent pre-T12 candidate remote receipts, "
            "complete run inventory, authenticated official inputs/results, "
            "predeclared statistical decision bounds and manual review are "
            "required. No model, archive or production change."
        ),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path,
                        help="Previously generated research-only aggregate comparison JSON")
    args = parser.parse_args()
    if args.reference is None:
        print(json.dumps({
            "schema": GUARD_SCHEMA,
            "status": "no_future_reference_report_supplied",
            "formal": False, "promotion_allowed": False,
            "model_improvement_proven": False,
            "confirmed_forward_reference_samples": 0,
        }, sort_keys=True))
        return
    if args.reference.is_symlink() or not args.reference.is_file():
        raise ValueError("untrusted_reference_path")
    if args.reference.stat().st_size > 100000:
        raise ValueError("oversize_reference_report")
    print(json.dumps(assess_reference_score(json.loads(
        args.reference.read_text(encoding="utf-8"))), sort_keys=True))


if __name__ == "__main__":
    main()
