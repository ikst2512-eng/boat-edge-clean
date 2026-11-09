"""Result-last four-mode forward comparison. Read-only and NEVER formal evidence."""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from math import comb, isfinite
from pathlib import Path

from collect_clean_results import BASE as CONFIRMED_RESULT_SOURCE_BASE

PROTOCOL = Path(__file__).resolve().parent / "research/four_mode_all_modes_forward_protocol_20261106.json"
COUNTS = {"narrow": 5, "hit": 10, "balance": 16, "hole": 22}
TOPS = (1, 3, 5, 10)
CODE = re.compile(r"20\d{6}(?:0[1-9]|1\d|2[0-4])(?:0[1-9]|1[0-2])\Z")
COMBO = re.compile(r"[1-6]-[1-6]-[1-6]\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
PROTOCOL_SHA256 = "ed94706b9b9bb3194f5e89e358c23df46b1f704b5d84cdf44bc9a225b24b91ff"


def clock(value):
    try:
        d = datetime.fromisoformat(value)
    except (TypeError, ValueError) as e:
        raise ValueError("invalid_clock") from e
    if d.utcoffset() != timedelta(hours=9):
        raise ValueError("non_JST_clock")
    return d


def protocol_check(p):
    if type(p) is not dict:
        raise ValueError("invalid_protocol")
    canonical = json.dumps(p, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("changed_forward_protocol")
    return p


def validate_tickets(v, size):
    if not isinstance(v, list) or len(v) != size or len(set(map(str, v))) != size or any(
        not isinstance(t, str) or not COMBO.fullmatch(t) or len(set(t.split("-"))) != 3 for t in v
    ):
        raise ValueError("invalid_or_changed_ticket_budget")
    return v


def freeze(row, p):
    if not isinstance(row, dict) or any(k in row for k in
       ("result", "finish_order", "winning_ticket", "confirmed_at_jst", "payout")):
        raise ValueError("outcome_leak_in_pre_result_roster")
    # A future scenario-conditional model is a DISTINCT unregistered study.
    # Its presence must never silently consume the 2026-11-06 frozen 600 slots.
    if ("scenario_bridge" in row or "scenario_candidate_study_id" in row
            or "unregistered_scenario_model" in row):
        raise ValueError("scenario_candidate_requires_separate_future_registration")
    code = row.get("race_code")
    if not isinstance(code, str) or not CODE.fullmatch(code):
        raise ValueError("invalid_race_code")
    deadline = clock(row.get("deadline_jst"))
    if (not clock(p["eligible_deadline_start_jst"]) <= deadline <= clock(p["eligible_deadline_end_jst"])
        or deadline.strftime("%Y%m%d") != code[:8] or row.get("model_version") != p["model_version"]):
        raise ValueError("date_or_model_version_mismatch")
    cutoff = deadline - timedelta(minutes=12)
    try:
        source = clock(row["official_source_received_jst"])
        bg = clock(row["baseline_generated_jst"])
        bo = clock(row["baseline_github_observed_jst"])
        cg = clock(row["candidate_generated_jst"])
        co = clock(row["candidate_github_observed_jst"])
    except KeyError as e:
        raise ValueError("missing_clock") from e
    # The original must be remotely observable BEFORE the candidate is
    # generated. GitHub's Date header has one-second resolution, so require
    # a full-second gap around both original and candidate observations.
    if not (source < bg and
            bg + timedelta(seconds=1) < bo and
            bo + timedelta(seconds=1) < cg and
            cg + timedelta(seconds=1) < co < cutoff):
        raise ValueError("late_or_same_second_T12")
    if (row.get("official_beforeinfo_complete_6") is not True or
        row.get("official_exhibition_complete_6") is not True or
        row.get("official_odds_complete_120") is not True or
        row.get("result_based_features_used") is not False):
        raise ValueError("incomplete_or_postrace_feature")
    if any(not isinstance(row.get(key), str) or not SHA.fullmatch(row[key]) for key in
           ("source_sha256", "original_forecast_sha256", "candidate_method_sha256")):
        raise ValueError("unanchored_source_or_method")
    selectors = row.get("mode_candidate_selector_sha256")
    if not isinstance(selectors, dict) or set(selectors) != set(COUNTS) or any(
        not isinstance(v, str) or not SHA.fullmatch(v) for v in selectors.values()
    ):
        raise ValueError("missing_four_mode_selectors")
    for kind in ("baseline", "candidate"):
        if not isinstance(row.get(kind), dict) or set(row[kind]) != set(COUNTS):
            raise ValueError("missing_four_modes")
        for mode,size in COUNTS.items():
            validate_tickets(row[kind][mode], size)
    if row.get("formal") is True or row.get("model_improvement_proven") is True:
        raise ValueError("forged_formal_status")
    return {"code": code, "deadline": deadline, "baseline": row["baseline"],
            "candidate": row["candidate"], "selectors": tuple(sorted(selectors.items())),
            "method": row["candidate_method_sha256"],
            "source_digest": row["source_sha256"],
            "original_digest": row["original_forecast_sha256"],
            "source_received_jst": source.isoformat(),
            "baseline_generated_jst": bg.isoformat(),
            "baseline_github_observed_jst": bo.isoformat(),
            "candidate_generated_jst": cg.isoformat(),
            "candidate_github_observed_jst": co.isoformat()}


def exact_mcnemar_two_sided_reference(gained, lost):
    """Conditional exact two-sided binomial p on discordant SAME-race pairs.

    This is only numerical machinery; provenance of input observations is
    never authenticated by a p-value. No optional testing or early stopping.
    """
    if (type(gained) is not int or type(lost) is not int or
            min(gained, lost) < 0 or gained + lost > 300):
        raise ValueError("invalid_paired_discordance_for_300_confirmation")
    discordant = gained + lost
    if discordant == 0:
        return 1.0
    smaller = min(gained, lost)
    return min(1.0, 2 * sum(comb(discordant, k)
                           for k in range(smaller + 1)) / (2 ** discordant))


def confirmation_holm_reference(scores, phase_progress, dates, policy):
    """Locked four-mode Top10 two-sided Holm arithmetic; NEVER certification."""
    target_pilot = policy["pilot_races"]
    target_confirm = policy["confirmation_races"]
    required_dates = policy["minimum_distinct_confirmation_dates"]
    expected_policy = "four_mode_top10_holm_two_sided_0.05"
    if (target_pilot != 300 or target_confirm != 300 or
            required_dates != 5 or
            policy["multiple_comparisons"] != expected_policy):
        raise ValueError("unsupported_registered_confirmation_design")
    available_days = sorted(set(dates))
    answer = {
        "status": "not_ready",
        "formal": False,
        "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "primary_metric": "paired_top10_exact_trifecta",
        "correction": expected_policy,
        "distinct_confirmed_confirmation_dates": len(available_days),
        "confirmed_confirmation_dates_reference_only": available_days,
        "minimum_distinct_confirmation_dates": required_dates,
        "comparison_count": 4,
        "p_values_reference_only": None,
        "holm_reject_reference_only": None,
        "candidate_positive_and_holm_reference_only": None,
        "warning": "Numerical result-only reference; candidate FIRST remote receipt, "
                   "official T-12 provenance and complete attempts are NOT attested.",
    }
    if any(phase_progress[name]["matched_result_pairs_reference_only"] != size
           for name, size in (("pilot", target_pilot),
                              ("confirmation", target_confirm))):
        answer["status"] = "pilot_or_confirmation_not_fully_scored_reference"
        return answer
    if len(available_days) < required_dates:
        answer["status"] = "insufficient_distinct_confirmation_dates"
        return answer
    pvals = {
        mode: exact_mcnemar_two_sided_reference(
            scores["confirmation"][mode]["top10"]["gained"],
            scores["confirmation"][mode]["top10"]["lost"])
        for mode in COUNTS
    }
    ordered = sorted(pvals, key=lambda mode: (pvals[mode], mode))
    rejected = {}
    stopped = False
    for index, mode in enumerate(ordered):
        threshold = 0.05 / (len(ordered) - index)
        reject = (not stopped and pvals[mode] <= threshold)
        rejected[mode] = reject
        if not reject:
            stopped = True
    answer["status"] = "numerical_holm_reference_only_not_certified"
    answer["p_values_reference_only"] = pvals
    answer["holm_reject_reference_only"] = rejected
    answer["candidate_positive_and_holm_reference_only"] = {
        mode: rejected[mode] and
              scores["confirmation"][mode]["top10"]["gained"] >
              scores["confirmation"][mode]["top10"]["lost"]
        for mode in COUNTS
    }
    return answer


def preflight_unregistered_scenario_bridge(baseline, bridge):
    """Result-blind INTERFACE ONLY for separate #1710 all-mode scenario Draft.

    This does not run the scenario model, parse official sources, read outcomes,
    preregister a method, or add ANY race to the locked #1693 cohort.
    """
    if type(baseline) is not dict or set(baseline) != set(COUNTS):
        raise ValueError("missing_four_mode_original")
    if (type(bridge) is not dict or
            bridge.get("schema") != "ALL_MODE_SCENARIO_BRIDGE_EXPLORATORY_V1" or
            type(bridge.get("mixed_120_board_sha256")) is not str or
            not SHA.fullmatch(bridge["mixed_120_board_sha256"]) or
            bridge.get("mode_ticket_budgets") != COUNTS):
        raise ValueError("invalid_unregistered_scenario_bridge_identity")
    must_be_false = (
        "source_feature_provenance_independently_verified",
        "verified_official_six_exhibition_and_120_odds",
        "first_remote_receipt_verified",
        "scenario_weights_calibrated",
        "probabilities_calibrated",
        "confirmed_results_read",
        "formal",
        "forecast_usable",
        "betting_recommendation",
        "production_changed",
        "model_improvement_proven",
        "promotion_allowed",
    )
    if (any(bridge.get(field) is not False for field in must_be_false)
            or any(field in bridge for field in (
                "finish_order", "confirmed_result", "winning_ticket", "payout"))):
        raise ValueError("outcome_or_forged_scenario_certification")
    modes = bridge.get("existing_four_mode_selector_on_mixture")
    if type(modes) is not dict or set(modes) != set(COUNTS):
        raise ValueError("missing_scenario_four_mode_tickets")
    contrast = {}
    for mode, size in COUNTS.items():
        old = validate_tickets(baseline[mode], size)
        new = modes[mode].get("tickets") if type(modes[mode]) is dict else None
        if type(new) is not list or len(new) != size:
            raise ValueError("invalid_scenario_mode_rows")
        candidate = []
        for item in new:
            if (type(item) is not dict or
                    type(item.get("combo")) is not str or
                    type(item.get("p")) not in (int, float) or
                    not isfinite(item["p"]) or not 0 <= item["p"] <= 100):
                raise ValueError("invalid_scenario_mode_ticket")
            candidate.append(item["combo"])
        validate_tickets(candidate, size)
        top = {}
        for k in TOPS:
            old_top, new_top = set(old[:k]), set(candidate[:k])
            top[f"top{k}"] = {
                "requested_topn": k,
                "effective_ticket_count": min(k, size),
                "requested_topn_exceeds_mode_budget": k > size,
                "original_ticket_count": len(old_top),
                "scenario_ticket_count": len(new_top),
                "unchanged_ticket_count": len(old_top & new_top),
                "new_tickets_not_hits": len(new_top - old_top),
                "removed_tickets_not_losses": len(old_top - new_top),
                "membership_changed": old_top != new_top,
            }
        contrast[mode] = {
            "top1_exact_combo_changed": old[0] != candidate[0],
            "top1_first_boat_changed": old[0][0] != candidate[0][0],
            "topn_exposure_result_blind": top,
        }
    return {
        "status": "unregistered_scenario_bridge_exposure_only",
        "source_namespace": "separate_draft_1710",
        "self_reported_mixed_120_board_sha256": bridge["mixed_120_board_sha256"],
        "comparison": contrast,
        "confirmed_results_read": False,
        "winning_hit_gain_or_loss_computed": False,
        "candidate_eligible_for_1693_registered_600": False,
        "requires_new_future_only_preregistration": True,
        "official_source_lineage_independently_verified": False,
        "independent_first_remote_receipt_verified": False,
        "formal": False,
        "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "warning": "Only ticket-set exposure from caller supplied, unregistered "
                   "scenario output. No inferred weather/entry/tide validity, "
                   "TopN outcome accuracy or candidate lineage.",
    }


def score(pre_result_rows, results, p):
    protocol_check(p)
    if not isinstance(pre_result_rows,list) or not isinstance(results,dict):
        raise ValueError("invalid_inputs")
    roster = {}
    excluded = Counter()
    for item in pre_result_rows:
        try:
            row = freeze(item,p)
        except (ValueError,KeyError,TypeError) as e:
            excluded[str(e)] += 1
            continue
        if row["code"] in roster:
            raise ValueError("duplicate_candidate")
        roster[row["code"]] = row
    # Do not silently replace a rejected pre-result candidate with a later race
    # to fill the fixed 300+300 cohort. An incomplete mixed roster is unscorable.
    if excluded and roster:
        raise ValueError("incomplete_candidate_roster_no_replacement")
    # All selector and method bytes must be fixed BEFORE any result lookup.
    if len({(r["selectors"],r["method"]) for r in roster.values()}) > 1:
        raise ValueError("selector_changed_across_future_races")
    # Build the reference roster identity entirely from pre-result information.
    # Stable across caller ordering / outcome arrival, but NOT an independently
    # time-stamped freeze or an authenticated first remote receipt.
    ordered_all = sorted(roster.values(), key=lambda r: (r["deadline"], r["code"]))
    fixed_capacity = p["pilot_races"] + p["confirmation_races"]
    ordered = ordered_all[:fixed_capacity]
    pre_result_manifest = [
        {
            "race_code": row["code"],
            "deadline_jst": row["deadline"].isoformat(),
            "source_sha256": row["source_digest"],
            "original_forecast_sha256": row["original_digest"],
            "self_reported_pre_result_chronology_jst": {
                "official_source_received_jst": row["source_received_jst"],
                "baseline_generated_jst": row["baseline_generated_jst"],
                "baseline_github_observed_jst": row["baseline_github_observed_jst"],
                "candidate_generated_jst": row["candidate_generated_jst"],
                "candidate_github_observed_jst": row["candidate_github_observed_jst"],
            },
            "candidate_method_sha256": row["method"],
            "mode_candidate_selector_sha256": dict(row["selectors"]),
            "baseline": row["baseline"],
            "candidate": row["candidate"],
        }
        for row in ordered
    ]
    reference_roster_sha256 = (
        hashlib.sha256(json.dumps(pre_result_manifest, sort_keys=True,
                                  separators=(",", ":"), ensure_ascii=False)
                       .encode("utf-8")).hexdigest()
        if pre_result_manifest else None
    )
    scores = {phase:{m:{f"top{k}":{"baseline":0,"candidate":0,"gained":0,"lost":0}
                   for k in TOPS} for m in COUNTS} for phase in ("pilot","confirmation")}
    # This scorer is NEVER a formal certifier. Report phase progress separately
    # from the official 300+300 study to avoid promoting replayed evidence.
    # A pending/invalid outcome reserves its pre-result roster slot.
    phase_slots = {
        "pilot": len(ordered[:p["pilot_races"]]),
        "confirmation": len(ordered[p["pilot_races"]:p["pilot_races"] + p["confirmation_races"]]),
    }
    pending_by_phase = Counter()
    invalid_by_phase = Counter()
    confirmed_dates_by_phase = {"pilot": set(), "confirmation": set()}
    matched = Counter(); pending = []; bad = Counter()
    for index,row in enumerate(ordered):
        code = row["code"]
        phase = "pilot" if index < p["pilot_races"] else "confirmation"
        if code not in results or results[code] is None:
            pending.append(code)
            pending_by_phase[phase] += 1
            continue
        outcome = results[code]
        try:
            expected_result_url = (CONFIRMED_RESULT_SOURCE_BASE + code[:4] + "/"
                                   + code[4:6] + "/" + code[6:8] + ".csv")
            if not isinstance(outcome,dict):
                raise ValueError("untrusted_result_or_time")
            confirmed = clock(outcome.get("confirmed_at_jst"))
            collected = clock(outcome.get("collected_at_jst"))
            if (outcome.get("race_code") != code or
                outcome.get("status") != "confirmed" or
                outcome.get("source_url") != expected_result_url or
                not isinstance(outcome.get("source_sha256"),str) or
                not SHA.fullmatch(outcome["source_sha256"]) or
                confirmed <= row["deadline"] or
                collected < confirmed):
                raise ValueError("untrusted_result_or_time")
            finish = outcome.get("finish_order")
            if (type(finish) is not list or len(finish) != 3 or
                any(type(x) is not int or not 1<=x<=6 for x in finish) or len(set(finish)) != 3):
                raise ValueError("invalid_finish")
        except (ValueError,KeyError,TypeError) as e:
            bad[str(e)] += 1
            invalid_by_phase[phase] += 1
            continue
        matched[phase] += 1
        confirmed_dates_by_phase[phase].add(row["deadline"].date().isoformat())
        winning = "-".join(map(str,finish))
        for mode in COUNTS:
            for k in TOPS:
                a = winning in row["baseline"][mode][:k]
                b = winning in row["candidate"][mode][:k]
                c = scores[phase][mode][f"top{k}"]
                c["baseline"] += int(a); c["candidate"] += int(b)
                c["gained"] += int(b and not a); c["lost"] += int(a and not b)
    for phase in scores:
        for mode in scores[phase]:
            for k in TOPS:
                c = scores[phase][mode][f"top{k}"]
                n = matched[phase]
                c["denominator_reference_only"] = n
                c["requested_topn"] = k
                c["effective_ticket_count"] = min(k, COUNTS[mode])
                c["requested_topn_exceeds_mode_budget"] = k > COUNTS[mode]
                if c["candidate"]-c["baseline"] != c["gained"]-c["lost"]:
                    raise ValueError("paired_score_mismatch")
                both = c["baseline"] - c["lost"]
                neither = n - both - c["gained"] - c["lost"]
                if min(both, neither) < 0:
                    raise ValueError("paired_partition_mismatch")
                c["both_hit_reference_only"] = both
                c["neither_hit_reference_only"] = neither
                c["paired_discordant_reference_only"] = c["gained"] + c["lost"]
                # Descriptive rates ONLY: do not run inferential tests or
                # market "precision" until independent formal cohort audit.
                c["baseline_hit_pct_reference_only"] = (
                    round(100 * c["baseline"] / n, 2) if n else None)
                c["candidate_hit_pct_reference_only"] = (
                    round(100 * c["candidate"] / n, 2) if n else None)
                c["net_gain_pp_reference_only"] = (
                    round(100 * (c["gained"] - c["lost"]) / n, 2) if n else None)
    phase_progress = {}
    for phase, target in (("pilot", p["pilot_races"]),
                          ("confirmation", p["confirmation_races"])):
        reserved = phase_slots[phase]
        confirmed = matched[phase]
        waiting = pending_by_phase[phase]
        invalid = invalid_by_phase[phase]
        if reserved != confirmed + waiting + invalid:
            raise ValueError("phase_roster_result_partition_mismatch")
        phase_progress[phase] = {
            "target": target,
            "reserved_pre_result_slots_reference_only": reserved,
            "unreserved_slots": target - reserved,
            "matched_result_pairs_reference_only": confirmed,
            "pending_result_slots": waiting,
            "invalid_result_slots": invalid,
            "reference_status": (
                "not_started" if reserved == 0 else
                "reference_complete_nonformal" if reserved == target and
                confirmed == target else "collecting_reference_only"),
            "formal_status": "not_started_unverified_first_receipt_and_official_T12",
            "formally_certified_pairs": 0,
        }
    holm_reference = confirmation_holm_reference(
        scores, phase_progress, confirmed_dates_by_phase["confirmation"], p)
    # Descriptive across-mode/TopN *regression visibility* is not a newly
    # preregistered significance test, nor an alteration of Top10 primary.
    # No rates or "no regression" claim when no valid outcomes exist.
    regression_diagnostics = {}
    for phase in ("pilot", "confirmation"):
        n = matched[phase]
        by_mode = {}
        for mode in COUNTS:
            diffs = {f"top{k}": (
                scores[phase][mode][f"top{k}"]["gained"] -
                scores[phase][mode][f"top{k}"]["lost"])
                for k in TOPS}
            by_mode[mode] = {
                "evaluated_matched_results_reference_only": n,
                "net_hit_changes_by_topn_reference_only": (
                    diffs if n else None),
                "topn_with_fewer_hits_reference_only": (
                    [name for name, delta in diffs.items() if delta < 0]
                    if n else None),
                "any_topn_with_fewer_hits_reference_only": (
                    any(delta < 0 for delta in diffs.values()) if n else None),
                "top10_primary_net_change_reference_only": (
                    diffs["top10"] if n else None),
            }
        regression_diagnostics[phase] = {
            "status": ("descriptive_only_not_a_release_gate" if n
                       else "unavailable_without_matched_results"),
            "same_race_denominator_reference_only": n,
            "modes": by_mode,
            "any_mode_topn_with_fewer_hits_reference_only": (
                any(v["any_topn_with_fewer_hits_reference_only"]
                    for v in by_mode.values()) if n else None),
            "warning": "A positive Top10 gain can coincide with worse "
                       "Top1/3/5. These exploratory counts are not "
                       "prespecified secondary significance tests.",
        }
    return {"status":"reference_only_not_certified", "formal":False,
            "model_improvement_proven":False, "model_promotion_allowed":False,
            "independent_first_remote_receipt_verified":False,
            "complete_capture_run_inventory_verified":False,
            "eligible_roster_count":len(ordered), "matched_by_phase":dict(matched),
            "phase_progress":phase_progress,
            "confirmation_top10_holm_reference_only":holm_reference,
            "topn_regression_diagnostics_reference_only":regression_diagnostics,
            "selected_pre_result_roster_sha256_reference_only":reference_roster_sha256,
            "valid_pre_result_candidate_records_reference_only":len(ordered_all),
            "candidate_records_after_fixed_600_not_scored":len(ordered_all)-len(ordered),
            "pending_result_codes":pending,"invalid_result_counts":dict(bad),
            "excluded_before_result_read":dict(excluded),"scores":scores,
            "warning":"GitHub observation != first remote receipt. This script cannot authenticate supplied SHA or timestamps. No formal/prospective performance without independent source bytes and complete capture-run inventory."}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pre-result-roster",type=Path)
    ap.add_argument("--results",type=Path)
    args=ap.parse_args()
    p=protocol_check(json.loads(PROTOCOL.read_text(encoding="utf-8")))
    if args.pre_result_roster is None or args.results is None:
        # The normal no-input CI path must expose explicit 0/300 + 0/300
        # status instead of displaying only a generic valid-protocol flag.
        report = score([], {}, p)
        report["status"] = "protocol_valid_no_future_records_scored"
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return
    print(json.dumps(score(json.loads(args.pre_result_roster.read_text(encoding="utf-8")),
                           json.loads(args.results.read_text(encoding="utf-8")),p),ensure_ascii=False,sort_keys=True))


if __name__ == "__main__":
    main()
