"""Fail-closed regression gates for research-only hole pair precommit."""
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
import hole_future_pair_precommit as s

JST=timezone(timedelta(hours=9))
CODE="202611060101"
CUTOFF=datetime(2026,11,6,10,0,tzinfo=JST)
START=CUTOFF-timedelta(minutes=5)
FINISH=CUTOFF-timedelta(minutes=4)
BASE=["1-2-3","1-2-4","1-3-2","1-3-4","2-1-3",
      "2-1-4","1-4-2","1-4-3","2-3-1","2-3-4"]

def archive():
    tickets=lambda xs:[{"combo":x,"p":3.0} for x in xs]
    return {"deadline_jst":(CUTOFF+timedelta(minutes=12)).isoformat(),
            "model_version":"CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
            "modes":{"hole":{"tickets":tickets(BASE)},
                     "hit":{"tickets":tickets(["1-5-2","1-5-3","2-4-1","2-5-1"]+BASE)},
                     "balance":{"tickets":tickets(["1-5-2","1-5-3","2-4-1","2-5-1"]+BASE)}}}

class PairPrecommitTest(unittest.TestCase):
    def test_nov05_not_eligible_without_archive_or_result(self):
        with patch.object(s,"archived_four_modes",side_effect=AssertionError("opened archive")):
            r=s.freeze("202611050101",".")
        self.assertEqual(r["status"],"not_yet_eligible_or_invalid_code")
        self.assertFalse(r["formal"])

    def test_t12_start_and_end_boundaries(self):
        with patch.object(s,"archived_four_modes",return_value=(200,archive())):
            r=s.freeze(CODE,".",started_at=CUTOFF)
        self.assertEqual(r["status"],"after_t_minus_12")
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"four_mode_forecasts").mkdir()
            (root/"four_mode_forecasts"/(CODE+".json")).write_text("archived",encoding="utf-8")
            with patch.object(s,"archived_four_modes",return_value=(200,archive())), \
                 patch.object(s,"verify_locked_selection",return_value={"pinned":"sha"}):
                r=s.freeze(CODE,root,started_at=START,completed_at=CUTOFF)
            self.assertEqual(r["status"],"calculation_crossed_t_minus_12")
            self.assertFalse(r["formal"])

    def test_fixed_policies_and_result_blind_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"four_mode_forecasts").mkdir()
            (root/"four_mode_forecasts"/(CODE+".json")).write_text("archived",encoding="utf-8")
            events=[]
            actual_select = s.select
            def choosing(arc):
                events.append("choose")
                return actual_select(arc)
            def reading(code,root):
                events.append("result")
                return {"status":"historical_comparison_only","winning_ticket":"1-5-2"}
            with patch.object(s,"archived_four_modes",return_value=(200,archive())), \
                 patch.object(s,"verify_locked_selection",return_value={"pinned":"sha"}):
                r=s.freeze(CODE,root,started_at=START,completed_at=FINISH)
                self.assertEqual(r["status"],"locally_frozen_unverified")
                self.assertEqual(r["candidates"]["baseline"][:5],
                                 r["candidates"]["same_pair_two_thirds"][:5])
                self.assertEqual(r["candidates"]["baseline"][:5],
                                 r["candidates"]["two_pairs_one_third"][:5])
                self.assertNotEqual(r["candidates"]["baseline"],r["candidates"]["same_pair_two_thirds"])
                self.assertNotEqual(r["candidates"]["baseline"],r["candidates"]["two_pairs_one_third"])
                with patch.object(s,"select",side_effect=choosing), \
                     patch.object(s,"compare_race",side_effect=reading):
                    reviewed=s.review(r,root)
            self.assertEqual(events,["choose","result"])
            self.assertEqual(reviewed["status"],"reference_scored_without_independent_receipt")
            self.assertFalse(reviewed["formal"])
            self.assertEqual(reviewed["ranks"]["baseline"],0)
            self.assertEqual(reviewed["ranks"]["same_pair_two_thirds"],6)
            self.assertEqual(reviewed["ranks"]["two_pairs_one_third"],6)
            self.assertEqual(reviewed["gain_loss"]["same_pair_two_thirds"]["top10"]["gained"],1)
            self.assertEqual(reviewed["gain_loss"]["two_pairs_one_third"]["top10"]["gained"],1)
            self.assertEqual(reviewed["gain_loss"]["two_pairs_one_third"]["top5"]["gained"],0)

    def test_corrupt_or_false_attestation_prevents_outcome_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"four_mode_forecasts").mkdir()
            (root/"four_mode_forecasts"/(CODE+".json")).write_text("archived",encoding="utf-8")
            with patch.object(s,"archived_four_modes",return_value=(200,archive())), \
                 patch.object(s,"verify_locked_selection",return_value={"pinned":"sha"}):
                record=s.freeze(CODE,root,started_at=START,completed_at=FINISH)
                record["independent_first_receipt_verified"]=True
                with patch.object(s,"compare_race",side_effect=AssertionError("opened result")):
                    a=s.review(record,root)
                self.assertEqual(a["status"],"invalid_method_or_claim")
                record["independent_first_receipt_verified"]=False
                record["candidates"]["baseline"][0]="9-9-9"
                with patch.object(s,"compare_race",side_effect=AssertionError("opened result")):
                    b=s.review(record,root)
                self.assertEqual(b["status"],"candidate_replay_mismatch")

if __name__=="__main__":unittest.main()
