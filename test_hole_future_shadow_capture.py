"""Future-only same-job hole shadow freeze tests (never formal predeadline proof)."""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch

from hole_shadow_prospective_gate import freeze,JST

CODE="202611040101"
BASE=["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
      "1-4-3","1-4-5","1-2-5","1-3-5","1-2-6"]
CANDIDATE=BASE[:5]+["1-5-3","1-6-3"]+BASE[5:8]

class FutureFrozenTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"four_mode_forecasts").mkdir()
        self.blob=b'{"input_national_win_rates":[4,5,6,7,8,9]}'
        (self.root/"four_mode_forecasts"/(CODE+".json")).write_bytes(self.blob)
        self.cutoff=datetime(2026,11,4,12,0,tzinfo=JST)
        self.archive={"deadline_jst":self.cutoff.isoformat(),
                      "model_version":"CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
                      "modes":{"hole":{"tickets":[{"combo":t,"p":1.0} for t in BASE]},
                               "hit":{"tickets":[{"combo":"1-5-2","p":2},
                                                 {"combo":"1-5-3","p":1.5},
                                                 {"combo":"1-6-2","p":2},
                                                 {"combo":"1-6-3","p":1.5}]},
                               "balance":{"tickets":[]}}}
        self.expected={"baseline":BASE,"donor_order":CANDIDATE,
                       "max_ticket_score":CANDIDATE,
                       "third_national_rate":CANDIDATE}
    def test_future_candidates_frozen_with_source_hash_and_local_timestamp(self):
        with patch("hole_shadow_prospective_gate.archived_four_modes",return_value=(200,self.archive)),patch(
             "hole_shadow_prospective_gate.variants",return_value=self.expected),patch(
             "hole_shadow_prospective_gate.verify_locked_selection",return_value={"selector":"abc"}):
            output=freeze(CODE,self.root,self.cutoff-timedelta(minutes=15))
        self.assertEqual(output["future_locked_candidates"],self.expected)
        self.assertEqual(output["future_locked_selector_git_blobs"],{"selector":"abc"})
        self.assertEqual(output["source_sha256"],hashlib.sha256(self.blob).hexdigest())
        self.assertFalse(output["independent_first_receipt_verified"])
        self.assertFalse(output["prospective_verified"])
    def test_future_modified_top5_is_rejected(self):
        wrong={k:list(v) for k,v in self.expected.items()}
        wrong["third_national_rate"][0]="2-1-3"
        with patch("hole_shadow_prospective_gate.archived_four_modes",return_value=(200,self.archive)),patch(
             "hole_shadow_prospective_gate.variants",return_value=wrong),patch(
             "hole_shadow_prospective_gate.verify_locked_selection",return_value={}):
            with self.assertRaisesRegex(ValueError,"locked_candidate_budget"):
                freeze(CODE,self.root,self.cutoff-timedelta(minutes=15))
    def test_future_past_deadline_never_freezes(self):
        with patch("hole_shadow_prospective_gate.archived_four_modes",return_value=(200,self.archive)):
            self.assertEqual(freeze(CODE,self.root,self.cutoff)["status"],"past_deadline")
    def test_no_postrace_results_read_during_freeze(self):
        with patch("hole_shadow_prospective_gate.archived_four_modes",return_value=(200,self.archive)),patch(
             "hole_shadow_prospective_gate.verify_locked_selection",return_value={}),patch(
             "hole_shadow_prospective_gate.variants",return_value=self.expected),patch(
             "four_mode_frozen_diagnostic.compare_race",side_effect=AssertionError("result leaked")):
            self.assertEqual(freeze(CODE,self.root,self.cutoff-timedelta(hours=1))["status"],
                             "shadow_frozen_unverified")

if __name__=="__main__":unittest.main()
