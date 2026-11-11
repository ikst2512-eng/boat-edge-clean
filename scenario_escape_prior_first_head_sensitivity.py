"""RESEARCH ONLY: a first-head world weight that varies with 1C racer history.

Builds on #1692's *exploratory* chronological 1C-athlete residual idea,
#1710's already-frozen four scenario head and 120-way pair composer and
the exact external #1698 conditional callback. This is a SEPARATE,
UNREGISTERED numerical sensitivity study, NOT a pre-T12 forecast, a
certified official K statistic, an established causal 2C wall estimate
or a measured improvement. No results, K-file I/O, API, Git writing, Cron,
site selector changes or saved prediction mutation.

Until the actual first course and source age are independently attested,
exhibition course is only a PROXY; changed 1C exhibition is rejected because
the frozen "escape_wall" hypothesis boosts boat 1 rather than course 1.
"""
import copy
from datetime import date, datetime, timedelta
import math
import re

from research_model import probabilities
from scenario_first_head_research import hypothetical_head_board
from scenario_signed_st_four_mode_shadow import signed_F_four_mode_math
from scenario_four_mode_bridge import BUDGETS

SCHEMA="SEPARATE_ATHLETE_HISTORY_FIRST_HEAD_SENSITIVITY_V1"
HISTORY_SCHEMA="UNATTESTED_BEFORE_EVENT_OFFICIAL_K_C1_HISTORY_SUMMARY_V1"
STUDY="EXPLORATORY_ONLY_C1_ATHLETE_ESCAPE_DYNAMIC_HEAD_V1"
RACE=re.compile(r"20[0-9]{10}\Z")
K92_ZIP_SHA256="c668f545bae54f8148616315e307ed2a2b04a77a0cb8abf88bf3ea078749ce8e"
WORLDS=("escape_wall","two_sashi","third_attack","outer_benefit")
HISTORY_FIELDS={
    "schema","race_code","historic_training_end_date_jst",
    "official_K_replay_zip_sha256_claim","venue_code",
    "national_training_race_count","national_training_C1_escape_count",
    "venue_training_race_count","venue_training_C1_escape_count",
    "C1_athlete_registration","C1_athlete_training_race_count",
    "C1_athlete_venue_centered_residual_sum",
    "exhibition_entry_roster_by_boat","training_used_outcomes_after_target",
    "official_source_receipt_independently_authenticated",
    "exhibition_is_final_race_entry","outcomes_from_target_race_read",
}
ENTRY_FIELDS={"boat","registration","exhibition_course"}


def _finite(value,label,*,low,high):
    if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError("C1_history_"+label+"_invalid")
    return float(value)


def _strict_count(value,label):
    if type(value) is not int or value<0:
        raise ValueError("C1_history_"+label+"_invalid")
    return value


def historical_C1_escape_proxy(history,feature):
    """Return #1692-style venue+1C athlete residual as *sensitivity*, not P(1st)."""
    if (type(history) is not dict or set(history)!=HISTORY_FIELDS
            or history.get("schema")!=HISTORY_SCHEMA
            or history.get("official_K_replay_zip_sha256_claim")!=K92_ZIP_SHA256
            or history.get("training_used_outcomes_after_target") is not False
            or history.get("official_source_receipt_independently_authenticated") is not False
            or history.get("exhibition_is_final_race_entry") is not False
            or history.get("outcomes_from_target_race_read") is not False):
        raise ValueError("C1_history_source_claim_or_schema_forbidden")
    code=history["race_code"]
    if type(code) is not str or not RACE.fullmatch(code) or code!=feature.get("race_code"):
        raise ValueError("C1_history_target_race_identity_mismatch")
    if not 1<=int(code[8:10])<=24 or not 1<=int(code[10:12])<=12:
        raise ValueError("C1_history_race_venue_or_number_invalid")
    if history["venue_code"]!=code[8:10]:
        raise ValueError("C1_history_venue_mismatch")
    try:
        end=date.fromisoformat(history["historic_training_end_date_jst"])
        target=date.fromisoformat(code[:4]+"-"+code[4:6]+"-"+code[6:8])
    except (TypeError,ValueError) as exc:
        raise ValueError("C1_history_period_invalid") from exc
    # Frozen official-K sample from 8/1-10/31; no October holdout
    # labels used for an August-September learner.
    if end>date(2026,9,30) or end<date(2026,8,1) or end>=target:
        raise ValueError("C1_history_lookahead_or_untrained_period")
    n=_strict_count(history["national_training_race_count"],"national_denominator")
    k=_strict_count(history["national_training_C1_escape_count"],"national_numerator")
    vn=_strict_count(history["venue_training_race_count"],"venue_denominator")
    vk=_strict_count(history["venue_training_C1_escape_count"],"venue_numerator")
    player_n=_strict_count(history["C1_athlete_training_race_count"],"athlete_denominator")
    if (n<100 or k>n or vn<10 or vk>vn or vn>n
            or player_n>n):
        raise ValueError("C1_history_invalid_race_counts")
    residual=_finite(history["C1_athlete_venue_centered_residual_sum"],
                      "athlete_residual",low=-player_n,high=player_n)
    racer=history["C1_athlete_registration"]
    if type(racer) is not str or re.fullmatch(r"[0-9]{4,6}",racer) is None:
        raise ValueError("C1_history_athlete_registration_invalid")
    roster=history["exhibition_entry_roster_by_boat"]
    feature_rows=feature.get("exhibition_st_by_boat")
    if type(roster) is not list or len(roster)!=6 or type(feature_rows) is not list or len(feature_rows)!=6:
        raise ValueError("C1_history_six_source_roster_required")
    if (any(type(r) is not dict or set(r)!=ENTRY_FIELDS for r in roster)
            or [r["boat"] for r in roster]!=list(range(1,7))
            or any(type(r["registration"]) is not str or
                   re.fullmatch(r"[0-9]{4,6}",r["registration"]) is None
                   for r in roster)
            or len({r["registration"] for r in roster})!=6
            or any(type(r["exhibition_course"]) is not int
                   for r in roster)
            or {r["exhibition_course"] for r in roster}!=set(range(1,7))
            or any(type(entry) is not dict
                   or entry.get("boat")!=r["boat"]
                   or entry.get("exhibition_course_only")!=r["exhibition_course"]
                   for r,entry in zip(roster,feature_rows))):
        raise ValueError("C1_history_roster_or_exhibition_course_mismatch")
    # Cannot silently reassign old fixed head shift of boat1 to entrant2.
    if roster[0]["exhibition_course"]!=1:
        raise ValueError("C1_history_changed_exhibition_entry_requires_separate_world_mapping")
    if racer!=roster[0]["registration"]:
        raise ValueError("C1_history_athlete_does_not_match_exhibition_course1")
    national=k/n
    venue=(vk+40*national)/(vn+40)
    player_delta=residual/(player_n+40)
    candidate=min(.995,max(.005,venue+player_delta))
    venue=min(.995,max(.005,venue))
    return {
        "venue_C1_escape_proxy":venue,
        "athlete_adjusted_C1_escape_proxy":candidate,
        "athlete_effect_vs_venue":candidate-venue,
        "venue_smoothing_races":40,
        "athlete_residual_smoothing_races":40,
        "source_lookahead_tested_structurally":True,
        "official_original_K_bytes_replayed_in_this_function":False,
        "exhibition_course_assumed_final_entry":False,
        "trained_coefficients_formally_calibrated":False,
        "predictive_effect_proven":False,
    }


def _world_weights(escape_proxy):
    """Illustrative escape/non-escape split; no calibrated scenario weights.

    This is NOT a causal 2C wall probability. The remaining probability is
    split equally among the frozen other three hypothetical head scenarios.
    """
    p=_finite(escape_proxy,"world_proxy",low=.005,high=.995)
    return {
        "escape_wall":p,
        "two_sashi":(1-p)/3,
        "third_attack":(1-p)/3,
        "outer_benefit":(1-p)/3,
    }


def sensitivity_only(history, signed_feature, national_rates, exhibition_times,
                     registered_plans, reviewed_1698_callback):
    """Two paired four-mode boards; no authentication, scoring or persistence."""
    hist=historical_C1_escape_proxy(history,signed_feature)
    if (type(registered_plans) is not dict
            or set(registered_plans)!=set(WORLDS)):
        raise ValueError("C1_history_complete_four_frozen_worlds_required")
    # Caller supplies original frozen hypotheses, never learns weights from a
    # target outcome. Original hypothetical head distributions are retained.
    normal=_world_weights(hist["venue_C1_escape_proxy"])
    athlete=_world_weights(hist["athlete_adjusted_C1_escape_proxy"])
    mode_control={m:copy.deepcopy(normal) for m in BUDGETS}
    mode_athlete={m:copy.deepcopy(athlete) for m in BUDGETS}
    base=probabilities(national_rates)
    head={}
    for world in WORLDS:
        head[world]=hypothetical_head_board(
            base,registered_plans[world]["head_log_shifts"],
            study_id=STUDY+"_HEAD_"+world.upper())["hypothesis_first_mass"]
    first_mass=lambda weights:{str(boat):math.fsum(
        weights[world]*head[world][str(boat)] for world in WORLDS)
        for boat in range(1,7)}
    a=signed_F_four_mode_math(
        signed_feature,national_rates,exhibition_times,
        registered_plans,mode_control,reviewed_1698_callback,
        study_id=STUDY)
    b=signed_F_four_mode_math(
        signed_feature,national_rates,exhibition_times,
        registered_plans,mode_athlete,reviewed_1698_callback,
        study_id=STUDY)
    return {
        "schema":SCHEMA,"study_id":STUDY,
        "race_code":history["race_code"],
        "feature_status":"unverified_historical_training_and_exhibition_proxy_only",
        "history_summary":hist,
        "control_venue_only_world_weights":normal,
        "hypothesis_athlete_world_weights":athlete,
        "control_head_mass_by_boat":first_mass(normal),
        "hypothesis_head_mass_by_boat":first_mass(athlete),
        "control_four_mode_tickets":a["four_mode_hypothetical_tickets"],
        "hypothesis_four_mode_tickets":b["four_mode_hypothetical_tickets"],
        "same_mode_budgets":dict(BUDGETS),
        "world_splitting_is_uncalibrated_hypothesis":True,
        "wall_effect_measured":False,"actual_final_entry_verified":False,
        "wind_wave_tide_motor_used":False,
        "candidate_created":False,"first_remote_receipt_verified":False,
        "eligible_for_existing_600":False,"eligible_for_new_600":False,
        "outcomes_read":False,"formal":False,
        "production_changed":False,"accuracy_improvement_proven":False,
        "warning":"Postrace K-derived history summary unverified here. Pure sensitivity; not a validated future forecast.",
    }
