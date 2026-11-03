import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from hole_future_locked_eval import evaluate

CODE="202611040101"

class FutureLockedEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/"four_mode_forecasts").mkdir()
        (self.root/"four_mode_forecasts"/(CODE+".json")).write_text("{}")
        self.archive={"model_version":"CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
                      "generated_at_jst":"2026-11-04T09:00:00+09:00",
                      "deadline_jst":"2026-11-04T10:00:00+09:00"}
        self.picks={"baseline":["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
                                 "1-4-3","1-4-5","1-2-5","1-3-5","1-2-6"],
                    "donor_order":["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
                                   "1-5-2","1-6-2","1-4-3","1-4-5","1-2-5"],
                    "max_ticket_score":["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
                                         "1-5-2","1-6-2","1-4-3","1-4-5","1-2-5"],
                    "third_national_rate":["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
                                           "1-5-3","1-6-3","1-4-3","1-4-5","1-2-5"]}
    def test_excludes_all_prior_dates_even_if_present(self):
        self.assertEqual(evaluate(self.root,date(2026,11,3))["status"],"not_yet_eligible")
        (self.root/"four_mode_forecasts"/"202611030101.json").write_text("{}")
        with patch("hole_future_locked_eval.archived_four_modes",return_value=(200,self.archive)),patch(
            "hole_future_locked_eval.national_rates",return_value=None),patch(
            "hole_future_locked_eval.variants",return_value=self.picks),patch(
            "hole_future_locked_eval.compare_race",
            return_value={"status":"historical_comparison_only","winning_ticket":"1-5-3"}):
            r=evaluate(self.root,date(2026,11,4))
        self.assertEqual(r["comparable"],1)
        self.assertEqual(r["race_codes"],[CODE])
        self.assertEqual(r["race_flags"][CODE]["third_national_rate"]["top10"],True)
        self.assertEqual(r["delta"]["third_national_rate"]["top10"]["net"],1)
        self.assertEqual(r["delta"]["donor_order"]["top10"]["net"],0)
        self.assertFalse(r["formal"])
        self.assertFalse(r["independent_first_receipt_verified"])
    def test_results_missing_is_not_success(self):
        with patch("hole_future_locked_eval.archived_four_modes",return_value=(200,self.archive)),patch(
            "hole_future_locked_eval.national_rates",return_value=None),patch(
            "hole_future_locked_eval.variants",return_value=self.picks),patch(
            "hole_future_locked_eval.compare_race",return_value={"status":"result_unavailable"}):
            r=evaluate(self.root,date(2026,11,4))
        self.assertEqual(r["status"],"insufficient_new_confirmed_races")
        self.assertEqual(r["excluded_by_reason"],{"unconfirmed_result":1})
    def test_disallow_top5_change(self):
        wrong=dict(self.picks)
        wrong["third_national_rate"]=list(self.picks["donor_order"])
        wrong["third_national_rate"][0]="2-1-3"
        with patch("hole_future_locked_eval.archived_four_modes",return_value=(200,self.archive)),patch(
            "hole_future_locked_eval.national_rates",return_value=None),patch(
            "hole_future_locked_eval.variants",return_value=wrong):
            with self.assertRaises(ValueError):evaluate(self.root,date(2026,11,4))
    def test_invalid_candidate_day_not_counted(self):
        a=dict(self.archive,deadline_jst="2026-11-03T23:30:00+09:00")
        with patch("hole_future_locked_eval.archived_four_modes",return_value=(200,a)):
            r=evaluate(self.root,date(2026,11,4))
        self.assertEqual(r["comparable"],0)
        self.assertEqual(r["excluded_by_reason"],{"local_timing_invalid":1})
    def test_daily_model_denominators_and_evidence_gate(self):
        second="202611050101"
        third="202611050102"
        (self.root/"four_mode_forecasts"/(second+".json")).write_text("{}")
        (self.root/"four_mode_forecasts"/(third+".json")).write_text("{}")
        def archive(code,root):
            template=dict(self.archive)
            if code!=CODE:
                template["deadline_jst"]="2026-11-05T10:00:00+09:00"
                template["generated_at_jst"]="2026-11-05T09:00:00+09:00"
                template["model_version"]="CLEAN_FOUR_MODES_V1_UNCALIBRATED"
            return 200,template
        def confirmed(code,root):
            if code==third:
                return {"status":"result_unavailable"}
            return {"status":"historical_comparison_only",
                    "winning_ticket":"1-5-3" if code==CODE else "1-2-3"}
        with patch("hole_future_locked_eval.archived_four_modes",side_effect=archive),patch(
            "hole_future_locked_eval.national_rates",return_value=None),patch(
            "hole_future_locked_eval.variants",return_value=self.picks),patch(
            "hole_future_locked_eval.compare_race",side_effect=confirmed):
            output=evaluate(self.root,date(2026,11,5))
        self.assertEqual(output["scanned_valid_date_codes"],3)
        self.assertEqual(output["comparable"],2)
        self.assertEqual(output["excluded_by_reason"],{"unconfirmed_result":1})
        self.assertEqual(output["by_day"]["2026-11-04"]["comparable"],1)
        self.assertEqual(output["by_day"]["2026-11-05"]["scanned"],2)
        self.assertEqual(output["by_day"]["2026-11-05"]["comparable"],1)
        self.assertEqual(output["by_day"]["2026-11-05"]["excluded"],{"unconfirmed_result":1})
        self.assertEqual(
            output["by_model_version"]["CLEAN_FOUR_MODES_V1_UNCALIBRATED"]["comparable"],1)
        self.assertEqual(
            output["by_model_version"]["CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"]["comparable"],1)
        self.assertEqual(output["by_day"]["2026-11-04"]["hits"]["third_national_rate"]["top10"],1)
        self.assertEqual(output["hits"]["third_national_rate"]["top10"],2)
        self.assertFalse(output["evidence_quality"]["independent_remote_first_receipt_proof_present"])
        self.assertFalse(output["evidence_quality"]["eligible_for_formal_accuracy"])

    def test_missing_result_is_counted_by_day_not_a_hit(self):
        with patch("hole_future_locked_eval.archived_four_modes",return_value=(200,self.archive)),patch(
            "hole_future_locked_eval.national_rates",return_value=None),patch(
            "hole_future_locked_eval.variants",return_value=self.picks),patch(
            "hole_future_locked_eval.compare_race",return_value={"status":"result_unavailable"}):
            result=evaluate(self.root,date(2026,11,4))
        self.assertEqual(result["by_day"]["2026-11-04"]["scanned"],1)
        self.assertEqual(result["by_day"]["2026-11-04"]["comparable"],0)
        self.assertEqual(result["by_day"]["2026-11-04"]["excluded"]["unconfirmed_result"],1)
        self.assertEqual(result["by_model_version"],{})
    def test_reject_invalid_window(self):
        with self.assertRaises(ValueError):evaluate(self.root,date(2026,11,4),days=32)

if __name__=="__main__":
    unittest.main()
