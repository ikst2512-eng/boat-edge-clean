"""Verify persisted research forecasts are reused and cutoff failures stop output."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import research_model as m
class PersistTests(unittest.TestCase):
    def test_saved_used_without_fetch(self):
        with tempfile.TemporaryDirectory() as d:
            rec={"race_code":"209901011201","ok":True,"status":"research","predictions":["-".join(map(str,t)) for t in m.TICKETS[:10]],
                 "validated":False,"model_version":"fixture","generated_at":"2099-01-01T00:00:00+09:00","message":"research"}
            path=Path(d)/"209901011201.json"
            path.write_text(json.dumps(rec),encoding="utf-8")
            with patch.object(m,"STORE",Path(d)),patch.object(m,"read_rows",side_effect=AssertionError("unexpected fetch")):
                self.assertEqual(m.predict("20990101","12","1")["predictions"],rec["predictions"])
    def test_tampered_saved_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"209901011201.json").write_text('{"race_code":"wrong","status":"research","validated":false}',encoding="utf-8")
            with patch.object(m,"STORE",Path(d)):
                with self.assertRaises(ValueError):m.predict("20990101","12","1")
    def test_saved_unhashable_tickets_fail_with_value_error(self):
        with tempfile.TemporaryDirectory() as d:
            record = {"race_code": "209901011201", "status": "research",
                      "validated": False, "predictions": [{"bad": "ticket"}] * 10}
            (Path(d) / "209901011201.json").write_text(json.dumps(record), encoding="utf-8")
            with patch.object(m, "STORE", Path(d)):
                with self.assertRaisesRegex(ValueError, "invalid prediction list"):
                    m._saved("209901011201")

    def test_missing_source_never_saved(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(m,"STORE",Path(d)),patch.object(m,"read_rows",side_effect=ValueError("source not ready")):
                with self.assertRaises(ValueError):m.predict("20990101","12","1")
                self.assertEqual(list(Path(d).iterdir()),[])
if __name__=="__main__":unittest.main()
