import unittest
from urllib.error import HTTPError
from datetime import datetime
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import clean_schedule as s


class ScheduleTests(unittest.TestCase):
    def test_parses_valid_schedule(self):
        row={"レースコード":"202610270101","電話投票締切予定":"15:22"}
        o=s.parse_schedule("20261027",[row],datetime.now(s.JST))
        self.assertEqual(o["races"][0]["deadline_jst"][:16],"2026-10-27T15:22")
        self.assertFalse(o["results_confirmed"])

    def test_duplicate_rejected(self):
        row={"レースコード":"202610270101","電話投票締切予定":"1522"}
        with self.assertRaises(ValueError):
            s.parse_schedule("20261027",[row,row],datetime.now(s.JST))

    def test_invalid_date_without_network(self):
        self.assertEqual(s.clean_schedule("20261340")[0],400)

    def test_not_yet_published_csv_is_not_a_server_failure(self):
        error=HTTPError("https://example.invalid/file.csv",404,"Not Found",None,None)
        with patch.object(s,"read_rows",side_effect=error), patch("clean_openapi_sources.load",side_effect=ValueError("unavailable")), patch.object(s,"schedule_from_frozen_candidates",return_value=None):
            status,data=s.clean_schedule("20261029")
        self.assertEqual(status,404)
        self.assertEqual(data["status"],"schedule_not_published")
        self.assertNotIn("races",data)

    def test_unpublished_csv_uses_verified_alternate_schedule(self):
        error=HTTPError("https://example.invalid/file.csv",404,"Not Found",None,None)
        titles=[{"レースコード":"202610300101","電話投票締切予定":"15:22"}]
        with patch.object(s,"read_rows",side_effect=error), patch("clean_openapi_sources.load",return_value=(titles,[],datetime.now(s.JST),"digest",{"source":"nonofficial_openapi_v1"})):
            status,data=s.clean_schedule("20261030")
        self.assertEqual(status,200)
        self.assertEqual(data["status"],"alternate_published_schedule")
        self.assertEqual(data["source"],"nonofficial_openapi_v1")
        self.assertEqual(data["races"][0]["race_code"],"202610300101")

    def test_archived_schedule_fallback_has_real_races_only(self):
        import tempfile, json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            record={"race_code":"202610300101","status":"prospective_candidate",
                    "formal":False,"scoring":False,"validated":False,
                    "source_deadline_jst":"2026-10-30T15:21:00+09:00",
                    "cutoff_jst":"2026-10-30T15:09:00+09:00",
                    "generated_at":"2026-10-30T10:44:00+09:00"}
            (root/"202610300101.json").write_text(json.dumps(record))
            result=s.schedule_from_frozen_candidates("20261030",root)
            self.assertEqual(len(result["races"]),1)
            self.assertTrue(result["partial_coverage"])
            self.assertEqual(result["races"][0]["race_code"],"202610300101")
            record["generated_at"]="2026-10-30T16:00:00+09:00"
            (root/"202610300101.json").write_text(json.dumps(record))
            self.assertIsNone(s.schedule_from_frozen_candidates("20261030",root))

    def test_schedule_uses_frozen_candidates_if_sources_absent(self):
        error=HTTPError("https://example.invalid/file.csv",404,"Not Found",None,None)
        payload={"ok":True,"date":"20261030","races":[{"race_code":"202610300101"}]}
        with patch.object(s,"read_rows",side_effect=error), patch("clean_openapi_sources.load",side_effect=ValueError("unavailable")), patch.object(s,"schedule_from_frozen_candidates",return_value=payload):
            status,data=s.clean_schedule("20261030")
        self.assertEqual(status,200)
        self.assertEqual(data["races"][0]["race_code"],"202610300101")

    def test_upstream_503_remains_source_failure(self):
        error=HTTPError("https://example.invalid/file.csv",503,"unavailable",None,None)
        with patch.object(s,"read_rows",side_effect=error):
            status,data=s.clean_schedule("20261029")
        self.assertEqual((status,data["status"]),(503,"source_unavailable"))

    def test_upstream_missing_daily_file_is_not_empty_schedule(self):
        with patch.object(s,"read_rows",side_effect=HTTPError("https://upstream.invalid",404,"not found",{},None)), patch("clean_openapi_sources.load",side_effect=ValueError("no alternate schedule")), patch.object(s,"schedule_from_frozen_candidates",return_value=None):
            status,data=s.clean_schedule("20261029")
        self.assertEqual(status,404)
        self.assertEqual(data["status"],"schedule_not_published")
        self.assertEqual(data["upstream_http_status"],404)
        self.assertTrue(data["retryable"])
        self.assertEqual(data["date"],"20261029")

    def test_upstream_timeout_is_retryable_503(self):
        with patch.object(s, "read_rows", side_effect=URLError("timed out")):
            status, data = s.clean_schedule("20261029")
        self.assertEqual((status, data["status"]), (503, "source_unavailable"))
        self.assertTrue(data["retryable"])

    def test_malformed_csv_is_502_not_upstream_outage(self):
        with patch.object(s, "read_rows", return_value=([{"レースコード": "202610290101", "電話投票締切予定": ""}], datetime.now(s.JST), "abc")):
            status, data = s.clean_schedule("20261029")
        self.assertEqual((status, data["status"]), (502, "source_invalid"))
        self.assertFalse(data["retryable"])

    def test_source_decode_error_is_502(self):
        with patch.object(s, "read_rows", side_effect=UnicodeDecodeError("utf-8", b"\\xff", 0, 1, "bad byte")):
            status, data = s.clean_schedule("20261029")
        self.assertEqual((status, data["status"]), (502, "source_invalid"))

    def test_unexpected_bug_is_internal_500(self):
        with patch.object(s, "read_rows", side_effect=RuntimeError("unexpected")):
            status, data = s.clean_schedule("20261029")
        self.assertEqual((status, data["status"]), (500, "internal_error"))
        self.assertFalse(data["retryable"])

    def test_upstream_failure_no_old_fallback(self):
        with patch.object(s,"read_rows",side_effect=TimeoutError()):
            status,data=s.clean_schedule("20261027")
        self.assertEqual((status,data["status"]),(503,"source_unavailable"))


if __name__=="__main__":
    unittest.main()
