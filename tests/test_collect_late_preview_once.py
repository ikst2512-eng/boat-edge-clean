import csv, io, tempfile, unittest
from datetime import datetime
from pathlib import Path
from research_model import JST
from collect_late_preview_once import collect

class Integration(unittest.TestCase):
    def test_fetch_to_append_only_evidence(self):
        def fetch(url):
            b=io.StringIO()
            w=csv.DictWriter(b,fieldnames=["レースコード","締切時刻","取得日時","艇1_コース"])
            w.writeheader()
            w.writerow({"レースコード":"202610310111","締切時刻":"19:00","取得日時":"2026-10-31T18:54:00+09:00","艇1_コース":"1"})
            return b.getvalue().encode()
        now=lambda:datetime(2026,10,31,18,55,tzinfo=JST)
        with tempfile.TemporaryDirectory() as folder:
            outcome=collect(day="20261031",root=folder,fetch=fetch,clock=now)
            self.assertEqual(outcome["kinds"]["stt"]["saved"],1)
            self.assertIn("paired_complete",outcome["paired_six_lane_coverage"])
            self.assertEqual(outcome["kinds"]["stt"]["pre_deadline_2min"]["pre_cutoff_observed"],1)
            self.assertEqual(outcome["kinds"]["stt"]["pre_deadline_12min"]["pre_cutoff_observed"],0)
            self.assertTrue((Path(folder)/"20261031"/"stt"/"202610310111.json").is_file())
            second=collect(day="20261031",root=folder,fetch=fetch,clock=now)
            self.assertEqual(second["kinds"]["stt"]["error"],"FileExistsError")
            self.assertEqual(second["kinds"]["stt"]["status"],"capture_invalid")
            self.assertEqual(second["capture_invalid"],5)
            self.assertEqual(second["sources_unavailable"],0)
            self.assertEqual(second["status"],"capture_invalid")
    def test_total_upstream_outage_is_explicit_not_success(self):
        from urllib.error import HTTPError
        def unavailable(url):
            raise HTTPError(url, 404, "Not Found", {}, None)
        with tempfile.TemporaryDirectory() as folder:
            result=collect(day="20261031",root=folder,fetch=unavailable,
                           clock=lambda:datetime(2026,10,31,18,55,tzinfo=JST))
            self.assertEqual(result["status"],"source_unavailable")
            self.assertEqual(result["sources_available"],0)
            self.assertEqual(result["sources_unavailable"],5)
            self.assertEqual(result["saved_total"],0)
            self.assertEqual(result["paired_six_lane_coverage"]["paired_complete"],0)
            self.assertTrue(all(v["http_status"]==404 for v in result["kinds"].values()))

    def test_before_publication_404_is_not_claimed_as_outage(self):
        from urllib.error import HTTPError
        def unavailable(url):
            raise HTTPError(url, 404, "Not Found", {}, None)
        with tempfile.TemporaryDirectory() as folder:
            result=collect(day="20261101",root=folder,fetch=unavailable,
                           clock=lambda:datetime(2026,11,1,4,32,tzinfo=JST))
            self.assertEqual(result["status"],"not_yet_expected")
            self.assertEqual(result["sources_available"],0)
            self.assertTrue(all(v["availability_interpretation"] ==
                                "before_expected_publication_window"
                                for v in result["kinds"].values()))

    def test_partial_source_failure_is_not_all_sources_retrieved(self):
        from urllib.error import HTTPError
        def mixed(url):
            if "/stt/" not in url:
                raise HTTPError(url, 404, "Not Found", {}, None)
            return b"\xef\xbb\xbf" + "レースコード\n".encode()
        with tempfile.TemporaryDirectory() as folder:
            result=collect(day="20261031",root=folder,fetch=mixed,
                           clock=lambda:datetime(2026,10,31,18,55,tzinfo=JST))
            self.assertEqual(result["status"],"partial_source_failure")
            self.assertEqual(result["sources_available"],1)
            self.assertEqual(result["sources_unavailable"],4)
            self.assertEqual(result["saved_total"],0)

    def test_all_sources_empty_is_not_claimed_as_race_data(self):
        def empty(url):
            return "レースコード\n".encode()
        with tempfile.TemporaryDirectory() as folder:
            result=collect(day="20261031",root=folder,fetch=empty,
                           clock=lambda:datetime(2026,10,31,18,55,tzinfo=JST))
            self.assertEqual(result["status"],"sources_retrieved_no_rows")
            self.assertEqual(result["sources_available"],5)
            self.assertEqual(result["race_rows_total"],0)
            self.assertEqual(result["saved_total"],0)

    def test_late_race_not_written(self):
        now=lambda:datetime(2026,10,31,18,59,tzinfo=JST)
        with tempfile.TemporaryDirectory() as folder:
            outcome=collect(day="20261031",root=folder,fetch=lambda u:b"\xef\xbb\xbf\xe3\x83\xac\xe3\x83\xbc\xe3\x82\xb9\xe3\x82\xb3\xe3\x83\xbc\xe3\x83\x89\n",clock=now)
            self.assertEqual(outcome["kinds"]["stt"]["saved"],0)
if __name__=="__main__":unittest.main()
