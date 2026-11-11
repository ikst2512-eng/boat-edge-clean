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
from four_mode_official_future_lineage_preflight import has_embedded_outcome

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
    if not isinstance(row, dict) or has_embedded_outcome(row):
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
            or has_embedded_outcome(bridge)):
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


def review_upstream_t12_source_pair_handoff(report):
    """Consume an already-replayed #1694 T12 source/forecast join; NO admission.

    Distinct from #1694's independent ZIP, raw HTTP, Git blob auditors:
    this is only a read-only, result-blind ④ handoff of *blockers*. The
    supplied report is not independently authenticated by this function.
    """
    if (type(report) is not dict or
            report.get("schema") != "T12_PINNED_SCHEDULED_PAIR_FROZEN_REPLAY_V1" or
            report.get("formal") is not False or
            report.get("t12_eligible") is not False or
            report.get("accuracy_scoring_allowed") is not False or
            report.get("new_formal_certifications") != 0 or
            report.get("formal_accuracy_denominator") is not None or
            report.get("same_race_complete_official_three_originals") != 0 or
            report.get("verified_model_original_byte_consumption") != 0 or
            report.get("verified_first_forecast_remote_acceptances") != 0 or
            report.get("source_originals_individually_replayed") is not True or
            report.get("original_zip_directly_rehashed_inside_ci") is not False or
            has_embedded_outcome(report)):
        raise ValueError("invalid_or_overclaimed_upstream_t12_report")
    if (type(report.get("source_run_id")) is not int or
            report["source_run_id"] <= 0 or
            type(report.get("source_artifact_id")) is not int or
            report["source_artifact_id"] <= 0 or
            type(report.get("source_original_zip_sha256_from_metadata")) is not str or
            not SHA.fullmatch(report["source_original_zip_sha256_from_metadata"]) or
            type(report.get("pinned_forecast_ref")) is not str or
            not re.fullmatch(r"[0-9a-f]{40}", report["pinned_forecast_ref"])):
        raise ValueError("unbound_upstream_source_zip_or_forecast_identity")
    try:
        published = datetime.fromisoformat(
            report["github_server_source_archive_published_at_utc"])
    except (TypeError, KeyError, ValueError) as exc:
        raise ValueError("missing_upstream_independent_source_zip_clock") from exc
    if published.utcoffset() != timedelta(0):
        raise ValueError("upstream_source_zip_clock_not_utc")
    day = report.get("day_jst")
    codes = report.get("race_rows")
    if (type(day) is not str or not re.fullmatch(r"20[0-9]{6}", day)
            or type(codes) is not list or len(codes) == 0
            or type(report.get("original_source_candidate_races")) is not int
            or len(codes) != report["original_source_candidate_races"]):
        raise ValueError("invalid_upstream_t12_roster")
    seen = set()
    per_race = []
    counts = Counter()
    pair_count = 0
    after_count = 0
    for row in codes:
        if type(row) is not dict or has_embedded_outcome(row):
            raise ValueError("unsafe_upstream_t12_race_metadata")
        code = row.get("race_code")
        if (type(code) is not str or not CODE.fullmatch(code)
                or code[:8] != day or code in seen
                or row.get("formal") is not False
                or row.get("official_racelist_original_replayed") is not False
                or row.get("model_consumption_proven") is not False
                or row.get("first_forecast_git_remote_acceptance_proven") is not False):
            raise ValueError("invalid_upstream_same_race_provenance")
        seen.add(code)
        pair = row.get("source_pair_complete_by_t12")
        if type(pair) is not bool or type(row.get("official_odds_120_verified")) is not bool:
            raise ValueError("invalid_upstream_two_source_status")
        if (pair and (row.get("official_odds_120_verified") is not True or
                      row.get("exhibition_time_observed_boats") != 6)):
            raise ValueError("contradictory_upstream_two_source_status")
        last = clock(row.get("last_original_source_received_jst"))
        cutoff = clock(row.get("official_t12_cutoff_jst"))
        if (last.date().strftime("%Y%m%d") != day
                or cutoff.date().strftime("%Y%m%d") != day
                or (pair and not last <= cutoff)
                or type(row.get("independent_source_zip_published_by_t12")) is not bool
                or row["independent_source_zip_published_by_t12"] is not
                (published + timedelta(seconds=1) <= cutoff)):
            raise ValueError("upstream_t12_source_clocks_conflict")
        forecasts = row.get("frozen_forecasts")
        if type(forecasts) is not dict or set(forecasts) != {"clean", "v2_four_mode"}:
            raise ValueError("missing_clean_and_v2_forecast_lineage")
        forecast_summary = {}
        for kind in ("clean", "v2_four_mode"):
            data = forecasts[kind]
            if (type(data) is not dict or data.get("formal") is not False
                    or data.get("first_forecast_git_remote_acceptance_verified") is not False
                    or data.get("actual_model_official_original_bytes_consumption_verified") is not False):
                raise ValueError("unverified_upstream_forecast_claim")
            generated = clock(data.get("generated_at_jst"))
            claimed_after = data.get("generated_after_pair_sources")
            claimed_cutoff = data.get("generated_before_t12")
            if (type(claimed_after) is not bool or
                    claimed_after != (generated > last) or
                    type(claimed_cutoff) is not bool or
                    claimed_cutoff != (generated <= cutoff)):
                raise ValueError("upstream_model_clock_claim_inconsistent")
            after_count += int(claimed_after)
            forecast_summary[kind] = {
                "generated_at_jst": generated.isoformat(),
                "generated_after_official_pair_sources": claimed_after,
                "generated_before_t12": claimed_cutoff,
                "official_source_byte_consumption_independently_verified": False,
                "first_forecast_remote_receipt_independently_verified": False,
            }
        pair_count += int(pair)
        blockers = []
        if not pair:
            blockers.append("beforeinfo_exhibition_six_or_odds120_or_cutoff_incomplete")
        if row["official_racelist_original_replayed"] is False:
            blockers.append("same_race_official_racelist_original_missing")
        if not forecast_summary["v2_four_mode"]["generated_after_official_pair_sources"]:
            blockers.append("v2_original_generated_before_official_pair")
        if not forecast_summary["v2_four_mode"]["generated_before_t12"]:
            blockers.append("v2_original_not_generated_before_t12")
        blockers.extend((
            "new_candidate_official_original_bytes_consumption_unverified",
            "new_candidate_independent_first_remote_receipt_unverified",
            "complete_capture_run_attempt_inventory_unverified",
            "new_future_preregistered_candidate_missing",
        ))
        for name in blockers:
            counts[name] += 1
        per_race.append({
            "race_code": code,
            "official_two_source_pair_complete_by_t12_reference_only": pair,
            "official_source_zip_published_by_t12_reference_only":
                row["independent_source_zip_published_by_t12"],
            "official_racelist_original_replayed_reference_only": False,
            "replayed_prior_forecasts": forecast_summary,
            "blocking_gates": blockers,
            "candidate_admitted_to_registered_600": False,
            "formal": False,
        })
    if (pair_count != report.get("complete_two_original_races") or
            2 * len(codes) != report.get("matched_immutable_forecasts") or
            after_count != report.get("forecasts_generated_after_originals")):
        raise ValueError("upstream_handoff_totals_disagree")
    return {
        "schema": "FOUR_MODE_OFFICIAL_T12_UPSTREAM_HANDOFF_BLOCKERS_V1",
        "status": "upstream_source_pair_replay_blockers_only",
        "upstream_auditor": "Draft_1694",
        "upstream_race_count": len(codes),
        "upstream_source_run_id": report["source_run_id"],
        "upstream_source_artifact_id": report["source_artifact_id"],
        "upstream_original_source_zip_sha256_reference_only":
            report["source_original_zip_sha256_from_metadata"],
        "upstream_pinned_forecast_commit_reference_only":
            report["pinned_forecast_ref"],
        "upstream_source_zip_published_at_utc_reference_only":
            published.isoformat(),
        "upstream_report_identity_independently_authenticated_here": False,
        "race_rows": per_race,
        "blocking_gate_counts": dict(sorted(counts.items())),
        "formal_candidate_pairs_added": 0,
        "pilot_added": 0,
        "confirmation_added": 0,
        "official_source_or_model_consumption_certified_here": False,
        "first_remote_receipt_certified_here": False,
        "formal": False,
        "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "warning": "Upstream #1694 raw-source replay is not independently "
                   "repeated here. A complete beforeinfo+odds PAIR is never "
                   "a same-race official three-source proof, nor a new "
                   "post-source candidate's first remote acceptance.",
    }


def review_upstream_pre_source_remote_existence(source_report, witness_report):
    """Join #1694's exact prior-blob remote-existence witness; no first-receipt claim.

    A GitHub Actions run created_at is an independent UPPER BOUND on the
    remote commit's existence, not the Git push's FIRST acceptance instant.
    This routine never authenticates untrusted inputs; CI separately pins
    their GitHub artifact/run and exact archive/member SHA256.
    """
    source_review = review_upstream_t12_source_pair_handoff(source_report)
    if (type(witness_report) is not dict or
            has_embedded_outcome(witness_report) or
            witness_report.get("schema") !=
                "T12_NOV10_REMOTE_ADDED_BLOB_WITNESS_V1" or
            witness_report.get("formal") is not False or
            witness_report.get("accuracy_scoring_allowed") is not False or
            witness_report.get("exact_first_remote_git_acceptance_instants_verified") != 0 or
            witness_report.get("forecasts_proven_to_consume_official_originals") != 0 or
            witness_report.get("full_three_source_forecasts_verified") != 0 or
            witness_report.get("new_formal_certifications") != 0 or
            witness_report.get("formal_accuracy_denominator") is not None):
        raise ValueError("untrusted_or_overclaimed_remote_existence_witness")

    witness_rows = witness_report.get("race_rows")
    source_rows = source_report["race_rows"]
    expected = {r["race_code"] for r in source_rows}
    if (source_report.get("day_jst") != "20261110" or
            type(witness_rows) is not list or
            len(witness_rows) != len(source_rows) or
            witness_report.get("source_races") != len(source_rows) or
            witness_report.get("immutable_forecast_blobs_witnessed") !=
                2 * len(source_rows) or
            witness_report.get("remote_commit_existed_before_official_sources") !=
                2 * len(source_rows) or
            {r.get("race_code") for r in witness_rows if type(r) is dict}
                != expected):
        raise ValueError("remote_witness_cross_race_or_count_mismatch")

    seen = set()
    pinned_mode_commit = {}
    pinned_mode_run = {}
    joined_rows = []
    verified_bounds = 0
    mode_folders = {"clean": "prospective_predictions",
                    "v2_four_mode": "four_mode_forecasts"}
    for row in witness_rows:
        if (type(row) is not dict or row.get("race_code") in seen or
                row.get("formal") is not False):
            raise ValueError("remote_witness_duplicate_or_formal")
        code = row["race_code"]
        seen.add(code)
        original = next(r for r in source_rows if r["race_code"] == code)
        published = clock(original["last_original_source_received_jst"])
        cutoff = clock(original["official_t12_cutoff_jst"])
        if (clock(row.get("last_source_received_jst")) != published or
                clock(row.get("official_t12_cutoff_jst")) != cutoff):
            raise ValueError("remote_witness_source_clocks_not_same_race")
        forecasts = row.get("forecasts")
        if type(forecasts) is not dict or set(forecasts) != set(mode_folders):
            raise ValueError("remote_witness_both_prior_forecasts_required")
        modes = {}
        for mode, folder in mode_folders.items():
            item = forecasts[mode]
            if (type(item) is not dict or item.get("formal") is not False or
                    item.get("added_path") != f"{folder}/{code}.json" or
                    item.get("exact_file_git_blob_sha1_matched") is not True or
                    item.get("existing_blob_predates_official_source") is not True or
                    item.get("first_remote_acceptance_instant_proven") is not False or
                    item.get("actual_original_byte_model_consumption_proven") is not False):
                raise ValueError("remote_witness_prior_blob_identity_or_false_proof")
            commit = item.get("added_git_commit")
            run_id = item.get("independent_github_run_id")
            if (type(commit) is not str or
                    re.fullmatch(r"[0-9a-f]{40}", commit) is None or
                    type(run_id) is not int or run_id <= 0):
                raise ValueError("remote_witness_unbound_commit_or_run")
            try:
                existed_by = datetime.fromisoformat(
                    item["github_remote_existed_no_later_utc"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("missing_remote_existence_clock") from exc
            generated = clock(
                original["frozen_forecasts"][mode]["generated_at_jst"])
            if (existed_by.utcoffset() != timedelta(0) or
                    not generated <= existed_by < published or
                    not existed_by < cutoff):
                raise ValueError("remote_existence_does_not_precede_official_sources")
            if mode in pinned_mode_commit and (
                    pinned_mode_commit[mode] != commit or
                    pinned_mode_run[mode] != run_id):
                raise ValueError("remote_witness_cross_race_commit_substitution")
            pinned_mode_commit[mode] = commit
            pinned_mode_run[mode] = run_id
            verified_bounds += 1
            modes[mode] = {
                "file_added_relative_to_commit_parent_reference_only": True,
                "witness_git_commit_reference_only": commit,
                "witness_actions_run_id_reference_only": run_id,
                "github_commit_existed_no_later_utc_reference_only":
                    existed_by.isoformat(),
                "original_blob_existed_before_official_pair_reference_only": True,
                "independent_first_remote_acceptance_instant_verified": False,
                "official_original_bytes_consumed_by_model": False,
                "candidate_eligible_for_registered_600": False,
            }
        joined_rows.append({
            "race_code": code,
            "original_beforeinfo_odds_pair_complete_by_t12_reference_only":
                original["source_pair_complete_by_t12"],
            "same_race_official_racelist_original_present": False,
            "prior_forecast_remote_existence_bounds": modes,
            "existing_forecast_disqualified_from_post_source_study": True,
            "blocking_gates": next(
                x["blocking_gates"] for x in source_review["race_rows"]
                if x["race_code"] == code),
            "formal": False,
        })
    return {
        "schema": "FOUR_MODE_PRIOR_REMOTE_EXISTENCE_CAUSAL_ORDER_HANDOFF_V1",
        "status": "old_forecast_exists_before_official_pair_NOT_FIRST_REMOTE",
        "upstream_source_report_run_id": source_review["upstream_source_run_id"],
        "upstream_source_artifact_id": source_review["upstream_source_artifact_id"],
        "old_forecast_commit_existence_upper_bounds": verified_bounds,
        "first_remote_git_acceptance_instants_proven": 0,
        "new_source_consuming_candidate_forecasts": 0,
        "new_forecast_remote_acceptance_verified": 0,
        "race_rows": sorted(joined_rows, key=lambda r: r["race_code"]),
        "upstream_witness_archive_independently_authenticated_here": False,
        "pilot_added": 0,
        "confirmation_added": 0,
        "formal_candidate_pairs_added": 0,
        "formal": False,
        "model_improvement_proven": False,
        "model_promotion_allowed": False,
        "warning": "An independently observed GitHub run is an upper bound "
                   "on a prior commit's REMOTE EXISTENCE, never the FIRST Git "
                   "push acceptance instant. Those unchanged prior forecast "
                   "blobs cannot consume later official raw originals.",
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
    ap.add_argument("--upstream-t12-report",type=Path,
                    help="Read-only #1694 T12 same-race blocker handoff; no result scoring")
    ap.add_argument("--upstream-remote-witness",type=Path,
                    help="Optional paired #1694 Git remote-existence upper-bound report")
    args=ap.parse_args()
    p=protocol_check(json.loads(PROTOCOL.read_text(encoding="utf-8")))
    if args.upstream_t12_report is not None:
        if args.pre_result_roster is not None or args.results is not None:
            raise ValueError("upstream_t12_handoff_must_not_mix_with_result_scoring")
        target = args.upstream_t12_report
        if target.is_symlink() or not target.is_file() or target.stat().st_size > 2_000_000:
            raise ValueError("invalid_upstream_t12_report_file")
        source_report = json.loads(target.read_text(encoding="utf-8"))
        if args.upstream_remote_witness is not None:
            witness_path = args.upstream_remote_witness
            if (witness_path.is_symlink() or not witness_path.is_file() or
                    witness_path.stat().st_size > 2_000_000):
                raise ValueError("invalid_upstream_remote_witness_file")
            report = review_upstream_pre_source_remote_existence(
                source_report, json.loads(witness_path.read_text(encoding="utf-8")))
        else:
            report = review_upstream_t12_source_pair_handoff(source_report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return
    if args.upstream_remote_witness is not None:
        raise ValueError("remote_witness_requires_upstream_t12_report")
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
