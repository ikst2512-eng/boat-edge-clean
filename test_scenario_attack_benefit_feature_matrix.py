"""Nonformal scenario interaction contract: course-aware, no zero-filling or leakage."""
import copy
import unittest

from scenario_attack_benefit_feature_matrix import build_attack_benefit_matrix


def receipt(value=None, size=20):
    base = {
        "source_sha256": "a" * 64,
        "received_at_jst": "2026-11-15T09:45:00+09:00",
        "source_url": "https://www.boatrace.jp/",
    }
    if value is not None:
        base.update(value=value, sample_size=size)
    return base


def fixture():
    racers = []
    for i in range(1, 7):
        signals = {
            "motor_2ren_pct": receipt(45 + i, 60),
            "meeting_2ren_pct": receipt(35 + i, 5),
            "average_st_s": receipt(0.15, 100),
            "meeting_st_s": receipt(0.12, 5),
            "makuri_pct": receipt(25, 30),
            "makuri_sashi_pct": receipt(20, 30),
            "sashi_pct": receipt(30, 30),
        }
        if i == 2:
            signals["two_escape_assist_pct"] = receipt(80, 30)
        comment = dict(receipt(), annotation_method="manual_verified_quote",
                       quote="旋回足に手応え", tags=["turn_positive"])
        racers.append({
            "boat": i, "exhibition_course": i, "signals": signals,
            "comment": comment,
        })
    return {
        "schema": "SCENARIO_PRE_RACE_FEATURE_CLAIMS_V1",
        "race_code": "202611151209",
        "generated_at_jst": "2026-11-15T10:00:00+09:00",
        "deadline_at_jst": "2026-11-15T11:00:00+09:00",
        "exhibition_entry_source": receipt(),
        "racers": racers,
    }


class InteractionTests(unittest.TestCase):
    def test_all_120_with_attack_benefit_paths(self):
        x = build_attack_benefit_matrix(fixture())
        self.assertEqual(x["count"], 120)
        self.assertEqual(len({v["ticket"] for v in x["rows"]}), 120)
        by_ticket = {r["ticket"]: r["features"] for r in x["rows"]}
        self.assertAlmostEqual(by_ticket["3-4-5"]["third_attack_four_sashi_second"], .075)
        self.assertAlmostEqual(by_ticket["4-3-5"]["third_attack_four_sashi_head"], .075)
        self.assertAlmostEqual(by_ticket["5-3-4"]["third_attack_five_makuri_sashi_head"], .05)
        self.assertAlmostEqual(by_ticket["3-4-5"]["second_motor_2ren"], .49)
        self.assertAlmostEqual(by_ticket["3-4-5"]["third_meeting_2ren"], .40)
        self.assertEqual(by_ticket["3-4-5"]["second_comment_turn"], 1)
        self.assertAlmostEqual(by_ticket["3-5-4"]["third_attack_five_makuri_sashi_second"], .05)
        self.assertAlmostEqual(by_ticket["3-4-5"]["third_attack_five_makuri_sashi_third"], .05)
        self.assertAlmostEqual(by_ticket["1-2-3"]["escape_two_escape_assist_proxy"], .8)
        self.assertAlmostEqual(by_ticket["3-4-5"]["third_attack_two_escape_assist_obstacle_proxy"], .2)
        self.assertEqual(by_ticket["1-2-3"]["third_attack_four_sashi_second"], 0.0)
        self.assertFalse(x["predicted_probabilities"])
        self.assertFalse(x["production_changed"])
        self.assertEqual(x["feature_matrix_sha256"], build_attack_benefit_matrix(fixture())["feature_matrix_sha256"])

    def test_exhibition_course_not_boat_assumption(self):
        x = fixture()
        x["racers"][0]["exhibition_course"] = 3
        x["racers"][2]["exhibition_course"] = 1
        y = build_attack_benefit_matrix(x)
        by_ticket = {r["ticket"]: r["features"] for r in y["rows"]}
        self.assertAlmostEqual(by_ticket["1-4-5"]["third_attack_four_sashi_second"], .075)
        self.assertEqual(by_ticket["3-4-5"]["third_attack_four_sashi_second"], 0.0)
        self.assertEqual(y["course_to_boat"]["1"], 3)

    def test_missing_is_unknown_not_zero(self):
        x = fixture()
        x["racers"][4]["signals"].pop("makuri_sashi_pct")
        x["racers"][2]["comment"] = None
        y = build_attack_benefit_matrix(x)
        v = {r["ticket"]: r["features"] for r in y["rows"]}
        self.assertIsNone(v["3-5-4"]["third_attack_five_makuri_sashi_second"])
        self.assertIsNone(v["3-4-5"]["head_comment_turn"])
        self.assertEqual(v["1-2-3"]["third_attack_five_makuri_sashi_second"], 0.0)

    def test_post_cutoff_receipt_rejected(self):
        x = fixture()
        x["racers"][2]["signals"]["makuri_pct"]["received_at_jst"] = "2026-11-15T10:10:00+09:00"
        with self.assertRaisesRegex(ValueError, "post_generation"):
            build_attack_benefit_matrix(x)

    def test_outcome_and_final_course_leakage_rejected(self):
        for place in ("top", "racer"):
            x = fixture()
            if place == "top":
                x["result"] = [3, 4, 5]
            else:
                x["racers"][0]["final_entry"] = 1
            with self.assertRaisesRegex(ValueError, "leakage|post_race"):
                build_attack_benefit_matrix(x)

    def test_comments_not_auto_inferred(self):
        x = fixture()
        x["racers"][0]["comment"]["annotation_method"] = "llm_guess"
        with self.assertRaisesRegex(ValueError, "manual_comment"):
            build_attack_benefit_matrix(x)

    def test_invalid_denominator_rejected(self):
        x = fixture()
        x["racers"][2]["signals"]["makuri_pct"]["sample_size"] = 0
        with self.assertRaisesRegex(ValueError, "denominator|sample"):
            build_attack_benefit_matrix(x)

    def test_after_deadline_recompute_rejected(self):
        x = fixture()
        x["generated_at_jst"] = "2026-11-15T11:05:00+09:00"
        with self.assertRaisesRegex(ValueError, "post_deadline"):
            build_attack_benefit_matrix(x)


if __name__ == "__main__":
    unittest.main()
