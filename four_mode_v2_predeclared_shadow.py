"""Read-only V2 shadow comparison with a frozen, predeclared candidate.

Protocol V1: a <=0.5 national-win-rate gap enables a 0.30
first-place novelty bonus *within the existing hit Top10*. This rule was
informed by inspected V1 history; it is not an independent V1 holdout.
No forecast or result files are written or modified.
"""
import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from four_mode_archive_api import archived_four_modes
from four_mode_frozen_diagnostic import compare_race

ROOT = Path(__file__).resolve().parent
VERSION = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
PROTOCOL = "V2_FIRST_HEAD_GAP_0_5_BONUS_0_30_SHADOW_V1"
COUNT_POLICY = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
TOPS = (3, 5, 10)
MODES = ("narrow", "hit", "balance", "hole")
PAIRS = (("hit", "balance"), ("narrow", "hit"), ("balance", "hole"))
PAIR_OUTCOMES = ("both", "left_only", "right_only", "neither")
MISS_REASONS = ("covered", "winner_head_absent", "winner_second_pair_absent", "winner_third_absent")


def candidate_order(tickets, rates):
    """Result-blind, fixed-membership, deterministic shadow ordering."""
    if (type(rates) is not list or len(rates) != 6 or
            any(type(v) not in (int, float) or not math.isfinite(v) or
                v < 0 or v > 10 for v in rates)):
        raise ValueError("invalid_rates")
    if len(tickets) != 10:
        raise ValueError("invalid_ticket_count")
    if (len({row["combo"] for row in tickets}) != 10 or
            any(type(row["p"]) not in (int, float) or
                not math.isfinite(row["p"]) or row["p"] < 0 for row in tickets)):
        raise ValueError("invalid_tickets")
    originals = [row["combo"] for row in tickets]
    gap = sorted(rates, reverse=True)[0] - sorted(rates, reverse=True)[1]
    if gap > 0.5:
        return originals, False
    remaining = list(tickets)
    chosen = []
    while remaining:
        previous = {item["combo"][0] for item in chosen}
        best = max(remaining, key=lambda x: (
            x["p"] * (1 + 0.30 * (x["combo"][0] not in previous)),
            x["p"], x["combo"]))
        chosen.append(best)
        remaining.remove(best)
    return [row["combo"] for row in chosen], True


def missing_result_phase(deadline_jst, now):
    """Classify missing outcomes by schedule only; never infer collection failure."""
    deadline = datetime.fromisoformat(deadline_jst)
    if deadline.utcoffset() != timedelta(hours=9) or now.utcoffset() != timedelta(hours=9):
        raise ValueError("non_jst_timestamp")
    if now < deadline:
        return "before_deadline"
    if now < deadline + timedelta(minutes=60):
        return "within_60m_after_deadline"
    return "over_60m_after_deadline"


def evaluate(root=ROOT, now=None):
    root = Path(root)
    now = now or datetime.now(timezone(timedelta(hours=9)))
    directory = root / "four_mode_forecasts"
    groups = defaultdict(lambda: {
        "forecast_files": 0, "comparable": 0, "pending_results": 0,
        "forecast_only_exposure": {"valid": 0, "eligible": 0,
                                   "reordered_top10": 0,
                                   "changed_top3_membership": 0,
                                   "changed_top5_membership": 0},
        "matured_comparable": 0,
        "matured_modes": {m: {f"top{n}": 0 for n in TOPS} for m in MODES},
        "pending_by_deadline": {"before_deadline": 0,
                                "within_60m_after_deadline": 0,
                                "over_60m_after_deadline": 0},
        "applied": 0, "reordered_top10": 0, "changed_top3_membership": 0,
        "changed_top5_membership": 0, "modes": {m: {f"top{n}": 0 for n in TOPS} for m in MODES},
        "paired_modes": {f"{left}_vs_{right}": {f"top{n}": {o: 0 for o in PAIR_OUTCOMES}
                          for n in TOPS} for left, right in PAIRS},
        "miss_reasons": {m: {reason: 0 for reason in MISS_REASONS} for m in MODES},
        "baseline": {f"top{n}": 0 for n in TOPS},
        "candidate": {f"top{n}": 0 for n in TOPS},
        "gained_top3": 0, "lost_top3": 0})
    excluded = defaultdict(int)
    changed_top3_cases = []
    if not directory.is_dir():
        return {"status": "no_forecast_directory", "protocol": PROTOCOL,
                "formal": False, "groups": {}}
    for path in sorted(directory.glob("*.json")):
        if not re.fullmatch(r"20[0-9]{10}", path.stem):
            continue
        if path.is_symlink() or path.stat().st_size > 30000:
            excluded["unsafe_file"] += 1
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            excluded["invalid_json"] += 1
            continue
        if raw.get("model_version") != VERSION:
            continue
        date = path.stem[:8]
        row = groups[date]
        row["forecast_files"] += 1
        status, archive = archived_four_modes(path.stem, root)
        if status != 200 or archive.get("model_version") != VERSION:
            excluded["invalid_v2_archive"] += 1
            continue
        if any(len(archive["modes"][m]["tickets"]) != c
               for m, c in COUNT_POLICY.items()):
            excluded["invalid_v2_count_policy"] += 1
            continue
        try:
            candidate, enabled = candidate_order(
                archive["modes"]["hit"]["tickets"],
                raw["input_national_win_rates"])
        except (KeyError, ValueError, TypeError):
            excluded["invalid_shadow_inputs"] += 1
            continue
        # Outcome-blind exposure audit across ALL valid frozen V2 forecasts,
        # including races without a confirmed finish. This does not measure
        # accuracy or validate first-publication timing.
        baseline = [item["combo"] for item in archive["modes"]["hit"]["tickets"]]
        if len(candidate) != len(baseline) or set(candidate) != set(baseline):
            excluded["membership_changed"] += 1
            continue
        exposure = row["forecast_only_exposure"]
        exposure["valid"] += 1
        exposure["eligible"] += int(enabled)
        exposure["reordered_top10"] += int(candidate != baseline)
        exposure["changed_top3_membership"] += int(set(candidate[:3]) != set(baseline[:3]))
        exposure["changed_top5_membership"] += int(set(candidate[:5]) != set(baseline[:5]))
        compared = compare_race(path.stem, root)
        # Freeze changed-case identity and the original/candidate Top3 before
        # reading any outcome. A separate unresolved cohort is critical:
        # result availability is uneven and must never count as a model miss.
        if set(candidate[:3]) != set(baseline[:3]):
            case = {"race_code": path.stem, "date_jst": date,
                    "venue_code": path.stem[8:10],
                    "baseline_top3": baseline[:3], "candidate_top3": candidate[:3],
                    "result_status": ("confirmed_research_only"
                                      if compared.get("status") == "historical_comparison_only"
                                      else "missing"
                                      if compared.get("status") == "result_unavailable"
                                      else "invalid_or_untrusted"),
                    "pending_phase": None}
            if compared.get("status") == "result_unavailable":
                try:
                    case["pending_phase"] = missing_result_phase(archive["deadline_jst"], now)
                except (KeyError, ValueError, TypeError, OverflowError):
                    case["result_status"] = "invalid_deadline"
            changed_top3_cases.append(case)
        if compared.get("status") == "result_unavailable":
            try:
                phase = missing_result_phase(archive["deadline_jst"], now)
            except (KeyError, ValueError, TypeError, OverflowError):
                excluded["invalid_pending_deadline"] += 1
                continue
            row["pending_results"] += 1
            row["pending_by_deadline"][phase] += 1
            continue
        if compared.get("status") != "historical_comparison_only":
            excluded["invalid_or_untrusted_result"] += 1
            continue
        if any(compared.get("modes", {}).get(m, {}).get("coverage_diagnostic") not in MISS_REASONS
               for m in MODES):
            excluded["invalid_miss_diagnostics"] += 1
            continue
        winning = compared["winning_ticket"]
        # A mature confirmed result and an overdue missing result share the
        # same denominator. The 60m window is an operational diagnostic,
        # not proof that the upstream result should already exist.
        try:
            maturity = missing_result_phase(archive["deadline_jst"], now)
        except (KeyError, ValueError, TypeError, OverflowError):
            excluded["invalid_confirmed_deadline"] += 1
            continue
        row["comparable"] += 1
        row["matured_comparable"] += int(maturity == "over_60m_after_deadline")
        row["applied"] += int(enabled)
        # Eligibility is not evidence that the candidate changed a ranking.
        row["reordered_top10"] += int(candidate != baseline)
        row["changed_top3_membership"] += int(set(candidate[:3]) != set(baseline[:3]))
        row["changed_top5_membership"] += int(set(candidate[:5]) != set(baseline[:5]))
        for m in MODES:
            row["miss_reasons"][m][compared["modes"][m]["coverage_diagnostic"]] += 1
            for n in TOPS:
                hit_flag = compared["modes"][m][f"top{n}"]
                if type(hit_flag) is not bool:
                    raise ValueError("invalid_topn_flag")
                row["modes"][m][f"top{n}"] += int(hit_flag)
                if maturity == "over_60m_after_deadline":
                    row["matured_modes"][m][f"top{n}"] += int(hit_flag)
        for left, right in PAIRS:
            for n in TOPS:
                flag = f"top{n}"
                left_hit = compared["modes"][left][flag]
                right_hit = compared["modes"][right][flag]
                if type(left_hit) is not bool or type(right_hit) is not bool:
                    raise ValueError("invalid_paired_topn")
                outcome = ("both" if left_hit and right_hit else
                           "left_only" if left_hit else
                           "right_only" if right_hit else "neither")
                row["paired_modes"][f"{left}_vs_{right}"][flag][outcome] += 1
        for n in TOPS:
            row["baseline"][f"top{n}"] += int(winning in baseline[:n])
            row["candidate"][f"top{n}"] += int(winning in candidate[:n])
        row["gained_top3"] += int(winning in candidate[:3] and winning not in baseline[:3])
        row["lost_top3"] += int(winning in baseline[:3] and winning not in candidate[:3])
    output = dict(sorted(groups.items()))
    total = sum(v["comparable"] for v in output.values())
    return {"status": "v2_shadow_comparison" if total else "no_comparable_v2_yet",
            "protocol": PROTOCOL, "model_version": VERSION, "formal": False,
            "independent_remote_first_seen_verified": False,
            "v2_forecasts_seen": sum(v["forecast_files"] for v in output.values()),
            "v2_comparable": total, "groups": output, "excluded": dict(excluded),
            "changed_top3_cases": changed_top3_cases,
            "changed_top3_cases_count": len(changed_top3_cases),
            "evaluated_at_jst": now.isoformat(),
            "warning": "No official accuracy, no independent holdout, no claim of actual improvement."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed-top3-output", type=Path)
    args = parser.parse_args()
    report = evaluate()
    if args.changed_top3_output:
        cases = report.get("changed_top3_cases", [])
        args.changed_top3_output.write_text(
            json.dumps({"schema": "V2_SHADOW_CHANGED_TOP3_CASES_V1",
                        "formal": False,
                        "independent_remote_first_seen_verified": False,
                        "evaluated_at_jst": report.get("evaluated_at_jst"),
                        "count": len(cases), "cases": cases},
                       sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("V2_PREDECLARED_SHADOW=" + json.dumps(report, sort_keys=True))
