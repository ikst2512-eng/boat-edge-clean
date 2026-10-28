import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from urllib.error import HTTPError
from unittest.mock import patch
import collect_clean_results as c


class ResultCollectorTests(unittest.TestCase):
    def test_source_validated(self):
        header="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
        row="202610270101,2026-10-27T16:00:00+09:00,1,2,3\n"
        records=c.build_records("20261027",(header+row).encode(),datetime.fromisoformat("2026-10-27T17:00:00+09:00"))
        self.assertEqual(records["202610270101"]["finish_order"],[1,2,3])
        self.assertIn("boatracecsv.github.io",records["202610270101"]["source_url"])
    def test_current_day_404_waits_but_historical_404_fails(self):
        class Clock:
            @staticmethod
            def now(tz):
                return datetime.fromisoformat("2026-10-28T12:08:00+09:00")
            @staticmethod
            def strptime(*args):
                return datetime.strptime(*args)
        def not_found(*args, **kwargs):
            raise HTTPError("https://example.invalid", 404, "Not Found", {}, None)
        with patch.object(c, "datetime", Clock), patch.object(c, "urlopen", side_effect=not_found):
            self.assertEqual(c.collect()["status"], "waiting_for_published_source")
            self.assertEqual(c.collect("20261027")["status"], "waiting_for_published_source")
    def test_collection_status_shows_upstream_404_and_progress(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            report={"days":[
                {"day":"20261027","status":"waiting_for_published_source","source_races":0,"saved":0,"http_status":404},
                {"day":"20261028","source_races":7,"saved":7}
            ]}
            data=c.publish_collection_status(report,root=Path(folder))
            self.assertEqual(data["days"][0]["http_status"],404)
            self.assertEqual(data["days"][1]["newly_saved"],7)
            record=json.loads((Path(folder)/"confirmed_results"/"collection_status.json").read_text())
            self.assertEqual(record,data)
    def test_audit_lists_overdue_without_mislabeling_future_races(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            forecasts=root/"four_mode_forecasts"
            results=root/"confirmed_results"
            forecasts.mkdir()
            results.mkdir()
            for code,deadline in [
                ("202610280101","2026-10-28T14:00:00+09:00"),
                ("202610280102","2026-10-28T16:00:00+09:00"),
                ("202610280103","2026-10-28T20:00:00+09:00")]:
                (forecasts/(code+".json")).write_text(json.dumps({"race_code":code,"deadline_jst":deadline}),encoding="utf-8")
            (results/"202610280102.json").write_text('{"status":"confirmed"}',encoding="utf-8")
            now=datetime.fromisoformat("2026-10-28T18:00:00+09:00")
            self.assertEqual(c.audit_missing_results(root,now),["202610280101"])
            report={"days":[{"day":"20261027","source_races":10,"saved":0},{"day":"20261028","source_races":5,"saved":0}]}
            output=c.publish_collection_status(report,root,now)
            self.assertEqual(output["overdue_result_count"],1)
            self.assertEqual(output["overdue_race_codes"],["202610280101"])
            self.assertEqual(output["checked_at_jst"],now.isoformat())

    def test_missing_source_rows_are_not_declared_losses(self):
        header="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\\n"
        csv=(header+"202610280101,2026-10-28T12:00:00+09:00,1,2,3\\n"
            +"202610280102,2026-10-28T12:00:00+09:00,,,\\n").replace("\\n","\n")
        reasons=c.source_gap_reasons("20261028",csv.encode(),[
            "202610280101","202610280102","202610280103"])
        self.assertEqual(reasons["202610280101"],"row_present_requires_review")
        self.assertEqual(reasons["202610280102"],"invalid_or_unfinished_finish")
        self.assertEqual(reasons["202610280103"],"not_in_published_csv")
    def test_duplicate_source_rows_cannot_be_considered_confirmed(self):
        header="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
        row="202610280101,2026-10-28T12:00:00+09:00,1,2,3\n"
        self.assertEqual(c.source_gap_reasons("20261028",(header+row+row).encode(),["202610280101"])["202610280101"],"duplicate_source_rows")

    def test_retries_yesterday_and_today(self):
        calls=[]
        now=datetime.fromisoformat("2026-10-28T08:00:00+09:00")
        def fake_collect(day):
            calls.append(day)
            return {"day":day,"status":"waiting_for_published_source","saved":0}
        state=c.collect_recent(now=now,collector=fake_collect)
        self.assertEqual(calls,["20261027","20261028"])
        self.assertEqual(len(state["days"]),2)
    def test_rejects_duplicate_codes(self):
        header="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
        row="202610270101,2026-10-27T16:00:00+09:00,1,2,3\n"
        with self.assertRaises(ValueError):
            c.build_records("20261027",(header+row+row).encode(),datetime.fromisoformat("2026-10-27T17:00:00+09:00"))
    def test_no_invalid_finishes(self):
        raw="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n202610270101,2026-10-27T16:00:00+09:00,1,1,3\n"
        self.assertFalse(c.build_records("20261027",raw.encode(),datetime.fromisoformat("2026-10-27T17:00:00+09:00")))


if __name__=="__main__":
    unittest.main()
