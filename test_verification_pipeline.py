import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from verification_pipeline import evaluate, run


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.race = "202610280101"
        self.tickets = ["1-2-3", "1-3-2", "2-1-3", "3-1-2", "1-2-4", "1-4-2",
                        "2-3-1", "2-1-4", "3-2-1", "4-1-2", "4-2-1", "5-1-2",
                        "5-2-1", "6-1-2", "6-2-1"]

    def write(self, directory, obj):
        p = self.root / directory / (self.race + ".json")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj), encoding="utf-8")

    def forecast(self):
        tz = timezone(timedelta(hours=9))
        t = datetime(2026, 10, 28, 13, 0, tzinfo=tz)
        return {"race_code": self.race, "model": "V236_coverage15",
                "tickets": self.tickets, "saved_at_jst": (t-timedelta(minutes=3)).isoformat(),
                "deadline_jst": t.isoformat(), "predeadline_proof": "verified"}

    def result(self, order=(1, 2, 3)):
        return {"race_code": self.race, "status": "confirmed",
                "finish_order": list(order), "source_url": "https://example.org/official.csv",
                "confirmed_at_jst": "2026-10-28T14:00:00+09:00"}

    def test_missing_forecast_never_counted(self):
        self.write("confirmed_results", self.result())
        record = evaluate(self.race, self.root)
        self.assertEqual(record["state"], "waiting_prediction")

    def test_prediction_result_payout_stage_progress(self):
        self.write("v236_forecasts", self.forecast())
        self.assertEqual(evaluate(self.race, self.root)["state"], "waiting_result")
        self.write("confirmed_results", self.result())
        self.assertEqual(evaluate(self.race, self.root, payout_loader=lambda *args: (_ for _ in ()).throw(OSError()))["state"], "waiting_payout")
        scored = evaluate(self.race, self.root, payout_loader=lambda *_: 1230)
        self.assertEqual(scored["state"], "complete")
        self.assertTrue(scored["hit"])
        self.assertEqual(scored["return_yen"], 4920)
        self.assertEqual(scored["profit_yen"], -80)
        self.assertEqual(scored["roi_pct"], 98.4)

    def test_missing_candidate(self):
        self.write("v236_forecasts", self.forecast())
        self.write("confirmed_results", self.result((6, 5, 4)))
        scored = evaluate(self.race, self.root, payout_loader=lambda *_: 1000)
        self.assertEqual(scored["miss_reason"], "second_missing")
        self.assertEqual(scored["profit_yen"], -5000)

    def test_frozen_after_deadline_rejected(self):
        record = self.forecast()
        record["saved_at_jst"] = "2026-10-28T14:00:00+09:00"
        self.write("v236_forecasts", record)
        self.write("confirmed_results", self.result())
        self.assertEqual(evaluate(self.race, self.root)["state"], "invalid_record")

    def test_state_persists_and_no_fabricated_roi(self):
        self.write("confirmed_results", self.result())
        summary = run(self.root)
        self.assertEqual(summary["eligible_complete_races"], 0)
        self.assertIsNone(summary["roi_pct"])
        self.assertTrue((self.root / "verification_status" / (self.race + ".json")).exists())


if __name__ == "__main__":
    unittest.main()
