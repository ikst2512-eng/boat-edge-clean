import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.verify_four_mode_new_receipts import verify

JST = timezone(timedelta(hours=9))

class FourModeReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = Path.cwd()
        import os
        os.chdir(self.temp.name)
        Path("four_mode_forecasts").mkdir()
        self.path = Path("four_mode_forecasts/202611020101.json")
        self.now = datetime(2026,11,2,7,0,tzinfo=JST)
        self.deadline = self.now + timedelta(minutes=60)
        self.record = {
            "schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1",
            "race_code":self.path.stem,
            "generated_at_jst":self.now.isoformat(),
            "deadline_jst":self.deadline.isoformat(),
            "validated":False,"target_rates_not_proven":True,
            "modes":{key:{"tickets":[{"combo":"1-2-3","p":2.0}]} for key in ("hit","balance","hole","narrow")}
        }
    def tearDown(self):
        import os
        os.chdir(self.previous)
        self.temp.cleanup()
    def write(self):
        self.path.write_text(json.dumps(self.record), encoding="utf-8")
    def test_valid_immutable_candidate(self):
        self.write()
        self.assertEqual(verify([str(self.path)], now=self.now+timedelta(minutes=1)),1)
    def test_refuses_after_cutoff(self):
        self.write()
        with self.assertRaisesRegex(ValueError,"receipt"):
            verify([str(self.path)],now=self.deadline-timedelta(seconds=60))
    def test_refuses_post_deadline_generation(self):
        self.record["generated_at_jst"]=(self.deadline-timedelta(minutes=3)).isoformat()
        self.write()
        with self.assertRaises(ValueError):
            verify([str(self.path)],now=self.now)
    def test_refuses_missing_mode(self):
        self.record["modes"].pop("hole")
        self.write()
        with self.assertRaisesRegex(ValueError,"missing_four_modes"):
            verify([str(self.path)],now=self.now)
    def test_refuses_invalid_ticket(self):
        self.record["modes"]["hit"]["tickets"]=[{"combo":"1-1-2","p":2.0}]
        self.write()
        with self.assertRaises(ValueError):
            verify([str(self.path)],now=self.now)

if __name__=="__main__":
    unittest.main()
