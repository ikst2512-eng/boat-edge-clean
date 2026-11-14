"""Pinned, distinct F-aware math replay: always read-only, never a new forecast.

Verifies Git blob SHA for new method, legacy baseline, original official
parsers, registered scenarios and the exact external #1698 conditional
function. Its only output is NONPROSPECTIVE research math from immutable
archived official triples. No live collector, clocks, results, Git write,
candidate freeze, formal accuracy score or site use.
"""
import copy
import importlib
import json
from pathlib import Path
import sys

from scenario_signed_st_official_input_adapter import extract_archived_signed_F_input
from scenario_signed_st_four_mode_shadow import signed_F_four_mode_math, STUDY_ID
from scenario_future_local_candidate_handoff import _git_blob_sha1

ROOT=Path(__file__).resolve().parent
PROTOCOL=ROOT/"research/signed_F_four_mode_future_protocol_20261111.json"
PROTOCOL_BLOB="8dd9bfc0ca0533ec6af138be3099ec6f58370a83"
PARENT_PROTOCOL=ROOT/"research/four_mode_triple_source_forward_protocol_20261110.json"
PARENT_BLOB="bf60d2879065d1f9ecbd6b442db17fcb8fbcb8b7"
EXPECTED_START="2026-11-12T00:00:00+09:00"


def _unique_pairs(pairs):
    data={}
    for k,v in pairs:
        if k in data:
            raise ValueError("duplicate_preregistered_study_json_key")
        data[k]=v
    return data


def require_registered_signed_F_method(conditional_callback):
    if (_git_blob_sha1(PROTOCOL.read_bytes())!=PROTOCOL_BLOB
            or _git_blob_sha1(PARENT_PROTOCOL.read_bytes())!=PARENT_BLOB):
        raise ValueError("signed_F_future_protocol_blob_drift")
    protocol=json.loads(PROTOCOL.read_text(encoding="utf-8"),
                        object_pairs_hook=_unique_pairs)
    old=json.loads(PARENT_PROTOCOL.read_text(encoding="utf-8"),
                   object_pairs_hook=_unique_pairs)
    if (protocol.get("schema")!="SIGNED_F_ST_FOUR_MODE_FUTURE_ONLY_PREREGISTRATION_V1"
            or protocol.get("study_id")!=STUDY_ID
            or protocol.get("eligible_new_race_deadline_start_jst")!=EXPECTED_START
            or protocol.get("original_1693_1710_future_600_unchanged") is not True
            or protocol.get("same_fixed_scenarios_as_original_1710")!=old["scenario_hypotheses"]
            or protocol.get("same_mode_weights_as_original_1710")!=old["mode_weights"]
            or protocol.get("mode_ticket_budgets")!=old["mode_ticket_budgets"]
            or protocol.get("deployment",{}).get("prospective_candidate_publisher_installed") is not False
            or protocol.get("deployment",{}).get("production_enabled") is not False):
        raise ValueError("registered_signed_F_protocol_content_or_prior_drift")
    methods=protocol["method_git_blob_sha1"]
    if type(methods) is not dict or not methods:
        raise ValueError("registered_signed_F_method_manifest_invalid")
    for name,expected in methods.items():
        file=ROOT/name
        if (type(name) is not str or not name.endswith(".py")
                or ".." in Path(name).parts or not file.is_file()
                or type(expected) is not str
                or _git_blob_sha1(file.read_bytes())!=expected):
            raise ValueError("registered_signed_F_method_source_changed:"+str(name))
    external=protocol["pinned_external_1698_conditional"]
    if (external.get("commit")!="e152b57033f825e02343b004a9c013a8998f9954"
            or external.get("git_blob_sha1")!="0019978a4e27a1235d0b466c11f514bd7105f261"
            or external.get("code_path")!="position_sensitive_conditioned_lab.py"):
        raise ValueError("signed_F_pinned_1698_identity_changed")
    if (not callable(conditional_callback)
            or getattr(conditional_callback,"__module__",None)!="position_sensitive_conditioned_lab"):
        raise ValueError("signed_F_exact_1698_callback_required")
    m=sys.modules.get("position_sensitive_conditioned_lab")
    if (m is None or getattr(m,"experimental_conditional_board",None) is not conditional_callback
            or not getattr(m,"__file__",None)
            or _git_blob_sha1(Path(m.__file__).read_bytes())!=external["git_blob_sha1"]):
        raise ValueError("signed_F_1698_executable_git_blob_mismatch")
    return protocol


def archived_signed_F_four_mode_math_only(card_dir,beforeinfo_dir,odds_dir,
                                         conditional_callback):
    """Pure replay of already archived source bytes, results never accessed.

    Even when original source receipts were pre-T12, running this function
    AFTER the race cannot make a new valid prospective candidate.
    """
    protocol=require_registered_signed_F_method(conditional_callback)
    source=extract_archived_signed_F_input(card_dir,beforeinfo_dir,odds_dir)
    signed=source["signed_F_feature"]
    if signed["flag_F_count"]<1 or signed["flag_L_count"]!=0:
        raise ValueError("signed_F_study_requires_F_and_no_L")
    plans=protocol["same_fixed_scenarios_as_original_1710"]
    weights=protocol["same_mode_weights_as_original_1710"]
    primary=signed_F_four_mode_math(signed,
        source["six_official_racelist_national_win_rates"],
        source["six_official_exhibition_times_s"],plans,weights,
        conditional_callback,study_id=STUDY_ID)
    control_scenarios=copy.deepcopy(plans)
    for p in control_scenarios.values():
        p["position_coefficients"]["exhibition_st_s"]={"second":0.0,"third":0.0}
    control=signed_F_four_mode_math(signed,
        source["six_official_racelist_national_win_rates"],
        source["six_official_exhibition_times_s"],
        control_scenarios,weights,conditional_callback,study_id=STUDY_ID)
    assert primary["all_mode_tickets"]==control["all_mode_tickets"]==protocol["mode_ticket_budgets"]
    return {
        "schema":"REGISTERED_SIGNED_F_FOUR_MODE_ARCHIVED_MATH_ONLY_V1",
        "study_id":STUDY_ID,
        "race_code":source["race_code"],
        "registered_study_protocol_git_blob_sha1":PROTOCOL_BLOB,
        "registered_method_sources_checked_locally":True,
        "actual_original_source_race_card_beforeinfo_odds120_reparsed":True,
        "source_original_sha256":source["source_sha256"],
        "signed_feature_vector_sha256":signed["vector_sha256"],
        "F_boats":signed["flag_F_count"],
        "primary_method":"SIGNED_F_ST_NONZERO_REGISTERED_COEFFICIENTS",
        "control_method":"ZERO_ST_COEFFICIENTS_SAME_HEAD_TIME_SCENARIO_WEIGHTS",
        "math_4_modes_signed_F":primary["four_mode_hypothetical_tickets"],
        "math_4_modes_ST_zero_control":control["four_mode_hypothetical_tickets"],
        "same_4_mode_ticket_budgets":protocol["mode_ticket_budgets"],
        "research_math_executed":True,
        "historical_archive_replay_not_predeadline_forecast":True,
        "prospective_candidate_generated":False,
        "independent_first_remote_source_receipt_proven":False,
        "independent_first_remote_candidate_receipt_proven":False,
        "results_or_payouts_read":False,
        "old_1693_1710_cohort_unchanged":True,
        "new_pilot_samples":0,"new_confirmation_samples":0,
        "formal":False,"calibrated":False,"promotion_allowed":False,
        "production_changed":False,"accuracy_improvement_proven":False,
        "warning":"This is a result-blind post-event math regression, NOT a real-time saved candidate.",
    }
