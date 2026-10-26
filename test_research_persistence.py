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
    def test_saved_non_object_json_is_rejected_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "209901011201.json").write_text(
                '["not", "a", "snapshot"]', encoding="utf-8"
            )
            with patch.object(m, "STORE", Path(directory)):
                with self.assertRaisesRegex(ValueError, "invalid saved forecast structure"):
                    m._saved("209901011201")

    def test_saved_unhashable_tickets_fail_with_value_error(self):
        with tempfile.TemporaryDirectory() as d:
            record = {"race_code": "209901011201", "status": "research",
                      "validated": False, "predictions": [{"bad": "ticket"}] * 10}
            (Path(d) / "209901011201.json").write_text(json.dumps(record), encoding="utf-8")
            with patch.object(m, "STORE", Path(d)):
                with self.assertRaisesRegex(ValueError, "invalid prediction list"):
                    m._saved("209901011201")

    def test_cutoff_crossed_during_provenance_check_is_not_persisted(self):
        code = "209901011201"
        title = [{"レースコード": code, "電話投票締切予定": "12:30"}]
        cards = {"レースコード": code}
        cards.update({f"艇{i}_全国勝率": "5.0" for i in range(1, 7)})
        early = datetime(2099, 1, 1, 12, 17, tzinfo=m.JST)
        late = datetime(2099, 1, 1, 12, 19, tzinfo=m.JST)

        class AdvancingClock(datetime):
            calls = 0
            @classmethod
            def now(cls, tz=None):
                cls.calls += 1
                return early if cls.calls == 1 else late

        provenance = {"model_git_sha": "a" * 40,
                      "model_source_sha256": "b" * 64}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(m, "STORE", Path(directory)), \
                 patch.object(m, "read_rows", side_effect=[
                     (title, early, "c" * 64), ([cards], early, "d" * 64)]), \
                 patch.object(m, "model_provenance", return_value=provenance), \
                 patch.object(m, "datetime", AdvancingClock):
                with self.assertRaisesRegex(ValueError, "missed 12-minute cutoff"):
                    m.predict("20990101", 12, 1)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_missing_source_never_saved(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(m,"STORE",Path(d)),patch.object(m,"read_rows",side_effect=ValueError("source not ready")):
                with self.assertRaises(ValueError):m.predict("20990101","12","1")
                self.assertEqual(list(Path(d).iterdir()),[])
if __name__=="__main__":unittest.main()
