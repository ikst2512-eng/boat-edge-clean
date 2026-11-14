"""Immutable candidate-method contract for NEW separate future 4-mode study.

All checks are on locally checked-out, Git-content-pinned RESEARCH code.
They DO NOT prove a GitHub FIRST remote candidate receipt, real official
T-minus-12 inputs, predictive lift, or eligibility for #1693's old 600.
"""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

from scenario_future_three_original_gateway import STUDY, MIN_DAY
from scenario_mode_specific_exhibition_end_to_end import MODES, BUDGETS
from test_scenario_mode_specific_exhibition_end_to_end import hypotheses, weights

PROTOCOL = Path(__file__).parent / (
    "research/four_mode_triple_source_forward_protocol_20261110.json"
)
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
EXPECTED_METHOD_PATHS = {
    "research_model.py",
    "clean_four_modes.py",
    "scenario_exhibition_all_mode_runner.py",
    "scenario_mode_specific_exhibition_end_to_end.py",
    "scenario_official_exhibition_projection.py",
    "scenario_first_head_research.py",
    "scenario_four_mode_bridge.py",
    "scenario_future_three_original_gateway.py",
    "scenario_official_racelist_rates.py",
    "scripts/audit_three_official_t12_originals.py",
}


def no_duplicate_keys(pairs):
    x = {}
    for name, value in pairs:
        if name in x:
            raise ValueError("frozen_protocol_duplicate_key")
        x[name] = value
    return x


def read_protocol():
    raw = PROTOCOL.read_bytes()
    if len(raw) > 15000:
        raise ValueError("frozen_protocol_oversize")
    return json.loads(raw, object_pairs_hook=no_duplicate_keys,
                      parse_constant=lambda _: (_ for _ in ()).throw(
                          ValueError("nonfinite_protocol_value")))


def validate_protocol(p):
    if (type(p) is not dict
            or p.get("schema") !=
            "FOUR_MODE_TRIPLE_SOURCE_PROSPECTIVE_RESEARCH_PROTOCOL_V1"
            or p.get("study_id") != STUDY
            or p.get("status") !=
            "committed_research_protocol_not_active_no_confirmed_future_candidate"
            or p.get("registered_on_date_jst") != "2026-11-10"
            or p.get("old_registered_1693_600_unchanged") is not True
            or p.get("discovery_dates_excluded_through") != "2026-11-10"):
        raise ValueError("wrong_new_study_or_registration_boundary")
    begin = datetime.fromisoformat(p["eligible_deadline_start_jst"])
    end = datetime.fromisoformat(p["eligible_deadline_end_jst"])
    if (begin.utcoffset() != timedelta(hours=9)
            or end.utcoffset() != timedelta(hours=9)
            or not begin < end
            or begin.strftime("%Y%m%d") != MIN_DAY
            or begin.date().isoformat() <= p["discovery_dates_excluded_through"]):
        raise ValueError("new_cohort_not_strictly_future")
    if (p.get("scenario_hypotheses") != hypotheses()
            or p.get("mode_weights") != weights()
            or p.get("mode_ticket_budgets") != BUDGETS
            or set(p["mode_weights"]) != set(MODES)
            or p.get("primary_arm_id") != "FIXED_SCENARIO_HEAD35_4MODES_V1"
            or p.get("negative_control_arm_id") != "FIXED_SCENARIO_HEAD0_4MODES_V1"):
        raise ValueError("scenario_hypothesis_or_mode_weights_drift")
    source_pins = p.get("method_git_blob_sha1")
    if (type(source_pins) is not dict
            or set(source_pins) != EXPECTED_METHOD_PATHS
            or not all(type(x) is str and HEX40.fullmatch(x)
                       for x in source_pins.values())):
        raise ValueError("unfrozen_or_unexpected_local_method")
    ext = p.get("pinned_external_code")
    if (type(ext) is not dict
            or ext.get("1698_conditional_code_blob_sha1") !=
            "0019978a4e27a1235d0b466c11f514bd7105f261"
            or ext.get("1698_conditional_repo_commit") !=
            "e152b57033f825e02343b004a9c013a8998f9954"
            or ext.get("1693_semantic_replay_code_blob_sha1") !=
            "2f5af32201e3060c57b5a999f0389ce67c3046cb"
            or ext.get("1693_semantic_replay_repo_commit") !=
            "d93349e4855d6dc1026dfad1795a99632d7e9a35"):
        raise ValueError("existing_research_model_pin_drift")
    science = p.get("scientific_protocol")
    if (type(science) is not dict or
            science.get("pilot_eligible_races") != 300 or
            science.get("confirmation_independent_eligible_races") != 300 or
            "first_600_valid" not in science.get("allocation", "") or
            "existing_1693_result_LAST" not in science.get("scoring", "")):
        raise ValueError("future_600_and_existing_scorer_changed")
    if (type(p.get("admission_conditions")) is not list
            or len(p["admission_conditions"]) != 10):
        raise ValueError("invalid_full_future_evidence_requirements")
    for key in ("preregistration_independently_attested","formal",
                "improvement_proven","promotion_allowed"):
        if p.get(key) is not False:
            raise ValueError("unauthorized_future_study_promotion")
    for key in ("no_production_merge_or_live_selector_change",
                "no_candidate_remote_write_performed"):
        if p.get(key) is not True:
            raise ValueError("unintended_forecast_or_deployment_write")
    if p.get("new_pilot_admitted") != 0 or p.get("new_confirmation_admitted") != 0:
        raise ValueError("unverified_new_prospective_cases")
    return True


def verify_checked_out_method_blobs(p):
    """Fail if any live local model source differs from the registered blob."""
    validate_protocol(p)
    for path, pinned in p["method_git_blob_sha1"].items():
        if not (PROTOCOL.parent.parent / path).is_file():
            raise ValueError("registered_method_file_missing")
        actual = subprocess.check_output(
            ["git", "hash-object", path], cwd=PROTOCOL.parent.parent,
            text=True).strip()
        if actual != pinned:
            raise ValueError("preregistered_method_git_blob_drift:" + path)
    return True


class FrozenSeparateFutureStudyTests(unittest.TestCase):
    def test_protocol_exact_unmodified_source_and_hypotheses(self):
        p = read_protocol()
        self.assertTrue(verify_checked_out_method_blobs(p))
        self.assertEqual(p["scientific_protocol"]["pilot_eligible_races"],300)
        self.assertEqual(p["scientific_protocol"]["confirmation_independent_eligible_races"],300)

    def test_protocol_diverges_if_coefficient_or_world_weight_changes(self):
        import copy
        p=read_protocol()
        q=copy.deepcopy(p)
        q["scenario_hypotheses"]["two_sashi"]["head_log_shifts"][1]=3.6
        with self.assertRaisesRegex(ValueError,"hypothesis_or_mode_weights_drift"):
            validate_protocol(q)
        q=copy.deepcopy(p)
        q["mode_weights"]["hole"]["outer_benefit"]=0.6
        with self.assertRaisesRegex(ValueError,"hypothesis_or_mode_weights_drift"):
            validate_protocol(q)

    def test_future_window_or_cohort_cannot_backdate(self):
        import copy
        p=read_protocol()
        for date in ("2026-11-09T00:00:00+09:00",
                     "2026-11-10T00:00:00+09:00"):
            q=copy.deepcopy(p)
            q["eligible_deadline_start_jst"]=date
            with self.subTest(date=date),self.assertRaisesRegex(ValueError,"not_strictly_future"):
                validate_protocol(q)
        q=copy.deepcopy(p)
        q["scientific_protocol"]["pilot_eligible_races"]=106
        with self.assertRaisesRegex(ValueError,"future_600"):
            validate_protocol(q)

    def test_invalid_method_and_first_remote_claim_refused(self):
        import copy
        p=read_protocol()
        q=copy.deepcopy(p)
        q["method_git_blob_sha1"]["research_model.py"]="a"*40
        with self.assertRaisesRegex(ValueError,"preregistered_method_git_blob_drift"):
            verify_checked_out_method_blobs(q)
        q=copy.deepcopy(p)
        q["preregistration_independently_attested"]=True
        with self.assertRaisesRegex(ValueError,"promotion"):
            validate_protocol(q)
        q=copy.deepcopy(p)
        q["new_pilot_admitted"]=1
        with self.assertRaisesRegex(ValueError,"unverified"):
            validate_protocol(q)

    def test_no_duplicate_keys_or_nan_allowed(self):
        with self.assertRaisesRegex(ValueError,"duplicate"):
            json.loads('{"a":1,"a":2}', object_pairs_hook=no_duplicate_keys)
        with self.assertRaises(ValueError):
            json.loads('{"x":NaN}', parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("nonfinite")))


if __name__ == "__main__":
    unittest.main()
