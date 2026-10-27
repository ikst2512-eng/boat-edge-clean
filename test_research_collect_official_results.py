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
    def test_bounded_offline_mock_does_not_modify_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder,"202610270102.json")
            path.write_text('{"original":true}',encoding="utf-8")
            with patch("research_collect_official_results.urlopen",return_value=FakeResponse()) as urlopen:
                result=collect(folder,max_races=1)
            self.assertEqual(result["fetched"],1)
            self.assertEqual(result["results"][0]["ticket"],"1-2-4")
            self.assertEqual(result["results"][0]["verification_status"],"UNVERIFIED_SOURCE_RECEIPT")
            self.assertEqual(json.loads(path.read_text()),{"original":True})
            self.assertEqual(urlopen.call_count,1)
    def test_rejects_unbounded_collection(self):
        with self.assertRaises(ValueError):collect(".",max_races=145)
    def test_no_forecast_mutation_on_failed_fetch(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder,"202610270102.json")
            path.write_text("{}",encoding="utf-8")
            with patch("research_collect_official_results.urlopen",side_effect=TimeoutError()):
                result=collect(folder,max_races=1)
            self.assertEqual(result["fetched"],0)
            self.assertEqual(result["failed"],1)
            self.assertEqual(path.read_text(),"{}")
if __name__=="__main__":unittest.main()
