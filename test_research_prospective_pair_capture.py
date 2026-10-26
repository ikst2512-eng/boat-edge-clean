import unittest
from datetime import datetime, timedelta
from research_model import JST, probabilities
from research_prospective_pair_capture import freeze_record, capture

class PairCaptureTests(unittest.TestCase):
    def example(self):
        now=datetime(2026,10,28,9,0,tzinfo=JST)
        rates=[6]*6
        return now, {"race_code":"202610281201","status":"research","validated":False,
                "model_version":"national-beta0.4-exploratory-v1",
                "cutoff_jst":(now+timedelta(minutes=20)).isoformat(),
                "generated_at":(now-timedelta(minutes=1)).isoformat(),
                "source_title_received_jst":(now-timedelta(minutes=2)).isoformat(),
                "source_cards_received_jst":(now-timedelta(minutes=2)).isoformat(),
                "national_win_rates":rates,
                "predictions":["-".join(map(str,t)) for t,p in probabilities(rates)[:10]]}
    def test_freeze_120_without_scoring(self):
        now,row=self.example()
        pair=freeze_record(row,now)
        self.assertEqual(len(pair["baseline"]),120)
        self.assertEqual(len(pair["candidate"]),120)
        self.assertFalse(pair["prospective_verified"])
        self.assertEqual(pair["entry_status"],"assumed_identity_not_verified")
    def test_cutoff_refused(self):
        now,row=self.example()
        with self.assertRaises(ValueError):
            freeze_record(row,now+timedelta(minutes=20))
    def test_modified_baseline_refused(self):
        now,row=self.example()
        row["predictions"][0]="6-5-4"
        with self.assertRaises(ValueError):
            freeze_record(row,now)
    def test_existing_pair_source_mismatch_fails_closed(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        now,row=self.example()
        with tempfile.TemporaryDirectory() as root:
            inputs=Path(root)/"inputs"
            outputs=Path(root)/"outputs"
            inputs.mkdir()
            outputs.mkdir()
            (inputs/"202610281201.json").write_text(json.dumps(row),encoding="utf-8")
            (outputs/"202610281201.json").write_text(json.dumps({
                "race_code":row["race_code"],"candidate_git_blob_sha":"724cf7e83d491f4570bdd28cec72720cf5d03815",
                "source_snapshot_sha256":"0"*64}),encoding="utf-8")
            with patch("research_prospective_pair_capture.verify_candidate_source"):
                with self.assertRaisesRegex(ValueError,"existing pair"):
                    capture("20261028",inputs,outputs,now=now)

if __name__=="__main__":
    unittest.main()
