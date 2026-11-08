"""Outcome-blind audit of the *archived* four-mode ticket concentration.

This does NOT measure accuracy, detect all unsaved races, approve new
selectors, or prove official T-12/remote first receipt. No result reads.
"""
import argparse
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from clean_four_modes import rank_modes, ticket_order_audit
from research_model import probabilities

CODE = re.compile(r"20[0-9]{10}\Z")
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
MODES = ("narrow", "hit", "balance", "hole")
LENGTHS = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
TICKET = re.compile(r"[1-6]-[1-6]-[1-6]\Z")


def verified_pre_result_snapshot(raw, code):
    if (type(raw) is not dict or raw.get("race_code") != code
            or raw.get("model_version") != VERSION
            or raw.get("schema") != "CLEAN_FOUR_MODES_PREDEADLINE_V1"
            or raw.get("status") != "provisional"
            or raw.get("target_rates_not_proven") is not True
            or not isinstance(raw.get("modes"), dict)
            or set(raw["modes"]) != set(MODES)):
        raise ValueError("archive_schema_or_version_invalid")
    rates = raw.get("input_national_win_rates")
    if (type(rates) is not list or len(rates) != 6
            or any(type(r) not in (int, float)
                   or not math.isfinite(r) or r <= 0 or r > 10 for r in rates)):
        raise ValueError("invalid_national_win_rates")
    start = datetime.fromisoformat(raw["generated_at_jst"])
    cutoff = datetime.fromisoformat(raw["deadline_jst"])
    if (start.utcoffset() is None or cutoff.utcoffset() is None
            or start >= cutoff or cutoff.strftime("%Y%m%d") != code[:8]):
        raise ValueError("invalid_archive_timestamps")
    ordered = {}
    for name in MODES:
        mode = raw["modes"][name]
        tickets = mode.get("tickets") if type(mode) is dict else None
        if type(tickets) is not list or len(tickets) != LENGTHS[name]:
            raise ValueError("invalid_mode_ticket_count")
        combos = []
        for ticket in tickets:
            value = ticket.get("combo") if type(ticket) is dict else None
            if (not isinstance(value, str) or not TICKET.fullmatch(value)
                    or len(set(value.split("-"))) != 3):
                raise ValueError("invalid_trifecta")
            combos.append(value)
        if len(set(combos)) != len(combos):
            raise ValueError("duplicated_mode_ticket")
        ordered[name] = combos
    if ticket_order_audit(raw["modes"])["status"] != "pass":
        raise ValueError("mode_ticket_order_invalid")
    # A syntactically valid list can still have been silently re-ordered or
    # substituted. Recalculate the production V2 probability board using
    # only the pre-race rates. No result, payout or future source is opened.
    expected = rank_modes(probabilities(rates))
    for name in MODES:
        saved_tickets = raw["modes"][name]["tickets"]
        expected_tickets = expected[name]["tickets"]
        if any(
            saved.get("combo") != generated["combo"]
            or type(saved.get("p")) not in (int, float)
            or not math.isfinite(saved["p"])
            or saved["p"] != generated["p"]
            for saved, generated in zip(saved_tickets, expected_tickets)
        ):
            raise ValueError("stored_ticket_not_reproduced_from_inputs")
    return rates, ordered


def audit(root, day):
    if type(day) is not str or not re.fullmatch(r"20[0-9]{6}", day):
        raise ValueError("invalid_audit_day")
    root = Path(root)
    folder = root / "four_mode_forecasts"
    files = sorted(folder.glob(day + "*.json")) if folder.is_dir() else []
    first = {mode: Counter() for mode in MODES}
    first_head = {mode: Counter() for mode in MODES}
    full_orders = {mode: set() for mode in MODES}
    first_five = {mode: set() for mode in MODES}
    rates_seen = set()
    errors = []
    beforeinfo = Counter()
    shared_nonhole = 0
    top2_different_head_hit = 0
    for file in files:
        code = file.stem
        try:
            if (file.is_symlink() or file.stat().st_size > 30000
                    or not CODE.fullmatch(code) or not code.startswith(day)):
                raise ValueError("invalid_archive_file")
            raw = json.loads(file.read_bytes())
            rates, tickets = verified_pre_result_snapshot(raw, code)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError,
                OverflowError) as exc:
            errors.append({"race_code": code, "reason": str(exc)[:100]})
            continue
        rates_seen.add(tuple(rates))
        beforeinfo[str(raw.get("beforeinfo", "not_provided"))] += 1
        if len({tickets[m][0] for m in ("narrow", "hit", "balance")}) == 1:
            shared_nonhole += 1
        if tickets["hit"][0][0] != tickets["hit"][1][0]:
            top2_different_head_hit += 1
        for mode in MODES:
            a = tickets[mode]
            first[mode][a[0]] += 1
            first_head[mode][a[0].split("-")[0]] += 1
            full_orders[mode].add(tuple(a))
            first_five[mode].add(frozenset(a[:5]))
    accepted = sum(first["hit"].values())
    return {
        "schema": "FOUR_MODE_TOP1_ARCHIVED_INPUT_BIAS_AUDIT_V1",
        "day": day,
        "source": "local_saved_four_mode_forecasts_only",
        "status": "reference_only_not_accuracy",
        "formal": False,
        "model_promotion_allowed": False,
        "confirmed_results_read": False,
        "file_count": len(files),
        "valid_v2_saved": accepted,
        "invalid_archives": errors,
        "coverage_of_unsaved_races_verified": False,
        "distinct_national_win_rate_vectors": len(rates_seen),
        "fixed_1000_case_prior_used_by_model": True,
        "saved_ticket_order_and_scores_replayed": True,
        "forecast_features_in_production": ["six_national_win_rates"],
        "wind_st_course_motor_in_production_score": False,
        "same_top1_narrow_hit_balance": shared_nonhole,
        "same_top1_narrow_hit_balance_pct":
            round(100 * shared_nonhole / accepted, 2) if accepted else None,
        "hit_top2_different_head_count": top2_different_head_hit,
        "hit_top2_different_head_pct":
            round(100 * top2_different_head_hit / accepted, 2) if accepted else None,
        "top1_combos_by_mode": {m: dict(first[m].most_common()) for m in MODES},
        "top1_heads_by_mode": {m: dict(first_head[m].most_common()) for m in MODES},
        "distinct_full_ticket_orders_by_mode": {m: len(full_orders[m]) for m in MODES},
        "distinct_first_5_ticket_sets_by_mode": {m: len(first_five[m]) for m in MODES},
        "beforeinfo_flags": dict(beforeinfo),
        "warning": "Ticket and input diversity only; results, first remote receipt,"
                   " unsaved race coverage and T-12 proof not verified.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--day", default="20261108")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.root, args.day)
    content = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
