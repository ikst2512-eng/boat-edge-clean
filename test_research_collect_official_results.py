import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research_collect_official_results import collect

class FakeResponse:
    status=200
    headers={"Content-Type":"text/html; charset=utf-8"}
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,limit): return b"<html><body>" + "3連単 1-2-4 ¥1,240".encode("utf-8") + b"</body></html>"

class CollectorTests(unittest.TestCase):
    @staticmethod
    def complete_record():
        return {"race_code":"202610270102", "status":"research", "validated":False,
                "predictions":["1-2-4"], "generated_at":"2026-10-27T10:00:00+09:00",
                "cutoff_jst":"2026-10-27T15:41:00+09:00",
                "source_deadline_jst":"2026-10-27T15:53:00+09:00",
                "model_git_sha":"a"*40, "input_sha256":"b"*64,
                "source_title_sha256":"c"*64, "source_cards_sha256":"d"*64}

    def test_bounded_offline_mock_does_not_modify_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder,"202610270102.json")
            path.write_text(json.dumps(self.complete_record()),encoding="utf-8")
            with patch("research_collect_official_results.urlopen",return_value=FakeResponse()) as urlopen:
                result=collect(folder,max_races=1)
            self.assertEqual(result["fetched"],1)
            self.assertEqual(result["results"][0]["ticket"],"1-2-4")
            self.assertEqual(result["results"][0]["verification_status"],"UNVERIFIED_SOURCE_RECEIPT")
            self.assertEqual(json.loads(path.read_text()),self.complete_record())
            self.assertEqual(urlopen.call_count,1)
    def test_transient_timeout_recovers_without_modifying_forecast(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder,"202610270102.json")
            path.write_text(json.dumps(self.complete_record()),encoding="utf-8")
            with patch("research_collect_official_results.urlopen",side_effect=[TimeoutError(),FakeResponse()]) as fetch:
                report=collect(folder,max_races=1,retries=1,sleep_fn=lambda _:None)
            self.assertEqual(report["fetched"],1)
            self.assertEqual(report["failed"],0)
            self.assertEqual(fetch.call_count,2)
            self.assertEqual(json.loads(path.read_text()),self.complete_record())

    def test_rejects_unbounded_collection(self):
        with self.assertRaises(ValueError):collect(".",max_races=145)
    def test_no_forecast_mutation_on_failed_fetch(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder,"202610270102.json")
            path.write_text(json.dumps(self.complete_record()),encoding="utf-8")
            with patch("research_collect_official_results.urlopen",side_effect=TimeoutError()) as fetch:
                result=collect(folder,max_races=1,retries=2,sleep_fn=lambda _:None)
            self.assertEqual(fetch.call_count,3)
            self.assertEqual(result["fetched"],0)
            self.assertEqual(result["failed"],1)
            self.assertEqual(json.loads(path.read_text()),self.complete_record())
if __name__=="__main__":unittest.main()
