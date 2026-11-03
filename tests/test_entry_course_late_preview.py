import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from test_entry_course_prospective_capture import fixture
from entry_course_late_preview import prepare_late_preview_study
from entry_course_prospective_capture import prepare_prospective_capture
from entry_course_write_once import freeze_capture

JST=timezone(timedelta(hours=9))
DEADLINE="2026-11-03T18:33:00+09:00"
T12="2026-11-03T18:21:00+09:00"
T2="2026-11-03T18:31:00+09:00"
PREVIEW="2026-11-03T18:28:00+09:00"
FROZEN="2026-11-03T18:29:00+09:00"

def inputs():
    base,card,batch=fixture()
    base["generated_at"]="2026-11-03T18:00:00+09:00"
    base["cutoff_jst"]=T12
    base["source_deadline_jst"]=DEADLINE
    card["meta"]["deadline"]="18:33"
    card["source_audit"]["race_card"]["fetched_at"]=PREVIEW
    card["source_audit"]["beforeinfo"]["sources"]["stt"]["observed_at"]=PREVIEW
    card["source_audit"]["beforeinfo"]["sources"]["tkz"]["observed_at"]=PREVIEW
    batch["cutoff_at"]=T2
    batch["history"][0]["card_receipt_at"]=PREVIEW
    batch["history"][0]["result_receipt_at"]=PREVIEW
    return base,card,batch

class LatePreviewTests(unittest.TestCase):
    def test_t5_preview_blocked_from_t12_but_late_study_is_distinct(self):
        base,card,batch=inputs()
        with self.assertRaisesRegex(ValueError,"capture_not_pre_cutoff"):
            prepare_prospective_capture(base,card,batch,frozen_at=FROZEN,min_starts=1)
        outcome=prepare_late_preview_study(base,card,batch,frozen_at=FROZEN,min_starts=1)
        self.assertTrue(outcome["not_equivalent_to_t12"])
        self.assertEqual(outcome["cutoff_at"],T2)
        self.assertEqual(outcome["reference_baseline_cutoff_at"],T12)
        self.assertEqual(outcome["reference_t12_top10"],base["predictions"])
        for name in ("baseline","course","course_plus_st"):
            self.assertEqual(len(outcome[name]),120)
            self.assertEqual(len(set(outcome[name])),120)
        self.assertFalse(outcome["formal"])
        self.assertFalse(outcome["independent_remote_first_seen_verified"])
    def test_wrong_racecard_deadline_rejected(self):
        base,card,batch=inputs()
        card["meta"]["deadline"]="18:34"
        with self.assertRaisesRegex(ValueError,"card_deadline_mismatch"):
            prepare_late_preview_study(base,card,batch,frozen_at=FROZEN,min_starts=1)
    def test_racecard_receipt_after_freeze_rejected(self):
        base,card,batch=inputs()
        card["source_audit"]["race_card"]["fetched_at"]="2026-11-03T18:30:00+09:00"
        with self.assertRaisesRegex(ValueError,"card_provenance_missing_or_after_freeze"):
            prepare_late_preview_study(base,card,batch,frozen_at=FROZEN,min_starts=1)
    def test_missing_racecard_hash_rejected(self):
        base,card,batch=inputs()
        card["source_audit"]["race_card"]["sha256"]=None
        with self.assertRaisesRegex(ValueError,"card_provenance_missing_or_after_freeze"):
            prepare_late_preview_study(base,card,batch,frozen_at=FROZEN,min_starts=1)
    def test_future_preview_is_never_admissible(self):
        base,card,batch=inputs()
        card["source_audit"]["beforeinfo"]["sources"]["stt"]["observed_at"]="2026-11-03T18:32:00+09:00"
        with self.assertRaisesRegex(ValueError,"late_preview_missing"):
            prepare_late_preview_study(base,card,batch,frozen_at=FROZEN,min_starts=1)
    def test_preview_receipt_after_candidate_freeze_rejected(self):
        base,card,batch=inputs()
        late="2026-11-03T18:30:00+09:00"
        card["source_audit"]["beforeinfo"]["sources"]["stt"]["observed_at"]=late
        with self.assertRaisesRegex(ValueError,"late_preview_not_observed_at_freeze"):
            prepare_late_preview_study(base,card,batch,frozen_at=FROZEN,min_starts=1)
    def test_historical_source_receipt_after_candidate_freeze_rejected(self):
        base,card,batch=inputs()
        batch["history"][0]["result_receipt_at"]="2026-11-03T18:30:00+09:00"
        with self.assertRaisesRegex(ValueError,"late_history_not_observed_at_freeze"):
            prepare_late_preview_study(base,card,batch,frozen_at=FROZEN,min_starts=1)
    def test_late_history_cutoff_is_not_t12_cutoff(self):
        base,card,batch=inputs()
        batch["cutoff_at"]=T12
        with self.assertRaisesRegex(ValueError,"history_cutoff_mismatch"):
            prepare_late_preview_study(base,card,batch,frozen_at=FROZEN,min_starts=1)
    def test_t2_candidate_must_be_frozen_before_t2(self):
        base,card,batch=inputs()
        with self.assertRaisesRegex(ValueError,"not_frozen_in_late_window"):
            prepare_late_preview_study(base,card,batch,frozen_at=T2,min_starts=1)
    def test_fail_on_insufficient_samples(self):
        base,card,batch=inputs()
        with self.assertRaisesRegex(ValueError,"insufficient_course_samples"):
            prepare_late_preview_study(base,card,batch,frozen_at=FROZEN,min_starts=10)
    def test_exclusive_local_write_does_not_equal_remote_publication(self):
        base,card,batch=inputs()
        study=prepare_late_preview_study(base,card,batch,frozen_at=FROZEN,min_starts=1)
        with tempfile.TemporaryDirectory() as tmp:
            path=freeze_capture(study,tmp,clock=lambda:datetime(2026,11,3,18,30,tzinfo=JST))
            self.assertTrue(path.is_file())
            self.assertIn('"independently_archived": false',path.read_text())
            with self.assertRaises(FileExistsError):
                freeze_capture(study,tmp,clock=lambda:datetime(2026,11,3,18,30,tzinfo=JST))
            with self.assertRaisesRegex(ValueError,"capture_write_after_cutoff"):
                freeze_capture(study,tmp,clock=lambda:datetime(2026,11,3,18,32,tzinfo=JST))
if __name__=="__main__":unittest.main()
