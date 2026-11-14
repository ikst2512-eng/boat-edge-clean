"""Unregistered course-holder transfer: only synthetic input and frozen math.

No authentic K original, HTTP receipt, future first Git save, calibration,
outcome, return, bookmaker odds, or production usage is asserted here.
"""
import copy
import hashlib
import importlib
import json
import math
import os
import unittest
from unittest.mock import patch

import scenario_exhibition_course_head_research as lab
from scenario_exhibition_course_head_research import (
    STUDY, prepare_course_holder_head_study, run_course_holder_four_mode_sensitivity,
)
from scenario_four_mode_bridge import BUDGETS, _valid_board
from scenario_official_exhibition_projection import project_exhibition_research
from test_scenario_future_three_original_gateway import (
    future_synthetic, triple_fixture,
)
from test_scenario_official_exhibition_projection import replay_stub
from test_scenario_escape_prior_first_head_sensitivity import history


def input_case(swap=1):
    source, candidate = future_synthetic()
    if swap != 1:
        courses = source["normalized_source_claim"]["exhibition_courses"]
        courses[0], courses[swap-1] = courses[swap-1], courses[0]
        norm = source["normalized_source_claim"]
        candidate["consumed_normalized_claim_sha256"] = hashlib.sha256(
            json.dumps(norm, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")).encode()).hexdigest()
    audit = triple_fixture(source)
    projected = project_exhibition_research(source, candidate, replay_stub)
    h = history()
    h["race_code"] = projected["race_code"]
    h["venue_code"] = projected["race_code"][8:10]
    rows = projected["exhibition_features_by_boat"]
    h["exhibition_entry_roster_by_boat"] = [
        {"boat": r["boat"], "registration": r["registration_id"],
         "exhibition_course": r["exhibition_course_only"]} for r in rows]
    h["C1_athlete_registration"] = next(
        r["registration_id"] for r in rows if r["exhibition_course_only"] == 1)
    return audit, source, candidate, projected, h


def prepare(*case):
    return prepare_course_holder_head_study(*case)


class CourseHolderStructuralTests(unittest.TestCase):
    def test_original_course_order_preserves_each_registered_head_vector(self):
        case = input_case()
        before = copy.deepcopy(case)
        s = prepare(*case)
        plans, weights = lab._frozen_protocol()
        self.assertEqual(s["frozen_protocol_blob_sha1"],
                         lab.FROZEN_1710_PROTOCOL_BLOB)
        self.assertEqual(s["scenario_weights"], weights)
        for world in lab.WORLDS:
            self.assertEqual(
                s["frozen_head_coefficients_mapped_by_exhibition_course"][world],
                plans[world]["head_log_shifts"])
            board = _valid_board(s["head_models"][world]["ranked_board"])
            self.assertEqual(len(board), 120)
            self.assertAlmostEqual(math.fsum(board.values()), 1.0, places=12)
        self.assertEqual(s["history_source_join"]["exhibition_course1_boat"], 1)
        self.assertFalse(s["history_counts_applied_to_head_or_world_weights"])
        self.assertFalse(s["original_K_history_replayed_and_verified"])
        self.assertFalse(s["independent_first_remote_forecast_receipt_verified"])
        self.assertFalse(s["formal"])
        self.assertFalse(s["accuracy_improvement_proven"])
        self.assertEqual(case, before)

    def test_boat1_swap_to_any_other_course_maps_course1_head_to_actual_holder(self):
        for swap in range(2, 7):
            with self.subTest(exhibition_course_for_boat1=swap):
                case = input_case(swap)
                s = prepare(*case)
                holder = swap
                self.assertEqual(
                    s["exhibition_course_to_boat"]["1"], holder)
                self.assertEqual(
                    s["history_source_join"]["exhibition_course1_boat"], holder)
                self.assertEqual(
                    s["history_source_join"]["exhibition_course1_athlete"],
                    str(4509+holder))
                head = s["frozen_head_coefficients_mapped_by_exhibition_course"][
                    "escape_wall"]
                self.assertEqual(head[holder-1], 3.5)
                self.assertEqual(head[0], 0)
                # The 1C world now weighs the exhibited course-1 holder rather
                # than inventing boat1's outside-course inside escape.
                first = s["head_models"]["escape_wall"]["hypothesis_first_mass"]
                original = s["head_models"]["escape_wall"]["original_first_mass"]
                self.assertGreater(
                    first[str(holder)] / original[str(holder)],
                    first["1"] / original["1"])
                self.assertEqual(len(_valid_board(
                    s["head_models"]["escape_wall"]["ranked_board"])),120)
                self.assertFalse(s["pre_registered_new_candidate"])

    def test_wrong_athlete_or_roster_or_venue_fails_closed(self):
        for change in ("athlete", "roster", "venue", "race"):
            case = list(input_case(2))
            h = case[4]
            if change == "athlete": h["C1_athlete_registration"] = "4510"
            if change == "roster": h["exhibition_entry_roster_by_boat"][1]["registration"] = "9999"
            if change == "venue": h["venue_code"] = "18"
            if change == "race": h["race_code"] = "202611111711"
            with self.subTest(change=change), self.assertRaisesRegex(
                    ValueError,"history_"):
                prepare(*case)

    def test_late_or_lookahead_training_or_bad_counts_fails_closed(self):
        for key, value in (
            ("historic_training_end_date_jst", "2026-11-11"),
            ("historic_training_end_date_jst", "2026-07-31"),
            ("venue_training_C1_escape_count", 900),
            ("national_training_race_count", 0),
            ("C1_athlete_venue_centered_residual_sum", float("nan")),
        ):
            case=list(input_case(4)); case[4][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                prepare(*case)

    def test_forged_history_provenance_or_outcomes_not_consumed(self):
        for key, value in (
            ("official_source_receipt_independently_authenticated",True),
            ("exhibition_is_final_race_entry",True),
            ("outcomes_from_target_race_read",True),
            ("training_used_outcomes_after_target",True),
            ("winner",1),
        ):
            case=list(input_case(2)); case[4][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                prepare(*case)

    def test_wrong_same_race_source_or_tampered_digest_rejected(self):
        case=list(input_case(3))
        case[0]["registrations_by_lane"]["1"]="9999"
        with self.assertRaises(ValueError):
            prepare(*case)
        case=list(input_case(3))
        case[3]["exhibition_features_by_boat"][1]["exhibition_course_only"]=4
        with self.assertRaises(ValueError):
            prepare(*case)
        case=list(input_case(3))
        case[1]["originals"]["racelist"]["raw_base64"]="!!"
        with self.assertRaises(ValueError):
            prepare(*case)
        case=list(input_case(3))
        case[2]["generated_at_jst"]=case[0]["cutoff_jst"]
        with self.assertRaises(ValueError):
            prepare(*case)

    def test_registered_protocol_file_is_frozen(self):
        case=input_case()
        with patch.object(lab,"FROZEN_1710_PROTOCOL_BLOB","0"*40):
            with self.assertRaisesRegex(ValueError,"frozen_1710_protocol_changed"):
                prepare(*case)

    def test_history_weak_provenance_is_not_promoted_into_model(self):
        a=prepare(*input_case(2))
        bcase=list(input_case(2))
        bcase[4]["C1_athlete_venue_centered_residual_sum"]=-10
        b=prepare(*bcase)
        self.assertEqual(
            a["frozen_head_coefficients_mapped_by_exhibition_course"],
            b["frozen_head_coefficients_mapped_by_exhibition_course"])
        for name in lab.WORLDS:
            self.assertEqual(
                a["head_models"][name]["ranked_board"],
                b["head_models"][name]["ranked_board"])
        self.assertFalse(a["history_source_join"]["official_K_original_replayed_here"])
        self.assertFalse(b["history_source_join"]["independent_historical_receipt_verified"])


class Pinned1698CourseHolderMathTests(unittest.TestCase):
    def setUp(self):
        if os.getenv("RESEARCH_1698_PIN_REQUIRED") != "1":
            self.skipTest("requires the exact pinned #1698 code blob")
        self.callback=importlib.import_module(
            "position_sensitive_conditioned_lab").experimental_conditional_board

    def test_full_four_mode_board_and_120_ticket_mass_under_swapped_course(self):
        case=input_case(4)
        study=prepare(*case)
        result=run_course_holder_four_mode_sensitivity(
            study,case[3],self.callback)
        self.assertEqual(result["study_id"],STUDY)
        self.assertEqual(result["head_holder_by_exhibition_course"]["1"],4)
        self.assertEqual(
            {name:len(row["tickets"]) for name,row in result["modes"].items()},
            BUDGETS)
        self.assertEqual(result,run_course_holder_four_mode_sensitivity(
            study,case[3],self.callback))
        for key in ("formal","forecast_usable","calibrated","production_changed",
                    "independent_first_remote_receipt_verified","results_read",
                    "accuracy_improvement_proven","promotion_allowed"):
            self.assertIs(result[key],False,key)

    def test_actual_swap_changes_full_mode_content_vs_frozen_boat_vector(self):
        identity=input_case(1); swap=input_case(2)
        a=run_course_holder_four_mode_sensitivity(
            prepare(*identity),identity[3],self.callback)
        b=run_course_holder_four_mode_sensitivity(
            prepare(*swap),swap[3],self.callback)
        self.assertNotEqual(
            a["modes"]["narrow"]["board_sha256"],
            b["modes"]["narrow"]["board_sha256"])
        self.assertEqual(len(b["modes"]["narrow"]["tickets"]),5)
        self.assertEqual(len(b["modes"]["hole"]["tickets"]),22)

    def test_tampered_callback_and_changed_entry_after_prepare_rejected(self):
        case=input_case(5); study=prepare(*case)
        def fake(*args):
            x=self.callback(*args)
            x["formal"]=True
            return x
        with self.assertRaisesRegex(ValueError,"conditional_lab_contract"):
            run_course_holder_four_mode_sensitivity(study,case[3],fake)
        p=copy.deepcopy(case[3])
        p["exhibition_features_by_boat"][0]["exhibition_course_only"]=1
        # Even recomputing the vector hash must not allow a post-prepare swap.
        p["exhibition_features_sha256"] = hashlib.sha256(json.dumps(
            p["exhibition_features_by_boat"],sort_keys=True,
            separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        with self.assertRaises(ValueError):
            run_course_holder_four_mode_sensitivity(study,p,self.callback)

if __name__=="__main__":
    unittest.main()
