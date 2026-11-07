"""Verify a precommitted forward research protocol; NEVER score unsourced live races.

This is a research-plan verifier, not an acquisition or a first-receipt
attestor. No completed forecasts are claimed or inferred from an empty input.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROTOCOL = ROOT / "research" / "forward_hole_rank3_protocol_20261105.json"
SOURCE = ROOT / "hole_upper_rank_pair_protection.py"
SCHEMA = "BOAT_EDGE_HOLE_RANK3_FORWARD_STUDY_PREDECLARATION_V1"
SELECTOR_BLOB = "a2613df6cd58e3c8477df7e03d88d82298ef7fee"

def _read_json(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or not 100 <= p.stat().st_size < 15000:
        raise ValueError("protocol_missing_or_unsafe")
    raw = p.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("protocol_malformed") from exc
    if type(parsed) is not dict:
        raise ValueError("protocol_not_object")
    return parsed, hashlib.sha256(raw).hexdigest()

def _git_blob_sha1(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def validate(path=PROTOCOL, source=SOURCE):
    p, manifest_sha256 = _read_json(path)
    sel = p.get("selector")
    ev = p.get("evaluation")
    end = p.get("endpoint")
    evidence = p.get("include_only_if")
    governing = p.get("governance")
    if (p.get("schema") != SCHEMA
            or p.get("study_id") != "hole-hit-rank3-paired-top10-20261105-v1"
            or p.get("predeclaration_race_date_jst") != "2026-11-05"
            or p.get("first_race_date_jst") != "2026-11-05"
            or p.get("last_race_date_jst") != "2026-12-31"
            or p.get("remote_protocol_observation_before_jst") != "2026-11-05T07:00:00+09:00"
            or type(p.get("first_n_eligible_races")) is not int
            or p["first_n_eligible_races"] != 300
            or p.get("sample_order") != "deadline_jst_ascending_then_race_code_ascending"
            or p.get("research_only") is not True
            or any(p.get(k) is not False for k in (
                "formal", "remote_first_seen_verified",
                "production_forecast_changed", "model_improvement_proven"))):
        raise ValueError("protocol_contract_changed")
    if (type(sel) is not dict
            or sel.get("source_file") != "hole_upper_rank_pair_protection.py"
            or sel.get("function") != "propose"
            or sel.get("git_blob_sha1") != SELECTOR_BLOB
            or sel.get("algorithm_id") != "hole_upper_rank_pair_protection.propose:hit_rank3:v1"
            or sel.get("baseline_mode") != "hole"
            or sel.get("donor_mode") != "hit"
            or type(sel.get("maximum_tickets")) is not int or sel["maximum_tickets"] != 10
            or type(sel.get("insert_rank")) is not int or sel["insert_rank"] != 3
            or sel.get("protected_ranks") != [1, 2]
            or sel.get("preserve_existing_first_second_pairs") is not True
            or sel.get("selection_after_outcome_forbidden") is not True
            or sel.get("scoring_uses_saved_original_tickets_only") is not True):
        raise ValueError("predeclared_selector_changed")
    f = Path(source)
    if f.is_symlink() or not f.is_file() or f.stat().st_size > 100000:
        raise ValueError("selector_unavailable_or_unsafe")
    actual_blob = _git_blob_sha1(f.read_bytes())
    if not re.fullmatch(r"[0-9a-f]{40}", actual_blob) or actual_blob != SELECTOR_BLOB:
        raise ValueError("selector_code_mismatch")
    if (type(ev) is not dict
            or ev.get("design") != "fixed_sample_paired_before_after_no_early_claim"
            or ev.get("test") != "two_sided_exact_McNemar_binomial_on_discordant_top10"
            or type(ev.get("alpha")) is not float or ev["alpha"] != 0.05
            or type(ev.get("min_n_for_efficacy_claim")) is not int
            or ev["min_n_for_efficacy_claim"] != 300
            or any(ev.get(k) is not True for k in (
                "must_have_positive_net_gained_minus_lost",
                "secondary_topn_exploratory_only", "no_optional_stopping",
                "no_multiple_scenario_search"))):
        raise ValueError("statistics_contract_changed")
    if (type(end) is not dict or end.get("primary") != "top10_exact_trifecta_coverage"
            or end.get("secondary_descriptive") != ["top1", "top3", "top5"]
            or end.get("denominator") != "same_eligible_race_codes_for_baseline_and_candidate"
            or end.get("report_per_race") is not True
            or end.get("report_gained_lost") is not True):
        raise ValueError("metric_contract_changed")
    prereg_enrollment = {
        "decision_inputs": "verified_pre_result_archive_and_saved_shadow_and_remote_observation_only",
        "first_n_pre_result_eligible_races": 300,
        "first_n_order": "deadline_jst_ascending_then_race_code_ascending",
        "no_results_payouts_or_postrace_indicators_allowed": True,
        "pending_result_retains_original_enrolled_slot": True,
        "no_replacing_enrolled_races_with_later_winning_races": True,
        "no_early_optional_peek_for_efficacy": True,
        "pre_result_roster_complete_only_if_run_inventory_exhaustive": True,
        "insufficient_300_before_study_end_remains_inconclusive": True,
    }
    if p.get("enrollment") != prereg_enrollment:
        raise ValueError("pre_result_enrollment_contract_changed")
    if (type(p.get("protocol_refinement_note")) is not str
            or not p["protocol_refinement_note"].startswith(
                "Pre-result 300-member enrollment clarified on 2026-11-05 JST")):
        raise ValueError("amendment_disclosure_missing")
    required_evidence = {
        "source_forecast": "immutable_v2_four_mode_first_add_original",
        "source_and_model_inputs": "original_receipts_valid_and_six_boats",
        "frozen_candidate": "same_collection_job_before_T_minus_12_from_source_original",
        "github_server_observation": "exact_original_blob_observed_before_T_minus_12_with_trusted_server_date",
        "confirmed_outcome": "independently_persisted_valid_result_after_race",
        "complete_inventory": "all_in_scope_collection_runs_and_evidence_checked_no_silent_omissions",
    }
    if evidence != required_evidence:
        raise ValueError("future_evidence_gate_changed")
    for guard in ("no_production_change_without_manual_review",
                  "gemini_suggestions_not_eligible_for_this_precommitted_cohort",
                  "refuse_if_less_than_full_n", "refuse_if_evidence_or_run_inventory_incomplete",
                  "official_accuracy_requires_separate_independent_certification",
                  "github_server_observation_does_not_prove_first_receipt",
                  "trial_registration_does_not_certify_any_actual_forecast"):
        if type(governing) is not dict or governing.get(guard) is not True:
            raise ValueError("governance_guard_missing")
    return {
        "status": "forward_protocol_recorded_not_scored",
        "schema": SCHEMA,
        "study_id": p["study_id"],
        "minimum_future_verified_pairs_required": 300,
        "membership_selected_before_outcomes": True,
        "pending_result_preserves_member": True,
        "selector_git_blob_sha1": actual_blob,
        "protocol_sha256": manifest_sha256,
        "prospective_results_checked": False,
        "future_capture_inventory_checked": False,
        "actual_future_eligible_race_count": None,
        "model_improvement_proven": False,
        "formal": False,
        "production_promotion_allowed": False,
        "warning": ("Pre-registration alone does not prove it preceded every frozen race; "
                    "confirm protocol GitHub server observation vs race cutoff independently. "
                    "No evaluation or formal success until actual immutable forecasts, "
                    "remote observation, original source, results and run inventory are audited.")
    }

if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, sort_keys=True))
