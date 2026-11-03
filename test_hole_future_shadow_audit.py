"""Read-only frozen candidate audit integrity tests."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hole_future_shadow_audit import audit
from hole_future_locked_eval import LOCKED_SELECTION_BLOBS

CODE="202611040101"
BASE=["1-2-3","1-2-4","1-3-2","1-3-4","1-4-2",
      "1-4-3","1-4-5","1-2-5","1-3-5","1-2-6"]
ALTERNATE=BASE[:5]+["1-5-3","1-6-3"]+BASE[5:8]

class ShadowAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"four_mode_forecasts").mkdir()
        raw=b'{"input_national_win_rates":[4,5,6,7,8,9]}'
        (self.root/"four_mode_forecasts"/(CODE+".json")).write_bytes(raw)
        self.candidates={"baseline":BASE,"donor_order":BASE,
                         "max_ticket_score":ALTERNATE,
                         "third_national_rate":ALTERNATE}
        self.record={"race_code":CODE,"status":"shadow_frozen_unverified",
                     "source_sha256":hashlib.sha256(raw).hexdigest(),
                     "local_freeze_at_jst":"2026-11-04T09:00:00+09:00",
                     "deadline_jst":"2026-11-04T10:00:00+09:00",
                     "future_locked_candidates":self.candidates,
                     "future_locked_selector_git_blobs":LOCKED_SELECTION_BLOBS}
        self.shadow=self.root/"hole-shadow.json"
        self.archive={"deadline_jst":"2026-11-04T10:00:00+09:00"}
    def store(self):
        self.shadow.write_text(json.dumps({"status":"research_only_after_confirmed_push",
                                           "records":[self.record]}))
    def review(self):
        with patch("hole_future_shadow_audit.archived_four_modes",return_value=(200,self.archive)),patch(
             "hole_future_shadow_audit.national_rates",return_value=[4,5,6,7,8,9]),patch(
             "hole_future_shadow_audit.variants",return_value=self.candidates),patch(
             "hole_future_shadow_audit.compare_race",
             return_value={"status":"historical_comparison_only","winning_ticket":"1-5-3"}):
            return audit(self.root,self.shadow)
    def test_original_frozen_candidate_comparison(self):
        self.store()
        x=self.review()
        self.assertEqual(x["comparable"],1)
        self.assertEqual(x["eligible_codes"],[CODE])
        self.assertEqual(x["delta"]["third_national_rate"]["top10"]["gained"],1)
        self.assertFalse(x["formal"])
    def test_candidate_tampering_is_excluded(self):
        self.record["future_locked_candidates"]=dict(self.candidates,third_national_rate=BASE)
        self.store()
        x=self.review()
        self.assertEqual(x["comparable"],0)
        self.assertEqual(x["excluded_by_reason"]["candidate_replay_mismatch"],1)
        self.assertEqual(x["eligible_codes"],[])
    def test_method_tampering_is_excluded(self):
        self.record["future_locked_selector_git_blobs"]={"wrong":"hash"}
        self.store()
        x=self.review()
        self.assertEqual(x["excluded_by_reason"]["selection_method_mismatch"],1)
    def test_after_cutoff_is_excluded(self):
        self.record["local_freeze_at_jst"]="2026-11-04T10:01:00+09:00"
        self.store()
        x=self.review()
        self.assertEqual(x["excluded_by_reason"]["local_timing_invalid"],1)
    def test_result_not_yet_confirmed_is_valid_freeze_not_hit(self):
        self.store()
        with patch("hole_future_shadow_audit.archived_four_modes",return_value=(200,self.archive)),patch(
             "hole_future_shadow_audit.national_rates",return_value=[4,5,6,7,8,9]),patch(
             "hole_future_shadow_audit.variants",return_value=self.candidates),patch(
             "hole_future_shadow_audit.compare_race",return_value={"status":"result_pending"}):
            x=audit(self.root,self.shadow)
        self.assertEqual(x["eligible_codes"],[CODE])
        self.assertEqual(x["comparable"],0)
        self.assertEqual(x["excluded_by_reason"]["unconfirmed_result"],1)
    def test_no_unverified_files_count_as_hits(self):
        x=audit(self.root,self.shadow)
        self.assertEqual(x["status"],"missing_shadow")
        self.assertFalse(x["formal"])

if __name__=="__main__":
    unittest.main()
