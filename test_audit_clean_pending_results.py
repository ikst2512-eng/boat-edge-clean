import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from audit_clean_pending_results import audit
from research_model import JST

class PendingResultCoverageTests(unittest.TestCase):
    def test_future_missing_result_is_not_overdue_or_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"four_mode_forecasts";p.mkdir()
            (p/"202610290101.json").write_text(json.dumps({"race_code":"202610290101","deadline_jst":"2026-10-29T14:00:00+09:00"}))
            report=audit(tmp,"20261029",datetime(2026,10,29,6,30,tzinfo=JST))
            self.assertEqual(report["before_deadline"],1)
            self.assertEqual(report["awaiting_result_overdue"],0)
            self.assertTrue(report["no_result_is_not_a_miss"])
            late=audit(tmp,"20261029",datetime(2026,10,29,14,30,tzinfo=JST))
            self.assertEqual(late["awaiting_result_overdue"],1)
            self.assertEqual(late["overdue_race_codes"],["202610290101"])
    def test_result_file_present_not_claimed_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"four_mode_forecasts";p.mkdir()
            (p/"202610290101.json").write_text(json.dumps({"race_code":"202610290101","deadline_jst":"2026-10-29T14:00:00+09:00"}))
            q=Path(tmp)/"confirmed_results";q.mkdir()
            (q/"202610290101.json").write_text("{}")
            report=audit(tmp,"20261029",datetime(2026,10,29,15,0,tzinfo=JST))
            self.assertEqual(report["confirmed_result_file_present"],1)
            self.assertEqual(report["confirmed_result_usable"],0)
            self.assertEqual(report["invalid_result_file_present"],1)
            self.assertEqual(report["awaiting_result_overdue"],1)
            self.assertEqual(report["overdue_race_codes"],["202610290101"])
            self.assertFalse(report["official_results_validated"])
    def test_valid_confirmation_closes_gap_but_not_official_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            forecasts=root/"four_mode_forecasts"
            forecasts.mkdir()
            code="202610290101"
            (forecasts/(code+".json")).write_text(json.dumps({
                "race_code":code,"deadline_jst":"2026-10-29T14:00:00+09:00"}))
            confirmed=root/"confirmed_results"
            confirmed.mkdir()
            target=confirmed/(code+".json")
            target.write_text(json.dumps({
                "race_code":code,"status":"confirmed","finish_order":[1,3,2],
                "source_url":"https://boatracecsv.github.io/data/results/realtime/2026/10/29.csv",
                "source_sha256":"a"*64,
                "confirmed_at_jst":"2026-10-29T14:12:00+09:00",
                "collected_at_jst":"2026-10-29T14:15:00+09:00"
            }))
            report=audit(tmp,"20261029",datetime(2026,10,29,16,0,tzinfo=JST))
            self.assertEqual(report["confirmed_result_file_present"],1)
            self.assertEqual(report["confirmed_result_usable"],1)
            self.assertEqual(report["invalid_result_file_present"],0)
            self.assertEqual(report["awaiting_result_overdue"],0)
            self.assertEqual(report["overdue_race_codes"],[])
            self.assertFalse(report["official_results_validated"])

    def test_source_gap_diagnosis_includes_invalid_existing_confirmation(self):
        from collect_clean_results import diagnose_source_gaps
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            forecasts=root/"four_mode_forecasts"
            forecasts.mkdir()
            code="202610290101"
            (forecasts/(code+".json")).write_text(json.dumps({
                "race_code":code,"deadline_jst":"2026-10-29T14:00:00+09:00"}))
            confirmed=root/"confirmed_results"
            confirmed.mkdir()
            (confirmed/(code+".json")).write_text("{}")
            raw=("レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
                 "202610290101,2026-10-29T15:00:00+09:00,1,2,3\n").encode()
            output=diagnose_source_gaps("20261029",root,download=lambda _:raw)
            self.assertEqual(output["unresolved"],1)
            self.assertEqual(output["reasons"][code],"row_present_requires_review")

if __name__=="__main__":unittest.main()
