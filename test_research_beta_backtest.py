"""Deterministic offline regression tests; synthetic data are not accuracy evidence."""
import unittest
from datetime import datetime, timedelta, timezone
from research_beta_backtest import eligible_rows, evaluate, metrics

JST = timezone(timedelta(hours=9))
def fixture(n=50):
    start = datetime(2026, 10, 22, 12, tzinfo=JST)
    result = []
    for i in range(n):
        deadline = start + timedelta(days=i//12, minutes=i%12*20)
        result.append({
            "race_code": f"{deadline:%Y%m%d}{1+i%24:02d}{1+i%12:02d}",
            "independent_receipt_verified": True, "result_verified": True,
            "input_sha256": "a"*64, "first_git_blob_sha":"b"*40,
            "receipt_sha256":"c"*64,
            "source_received_at": (deadline-timedelta(minutes=40)).isoformat(),
            "generated_at": (deadline-timedelta(minutes=30)).isoformat(),
            "first_seen_at": (deadline-timedelta(minutes=20)).isoformat(),
            "deadline": deadline.isoformat(),
            "national_win_rates": [5.5, 4.8, 5.3, 4.9, 5.1, 4.6],
            "result": "1-2-3"
        })
    return result

class TestBacktest(unittest.TestCase):
    def test_never_claims_real_accuracy(self):
        report = evaluate(fixture(50))
        self.assertEqual(report["status"], "DESCRIPTIVE_ONLY")
        self.assertEqual(report["eligible"], 50)
        self.assertEqual(report["train_n"]+report["holdout_n"],50)
        self.assertIsNotNone(report["top3_delta"])
    def test_rejects_late_snapshot(self):
        rows=fixture(1)
        rows[0]["first_seen_at"]=rows[0]["deadline"]
        accepted, excluded=eligible_rows(rows)
        self.assertFalse(accepted)
        self.assertEqual(excluded["cutoff_violation"],1)
    def test_rejects_missing_receipt(self):
        rows=fixture(1)
        rows[0]["independent_receipt_verified"]=False
        accepted, excluded=eligible_rows(rows)
        self.assertFalse(accepted)
        self.assertEqual(excluded["unverified_receipt_or_result"],1)
    def test_rejects_duplicate(self):
        rows=fixture(1)
        accepted, excluded=eligible_rows(rows+rows)
        self.assertEqual(len(accepted),1)
        self.assertEqual(excluded["duplicate_or_invalid_race"],1)
    def test_normalized_model_and_hits(self):
        accepted,_=eligible_rows(fixture(1))
        score=metrics(accepted,0.4)
        self.assertEqual(score["n"],1)
        self.assertGreater(score["mean_log_loss"],0)
if __name__=="__main__":
    unittest.main()
