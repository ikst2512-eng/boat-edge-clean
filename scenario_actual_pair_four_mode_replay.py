"""Real beforeinfo 2-original -> existing #1710 x #1698 4-mode research math.

Pinned 11/9-10 original ZIPs only; neutral power rates and explicit scenario
weights are HYPOTHESES, not predictions. No results, model training, HTTP
collector, site output or saved forecast writes. 4th race fails closed.
"""
import argparse
import copy
import importlib
import json
from pathlib import Path

from scenario_official_pair_research_input import SOURCE, official_partial_from_zip
from scenario_mode_specific_exhibition_end_to_end import (
    evaluate_exhibition_mode_lenses, MODES
)

# These exact hypotheses are unchanged from existing #1710 integration
# tests and are intentionally NOT inferred from data or called calibrated.
from test_scenario_mode_specific_exhibition_end_to_end import hypotheses, weights

NEUTRAL_RATES = [5., 5., 5., 5., 5., 5.]
STUDY = "EXPLORATORY_ONLY_REAL_OFFICIAL_PAIR_V1"
REGRESSION_CODES = ("202611091110", "202611091710",
                    "202611101202", "202611102211")


def run_pair_research(nov9_zip, nov10_zip, conditional_callback):
    if not callable(conditional_callback):
        raise ValueError("reviewed_1698_conditional_callback_required")
    path_by_day={"20261109":nov9_zip,"20261110":nov10_zip}
    records=[]
    for code in REGRESSION_CODES:
        try:
            projection, witness=official_partial_from_zip(
                path_by_day[code[:8]],code)
        except ValueError as exc:
            # Fail closed only for actually missing exhibition data;
            # corrupt archive/receipts must terminate the whole audit.
            if str(exc) != "six_exhibition_st_not_yet_available":
                raise
            records.append({
                "race_code":code,"status":"EXHIBITION_MISSING_REJECTED",
                "research_four_modes_computed":False,
                "missing_reason":"source_exhibition_6course_ST_missing",
                "source_not_T12_certified":True,
            })
            continue
        output=evaluate_exhibition_mode_lenses(
            projection, list(NEUTRAL_RATES), hypotheses(), weights(),
            conditional_callback,study_id=STUDY)
        # Controlled negative test: zero every ST coefficient, hold all
        # other inputs and scenario hypotheses fixed to show input consumption.
        zero_st=copy.deepcopy(hypotheses())
        for world in zero_st.values():
            world["position_coefficients"]["exhibition_st_s"]={
                "second":0.0,"third":0.0,
            }
        no_st=evaluate_exhibition_mode_lenses(
            projection, list(NEUTRAL_RATES), zero_st, weights(),
            conditional_callback,study_id=STUDY)
        effect={
            mode: output["four_mode_research_tickets"][mode]
                  ["distinct_120_mixture_digest"] !=
                  no_st["four_mode_research_tickets"][mode]
                  ["distinct_120_mixture_digest"]
            for mode in MODES
        }
        if not any(effect.values()):
            raise ValueError("actual_exhibition_ST_not_consumed_in_model_research")
        if (output["forecast_usable"] or output["formal"]
                or output["promotion_allowed"]
                or output["production_changed"]
                or output["official_same_race_racelist_exhibition_odds120_verified"]
                or output["first_candidate_remote_receipt_verified"]):
            raise ValueError("unauthorized_live_or_formal_promotion")
        records.append({
            "race_code":code,"status":"RESEARCH_ONLY_REAL_BEFOREINFO_INPUT",
            "official_source_witness":witness,
            "projection_normalized_sha256":projection["normalized_source_sha256"],
            "exhibition_input_sha256":projection["exhibition_features_sha256"],
            "research_four_modes_computed":True,
            "model_ST_ablation_digest_changes":effect,
            "mode_top1_hypothetical":{
                mode:output["four_mode_research_tickets"][mode]["top1"]
                for mode in MODES
            },
            "mode_120_board_sha256_hypothetical":{
                mode:output["four_mode_research_tickets"][mode]
                ["distinct_120_mixture_digest"] for mode in MODES
            },
            "mode_ticket_budget":{
                mode:len(output["four_mode_research_tickets"][mode]["tickets"])
                for mode in MODES
            },
            "distinct_top1_in_hypothetical_model":
                output["distinct_top1_mode_tickets"],
            "weights_are_uncalibrated_fixture_not_generated_from_race":True,
            "national_athlete_win_rates_unknown_neutral_5_each_substituted":True,
            "two_course_wall_rate_from_official_sources":None,
            "wind_from_heading_verified":False,
            "wind_and_wave_consumed_in_scenario_probability":False,
            "actual_race_entry_verified":False,
            "no_racelist_original":True,
            "first_independent_forecast_Git_acceptance":False,
            "formal_accuracy_evidence":False,
            "forecast_usable":False,
            "betting_recommendation":False,
            "production_changed":False,
        })
    if [x["race_code"] for x in records]!=list(REGRESSION_CODES):
        raise ValueError("fixed_actual_source_cohort_changed")
    if (sum(x["research_four_modes_computed"] for x in records)!=3
            or sum(x["status"]=="EXHIBITION_MISSING_REJECTED" for x in records)!=1):
        raise ValueError("fixed_source_completeness_changed")
    return {
        "schema":"SCENARIO_ACTUAL_PRIMARY_TWO_SOURCE_FOUR_MODE_RESEARCH_V1",
        "classification":"actual_official_beforeinfo_bytes_replayed_into_hypothetical_four_mode_math_not_prediction",
        "fixed_actual_primary_source_artifact_ids":[
            SOURCE["20261109"]["artifact_id"],
            SOURCE["20261110"]["artifact_id"]],
        "original_primary_zip_sha256":[SOURCE[x]["zip_sha"] for x in SOURCE],
        "read_athlete_registration_from_actual_beforeinfo":True,
        "athlete_national_rates_from_source":False,
        "neutral_rates_only_for_numerical_sensitivity":True,
        "scenario_weights_not_calibrated":True,
        "source_original_racelist_missing_all_races":True,
        "source_first_receipts_only_collector_self_reported":True,
        "model_ST_was_actually_consumed_in_this_offline_research":True,
        "model_wind_wave_or_tide_scoring_applied":False,
        "real_official_T12_input_certified":False,
        "formal_accuracy_improvement_proven":False,
        "live_forecasts_changed":False,
        "production_deployment_performed":False,
        "results":records,
        "counts":{"races":4,"research_math_run_from_official_exhibition":3,
                  "missing_exhibition_rejected":1,
                  "four_mode_study_reports_generated":3,
                  "formal_forecasts":0,"production_changes":0},
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nov9-zip",type=Path,required=True)
    p.add_argument("--nov10-zip",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    callback=importlib.import_module("position_sensitive_conditioned_lab").experimental_conditional_board
    result=run_pair_research(args.nov9_zip,args.nov10_zip,callback)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "counts":result["counts"],
        "top1_hypotheses":{x["race_code"]:x.get("mode_top1_hypothetical")
                            for x in result["results"]},
        "st_ablation_changes":{x["race_code"]:x.get("model_ST_ablation_digest_changes")
                                for x in result["results"]},
        "formal_accuracy_improvement_proven":False,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
