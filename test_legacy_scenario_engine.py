"""Live-only restored legacy scenario + parallel immutable V2 regression."""
import copy
from datetime import datetime
import unittest

from legacy_scenario_engine import JST, MODEL_VERSION, restored_scenario_preview
from server import get_restored_scenario_preview
from four_mode_archive_api import archived_four_modes


NOW = datetime(2026, 11, 12, 10, 0, tzinfo=JST)
CODE = "202611120501"
RATES = [6.34, 5.22, 5.12, 6.03, 4.78, 4.92]


def current_card(with_before=True):
    racers = []
    for lane, win in enumerate(RATES, 1):
        racers.append({
            "lane": lane, "registration_no": str(3000+lane),
            "name": f"選手{lane}", "class": "A1" if lane in (1, 4) else "B1",
            "avg_st": .15+lane*.005,
            "national": {"win_rate": win, "quinella_rate": 49+lane},
            "local": {"win_rate": 5.1+lane*.11, "quinella_rate": 35+lane},
            "motor": {"quinella_rate": 31+lane},
            "boat": {"quinella_rate": 28+lane},
        })
    return {
        "schema_version": "boat-edge-race-v5",
        "race_key": "20261112-05-01",
        "meta": {
            "date": "2026-11-12", "venue_code": "05", "race_no": 1,
            "deadline": "12:00", "phase": "PRE_RESULT",
            "results_seen": False, "unlock": False, "scoring": False,
            "historical_reference_only": False,
        },
        "source_audit": {
            "race_card": {
                "status": "ok", "predeadline_verified": True,
                "fetched_at": "2026-11-12T09:20:00+09:00",
                "sha256": "a"*64,
            },
            "beforeinfo": ({
                "status": "ok", "fetched_at": "2026-11-12T09:40:00+09:00",
            } if with_before else {"status": "source_unavailable"}),
        },
        "racers": racers,
        "beforeinfo": ({
            "racers": [{"lane": lane, "exhibition_time": 6.70+lane*.03, "tilt": -0.5}
                       for lane in range(1, 7)],
            "start_exhibition": [
                {"lane": lane, "course": float(lane), "st": f".{10+lane:02d}"}
                for lane in range(1, 7)
            ],
        } if with_before else None),
    }


class RestoredEngineRegression(unittest.TestCase):
    def test_four_modes_use_the_restored_old_scores_not_v2_board(self):
        card = current_card()
        output = restored_scenario_preview(card, NOW)
        self.assertEqual(output["race_code"], CODE)
        self.assertEqual(output["model_version"], MODEL_VERSION)
        self.assertEqual(output["status"], "live_research_preview_not_saved")
        self.assertEqual(output["source_racecard_sha256"], "a"*64)
        self.assertTrue(output["observed_exhibition_only"])
        self.assertFalse(output["actual_final_entry_verified"])
        self.assertIn("exhibition_course_only", output["used_features"])
        self.assertIn("national_win_rate", output["used_features"])
        self.assertIn("motor_2ren", output["used_features"])
        self.assertIn("actual_final_entry", output["missing_or_unverified"])
        for key in ("formal", "calibrated", "accuracy_improvement_proven",
                    "independently_saved_before_T12", "production_buy_approved",
                    "baseline_prediction_changed"):
            self.assertIs(output[key], False, key)
        self.assertIs(output["head_top2_is_not_trifecta_hit70"], True)
        self.assertAlmostEqual(output["worlds"]["one_escape_model_pct"] +
                               output["worlds"]["one_not_escape_model_pct"], 100)
        self.assertEqual({mode: len(rows["tickets"]) for mode, rows in output["modes"].items()},
                         {"narrow": 5, "hit": 10, "balance": 16, "hole": 22})
        for mode, rec in output["modes"].items():
            names = [row["combo"] for row in rec["tickets"]]
            self.assertEqual(len(set(names)), len(names))
            self.assertTrue(all(len(set(map(int, name.split("-")))) == 3 for name in names))
            self.assertTrue(all(0 <= x["p"] <= 100 for x in rec["tickets"]))
        self.assertEqual(
            restored_scenario_preview(card, NOW)["modes"],
            output["modes"], "same pre-race inputs must reproduce identical modes")

    def test_national_rate_is_only_one_sensitive_feature_not_sole_input(self):
        baseline = restored_scenario_preview(current_card(), NOW)
        altered = current_card()
        altered["racers"][1]["national"]["win_rate"] = 8.0
        changed = restored_scenario_preview(altered, NOW)
        self.assertNotEqual(changed["worlds"]["one_escape_model_pct"],
                            baseline["worlds"]["one_escape_model_pct"])
        self.assertNotEqual(changed["modes"], baseline["modes"])
        st = current_card()
        st["beforeinfo"]["start_exhibition"][1]["st"] = ".01"
        st_result = restored_scenario_preview(st, NOW)
        self.assertNotEqual(st_result["modes"], baseline["modes"],
                            "a changed exhibition ST must change the 4-mode probability board")
        entry = current_card()
        entry["beforeinfo"]["start_exhibition"][2]["course"] = 4.0
        entry["beforeinfo"]["start_exhibition"][3]["course"] = 3.0
        entry_result = restored_scenario_preview(entry, NOW)
        self.assertNotEqual(entry_result["modes"], baseline["modes"],
                            "a real exhibition course change must affect the board")

    def test_changed_course_one_exhibition_does_not_fake_boat_one_escape(self):
        # Main legacy A/B head formula explicitly pins the escape world to
        # boat 1. Exhibition-course swaps must not produce misleading picks.
        # This does not claim the exhibition entry is the final race entry.
        for new_course in range(2, 7):
            card = current_card()
            rows = card["beforeinfo"]["start_exhibition"]
            rows[0]["course"], rows[new_course-1]["course"] = (
                rows[new_course-1]["course"], rows[0]["course"])
            with self.subTest(new_course=new_course):
                with self.assertRaisesRegex(
                        ValueError,
                        "legacy_escape_world_requires_boat1_exhibition_course1"):
                    restored_scenario_preview(card, NOW)
                status, response = get_restored_scenario_preview(
                    {"hd": ["20261112"], "jcd": ["05"], "rno": ["1"]},
                    card_loader=lambda hd, jcd, rno: card, now=NOW)
                self.assertEqual(status, 422)
                self.assertFalse(response["ok"])
                self.assertEqual(response["status"], "unverified_source")
                self.assertEqual(
                    response["reason"],
                    "legacy_escape_world_requires_boat1_exhibition_course1")
        # The original immutable V2 archive must still be retrievable.
        status, archive = archived_four_modes("202611111001")
        self.assertEqual(status, 200)
        self.assertEqual(
            archive["model_version"],
            "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED")

    def test_missing_preview_is_reported_not_fabricated(self):
        output = restored_scenario_preview(current_card(False), NOW)
        self.assertFalse(output["observed_exhibition_only"])
        self.assertNotIn("numeric_exhibition_ST", output["used_features"])
        self.assertNotIn("exhibition_course_only", output["used_features"])
        self.assertIn("numeric_exhibition_ST", output["missing_or_unverified"])
        self.assertIn("exhibition_course", output["missing_or_unverified"])

    def test_flagged_F_is_not_silently_cast_to_positive_or_zero(self):
        card = current_card()
        card["beforeinfo"]["start_exhibition"][1]["st"] = "F.03"
        output = restored_scenario_preview(card, NOW)
        self.assertIn("numeric_exhibition_ST", output["missing_or_unverified"])
        self.assertFalse(output["formal"])

    def test_past_replay_outcome_and_cross_race_refused(self):
        for change in (
            {"meta": {"phase": "HISTORICAL_READ_ONLY"}},
            {"race_key": "20261112-05-02"},
            {"result": {"trifecta": "1-2-3"}},
            {"payout": 1000},
            {"meta": {"results_seen": True}},
        ):
            card = current_card()
            for key, v in change.items():
                if key == "meta":
                    card["meta"].update(v)
                else:
                    card[key] = v
            with self.subTest(change=change), self.assertRaises(ValueError):
                restored_scenario_preview(card, NOW)
        with self.assertRaisesRegex(ValueError, "race_deadline_already_passed"):
            restored_scenario_preview(current_card(),
                                      datetime(2026, 11, 12, 12, 0, tzinfo=JST))
        with self.assertRaisesRegex(ValueError, "unverified_jst_original_clock"):
            card = current_card()
            card["source_audit"]["race_card"]["fetched_at"] = "2026-11-12T00:20:00+00:00"
            restored_scenario_preview(card, NOW)

    def test_six_source_and_exhibition_identity_rejections(self):
        mutants = []
        a = current_card(); a["racers"].pop(); mutants.append(a)
        a = current_card(); a["racers"][1]["registration_no"] = "3001"; mutants.append(a)
        a = current_card(); a["source_audit"]["race_card"]["predeadline_verified"] = False; mutants.append(a)
        a = current_card(); a["source_audit"]["race_card"]["sha256"] = ""; mutants.append(a)
        a = current_card(); a["beforeinfo"]["racers"][0]["lane"] = 2; mutants.append(a)
        a = current_card(); a["meta"]["date"] = "2026-11-11"; mutants.append(a)
        a = current_card(); a["racers"][0]["scratched"] = True; mutants.append(a)
        for num, card in enumerate(mutants):
            with self.subTest(idx=num), self.assertRaises(ValueError):
                restored_scenario_preview(card, NOW)

    def test_api_routes_only_current_results_and_originals_are_untouched(self):
        recorded = []
        def loader(hd, jcd, rno):
            recorded.append((hd,jcd,rno))
            return current_card()
        status, record = get_restored_scenario_preview(
            {"hd":["20261112"],"jcd":["05"],"rno":["1"]},
            card_loader=loader, now=NOW)
        self.assertEqual(status, 200)
        self.assertEqual(record["model_version"], MODEL_VERSION)
        self.assertEqual(recorded, [("20261112", "05", "1")])
        self.assertEqual(get_restored_scenario_preview(
            {"hd":["20261112"],"jcd":["05"],"rno":["1"]},
            card_loader=loader,
            now=datetime(2026,11,12,12,1,tzinfo=JST))[0], 422)
        self.assertEqual(get_restored_scenario_preview(
            {"hd":["20261112"],"jcd":["99"],"rno":["1"]},
            card_loader=loader, now=NOW)[0], 400)
        original_code = "202611111001"
        status, stored = archived_four_modes(original_code)
        self.assertEqual(status, 200)
        self.assertEqual(stored["model_version"],
                         "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED")
        self.assertFalse(stored["production_forecast"])

if __name__ == "__main__":
    unittest.main()
