"""Prospective-only Top1 *reference* scorer; never an official certification.

Top1 policy was registered on Nov 8, therefore Nov 5-8 are excluded in their
entirety. Results are read ONLY AFTER frozen original/candidate validation.
Even a fully reproduced local shadow does not prove the FIRST remote receipt
of that candidate, complete scheduled-run inventory, or official T-12 inputs.
"""
import argparse
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path

from collect_clean_results import confirmed_record_is_usable
from four_mode_all_mode_same_job_shadow import SIZES, TOP1_PAIR_RULE, at_jst
from four_mode_all_shadow_reference_review import (
    TOP1_PROTOCOL, validate_capture_before_any_results,
)

START = "2026-11-09T00:00:00+09:00"
END = "2026-12-31T23:59:59+09:00"
PILOT = 300
CONFIRM = 300


def policy():
    data = json.loads(TOP1_PROTOCOL.read_bytes())
    if (type(data) is not dict
            or data.get("schema") != "FOUR_MODE_TOP1_PAIR_FORWARD_PREREGISTRATION_V1"
            or data.get("policy_id") != TOP1_PAIR_RULE
            or data.get("registered_jst_date") != "2026-11-08"
            or data.get("eligible_deadline_start_jst") != START
            or data.get("eligible_deadline_end_jst") != END
            or data.get("pilot_races") != PILOT
            or data.get("confirmation_races") != CONFIRM
            or data.get("selection_order") !=
                "deadline_jst_then_race_code_ascending_without_outcome_based_replacement"
            or data.get("primary_metric") !=
                "paired_top1_exact_trifecta_with_4_mode_familywise_Holm_two_sided_alpha_0.05"
            or data.get("existing_primary_metric_unchanged") is not True
            or data.get("promotion_allowed") is not False
            or data.get("formal_count") != 0):
        raise ValueError("top1_forward_protocol_drift")
    return data


def _empty_stats():
    return {mode: {
        "original": 0, "candidate": 0, "gained": 0, "lost": 0,
        "denominator": 0, "original_pct": None, "candidate_pct": None,
    } for mode in SIZES}


def _safe_result(root, code, deadline):
    path = root / "confirmed_results" / (code + ".json")
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 20000:
        return "pending", None
    try:
        if not confirmed_record_is_usable(path, code):
            return "invalid", None
        value = json.loads(path.read_bytes())
        if (at_jst(value["confirmed_at_jst"]) <= deadline or
                at_jst(value["collected_at_jst"]) <
                    at_jst(value["confirmed_at_jst"])):
            return "invalid", None
        finish = value["finish_order"]
        if type(finish) is not list or len(finish) != 3 or any(
                type(n) is not int or not 1 <= n <= 6 for n in finish
        ) or len(set(finish)) != 3:
            return "invalid", None
        return "confirmed", "-".join(map(str, finish))
    except (OSError, ValueError, KeyError, UnicodeError, TypeError):
        return "invalid", None


def compare(captures, root):
    """Never certify: verifies supplied captures, not ALL actual Actions runs."""
    policy()
    root = Path(root)
    # Validate entire supplied original and candidate capture inventory before
    # reading even one outcome. The caller-supplied inventory is NOT proof that
    # all GitHub Actions runs were retrieved.
    candidates, exclusions, published = validate_capture_before_any_results(
        captures, root
    )
    start = at_jst(START)
    end = at_jst(END)
    future_excluded = [
        row["race_code"] for capture in captures
        for row in capture.get("records", [])
        if (isinstance(row, dict)
            and row.get("status") == "ineligible"
            and isinstance(row.get("race_code"), str)
            and START[:10].replace("-", "") <= row["race_code"][:8] <=
                END[:10].replace("-", ""))
    ]
    if future_excluded:
        raise ValueError("top1_incomplete_frozen_cohort_no_replacement")
    frozen = sorted(
        [dict(code=code, **row)
         for code, row in candidates.items()
         if row is not None and start <= row["deadline"] <= end],
        key=lambda r: (r["deadline"], r["code"])
    )
    selected = frozen[:PILOT + CONFIRM]
    metrics = {"pilot": _empty_stats(), "confirmation": _empty_stats()}
    phase_valid = Counter()
    pending = []
    invalid = []
    for index, row in enumerate(selected):
        # An absent outcome keeps its original slot; never add a later race.
        result, winning = _safe_result(root, row["code"], row["deadline"])
        if result == "pending":
            pending.append(row["code"])
            continue
        if result == "invalid":
            invalid.append(row["code"])
            continue
        phase = "pilot" if index < PILOT else "confirmation"
        phase_valid[phase] += 1
        for mode in SIZES:
            old = row["baseline"][mode]
            new = row["top1_pair_candidate"][mode]
            # Top2, Top3, Top5 and Top10 hit membership must be identical.
            if (len(old) != SIZES[mode] or len(new) != len(old)
                    or any(set(old[:n]) != set(new[:n])
                           for n in (2, 3, 5, 10))
                    or new[2:] != old[2:]):
                raise ValueError("top1_pair_membership_violation")
            stat = metrics[phase][mode]
            baseline_hit = winning == old[0]
            candidate_hit = winning == new[0]
            stat["original"] += int(baseline_hit)
            stat["candidate"] += int(candidate_hit)
            stat["gained"] += int(candidate_hit and not baseline_hit)
            stat["lost"] += int(baseline_hit and not candidate_hit)
    for phase in metrics:
        for stat in metrics[phase].values():
            n = phase_valid[phase]
            stat["denominator"] = n
            stat["original_pct"] = round(100 * stat["original"] / n, 2) if n else None
            stat["candidate_pct"] = round(100 * stat["candidate"] / n, 2) if n else None
            if stat["candidate"] - stat["original"] != stat["gained"] - stat["lost"]:
                raise ValueError("top1_paired_count_mismatch")
    return {
        "schema": "FOUR_MODE_TOP1_FORWARD_REFERENCE_V1",
        "status": "reference_only_no_prospective_certification",
        "formal": False,
        "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "candidate_first_remote_receipt_verified": False,
        "official_T_minus_12_six_and_odds_verified": False,
        "complete_capture_run_inventory_verified": False,
        "eligible_start_jst": START,
        "eligible_end_jst": END,
        "excluded_discovery_days": "2026-11-05 through 2026-11-08",
        "supplied_publication_races": published,
        "eligible_frozen_candidate_races": len(frozen),
        "reference_slots_reserved_first_600": len(selected),
        "pilot_slots_reserved": min(len(selected), PILOT),
        "confirmation_slots_reserved": max(0, len(selected) - PILOT),
        "confirmed_result_matches": dict(phase_valid),
        "pending_result_codes": pending,
        "invalid_result_codes": invalid,
        "supplied_precohort_exclusions": dict(exclusions),
        "top1_by_phase": metrics,
        "warning": "No complete run inventory, independently verified FIRST "
                   "candidate receipt or official T-12 source. This reference "
                   "sample cannot certify an accuracy gain or permit deployment.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--capture", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    captures = [json.loads(p.read_bytes()) for p in args.capture]
    result = compare(captures, args.root)
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(raw, encoding="utf-8")
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
