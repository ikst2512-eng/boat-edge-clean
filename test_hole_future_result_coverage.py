"""Verify confirmed-result attrition never becomes reconstructed hole accuracy."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from hole_future_result_coverage import reconcile

A="202611040101"
B="202611040102"
C="202611050101"
OLD="202611030101"

class FutureCoverageTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        directory=self.root/"four_mode_forecasts"
        directory.mkdir()
        for code in (A,B,C,OLD):
            (directory/(code+".json")).write_text("{}")
    def run_coverage(self,observed=(),scored=()):
        def outcome(code,root):
            if code==C:
                return {"status":"result_unavailable"}
            return {"status":"historical_comparison_only","winning_ticket":"1-2-3"}
        with patch("hole_future_result_coverage.archived_four_modes",
                   return_value=(200,{"status":"historical_research_only"})),patch(
             "hole_future_result_coverage.compare_race",side_effect=outcome):
            return reconcile(self.root,"2026-11-04","2026-11-06",observed,scored)
    def test_unobserved_confirmed_is_not_replayed_as_hit(self):
        result=self.run_coverage(observed=[A,C],scored=[A])
        self.assertEqual(result["archived"],3)
        self.assertEqual(result["confirmed"],2)
        self.assertEqual(result["confirmed_scored"],1)
        self.assertEqual(result["confirmed_without_shadow"],1)
        self.assertEqual(result["confirmed_missing_shadow_codes"],[B])
        self.assertEqual(result["unconfirmed_with_shadow"],1)
        self.assertFalse(result["formal"])
        self.assertFalse(result["all_archived_scored"])
    def test_observed_but_unscored_is_distinct_from_missing_shadow(self):
        result=self.run_coverage(observed=[A,B],scored=[A])
        self.assertEqual(result["confirmed_without_shadow"],0)
        self.assertEqual(result["confirmed_shadow_but_unscored"],1)
        self.assertEqual(result["confirmed_unscored_shadow_codes"],[B])
    def test_no_confirmed_cannot_claim_full_coverage(self):
        empty=Path(self.tmp.name)/"empty"
        (empty/"four_mode_forecasts").mkdir(parents=True)
        result=reconcile(empty,"2026-11-04","2026-11-06",[],[])
        self.assertFalse(result["all_archived_scored"])
        self.assertEqual(result["confirmed"],0)
    def test_before_nov4_window_is_ineligible(self):
        result=reconcile(self.root,"2026-11-01","2026-11-03",[],[])
        self.assertEqual(result["status"],"no_eligible_complete_days")
    def test_frozen_score_without_observation_is_blocked(self):
        with self.assertRaisesRegex(ValueError,"scored_without_capture"):
            self.run_coverage(observed=[],scored=[A])
    def test_scored_confirmed_all_present_but_pending_explicit(self):
        result=self.run_coverage(observed=[A,B,C],scored=[A,B])
        self.assertEqual(result["confirmed_without_shadow"],0)
        self.assertFalse(result["all_archived_scored"])
        self.assertEqual(result["unconfirmed"],1)

if __name__=="__main__":
    unittest.main()
