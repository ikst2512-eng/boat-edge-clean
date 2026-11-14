import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from urllib.error import HTTPError
from unittest.mock import patch
import collect_clean_results as c


class ResultCollectorTests(unittest.TestCase):
    @staticmethod
    def valid_confirmation(code):
        return {
            "race_code":code, "status":"confirmed", "finish_order":[1,2,3],
            "source_url":c.BASE+code[:4]+"/"+code[4:6]+"/"+code[6:8]+".csv",
            "source_sha256":"a"*64,
            "confirmed_at_jst":"2026-11-03T12:01:00+09:00",
            "collected_at_jst":"2026-11-03T12:02:00+09:00",
        }

    def test_result_writer_uses_current_main_without_losing_pr_test_head(self):
        workflow = (Path(__file__).resolve().parent /
                    ".github/workflows/collect-clean-results.yml").read_text()
        self.assertIn("ref: ${{ github.event_name == 'pull_request' && github.sha || 'main' }}", workflow)
        self.assertIn("github.event_name == 'pull_request' ||", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("git add -- confirmed_results/", workflow)
        self.assertIn("git -c rebase.autoStash=true rebase origin/main", workflow)

    def test_workflow_run_fallback_never_trusts_pr_or_foreign_repo(self):
        workflow = (Path(__file__).resolve().parent /
                    ".github/workflows/collect-clean-results.yml").read_text()
        self.assertIn("workflow_run:", workflow)
        self.assertIn("Four-mode prospective capture (research only)", workflow)
        self.assertIn("CLEAN prospective pre-cutoff capture", workflow)
        self.assertEqual(workflow.count("  workflow_run:"),1)
        self.assertEqual(workflow.count("    types: [completed]"),1)
        self.assertIn("types: [completed]", workflow)
        self.assertIn("contains(fromJSON('[\"schedule\", \"workflow_dispatch\"]'), github.event.workflow_run.event)", workflow)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", workflow)
        self.assertIn(
            "github.event.workflow_run.head_repository.full_name == github.repository",
            workflow)
        self.assertIn("group: clean-main-data-writers", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("git add -- confirmed_results/", workflow)

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
            (results/"202610280102.json").write_text(json.dumps(self.valid_confirmation("202610280102")),encoding="utf-8")
            now=datetime.fromisoformat("2026-10-28T18:00:00+09:00")
            self.assertEqual(c.audit_missing_results(root,now),["202610280101"])
            report={"days":[{"day":"20261027","source_races":10,"saved":0},{"day":"20261028","source_races":5,"saved":0}]}
            output=c.publish_collection_status(report,root,now)
            self.assertEqual(output["overdue_result_count"],1)
            self.assertEqual(output["overdue_race_codes"],["202610280101"])
            self.assertEqual(output["checked_at_jst"],now.isoformat())

    def test_invalid_existing_confirmation_stays_overdue_without_overwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            forecasts=root/"four_mode_forecasts"
            confirmed=root/"confirmed_results"
            forecasts.mkdir()
            confirmed.mkdir()
            code="202611030101"
            (forecasts/(code+".json")).write_text(json.dumps({
                "race_code":code,"deadline_jst":"2026-11-03T11:00:00+09:00"}))
            target=confirmed/(code+".json")
            now=datetime.fromisoformat("2026-11-03T12:00:00+09:00")
            valid=self.valid_confirmation(code)
            for payload in (
                "{}",
                "not-json",
                json.dumps(dict(valid,finish_order=[1,1,2])),
                json.dumps(dict(valid,race_code="202611030102")),
                json.dumps(dict(valid,source_sha256="bad")),
                json.dumps(dict(valid,confirmed_at_jst="2026-11-03T12:01:00")),
            ):
                with self.subTest(payload=payload):
                    target.write_text(payload,encoding="utf-8")
                    self.assertFalse(c.confirmed_record_is_usable(target,code))
                    self.assertEqual(c.audit_missing_results(root,now),[code])
                    self.assertEqual(target.read_text(encoding="utf-8"),payload)
            target.write_text(json.dumps(valid),encoding="utf-8")
            self.assertTrue(c.confirmed_record_is_usable(target,code))
            self.assertEqual(c.audit_missing_results(root,now),[])

    def test_persisted_source_timestamp_must_not_exceed_collection_grace(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            code="202611030101"
            path=root/(code+".json")
            valid=self.valid_confirmation(code)
            cases=[
                ("2026-11-03T12:05:00+09:00","2026-11-03T12:02:00+09:00",True),
                ("2026-11-03T03:05:00+00:00","2026-11-03T12:02:00+09:00",True),
                ("2026-11-03T12:05:01+09:00","2026-11-03T12:02:00+09:00",False),
                ("2026-11-03T03:05:01+00:00","2026-11-03T12:02:00+09:00",False),
            ]
            for source_time,collected_time,expected in cases:
                with self.subTest(source_time=source_time):
                    payload=dict(valid,confirmed_at_jst=source_time,
                                 collected_at_jst=collected_time)
                    path.write_text(json.dumps(payload),encoding="utf-8")
                    self.assertEqual(c.confirmed_record_is_usable(path,code),expected)

    def test_collector_rejects_corrupt_preexisting_result_without_overwrite(self):
        class Response:
            status=200
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,*args): return (
                "レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
                "202610270101,2026-10-27T16:00:00+09:00,1,2,3\n").encode()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            confirmed=root/"confirmed_results"
            confirmed.mkdir()
            code="202610270101"
            target=confirmed/(code+".json")
            valid=self.valid_confirmation(code)
            invalids=[
                "{}",
                json.dumps(dict(valid,source_sha256="broken")),
                json.dumps(dict(valid,finish_order=[1,1,3])),
                json.dumps(dict(valid,confirmed_at_jst="2026-11-03T12:06:00+09:00")),
            ]
            with patch.object(c,"ROOT",root), patch.object(c,"urlopen",return_value=Response()):
                for data in invalids:
                    with self.subTest(data=data):
                        target.write_text(data,encoding="utf-8")
                        with self.assertRaisesRegex(ValueError,"existing archive invalid"):
                            c.collect("20261027")
                        self.assertEqual(target.read_text(encoding="utf-8"),data)
                target.write_text(json.dumps(valid),encoding="utf-8")
                self.assertEqual(c.collect("20261027")["saved"],0)

    def test_saved_result_provenance_must_match_exact_day_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            code="202611030101"
            target=root/(code+".json")
            good=self.valid_confirmation(code)
            target.write_text(json.dumps(good),encoding="utf-8")
            self.assertTrue(c.confirmed_record_is_usable(target,code))
            for wrong in (
                "https://example.com/results.csv",
                c.BASE+"2026/11/02.csv",
                c.BASE+"2026/11/03.csv?cached=1",
                "https://boatracecsv.github.io.evil.test/data/results/realtime/2026/11/03.csv",
            ):
                with self.subTest(wrong=wrong):
                    target.write_text(json.dumps(dict(good,source_url=wrong)),encoding="utf-8")
                    self.assertFalse(c.confirmed_record_is_usable(target,code))

    def test_missing_source_rows_are_not_declared_losses(self):
        header="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\\n"
        csv=(header+"202610280101,2026-10-28T12:00:00+09:00,1,2,3\\n"
            +"202610280102,2026-10-28T12:00:00+09:00,,,\\n").replace("\\n","\n")
        reasons=c.source_gap_reasons("20261028",csv.encode(),[
            "202610280101","202610280102","202610280103"])
        self.assertEqual(reasons["202610280101"],"row_present_requires_review")
        self.assertEqual(reasons["202610280102"],"invalid_or_unfinished_finish")
        self.assertEqual(reasons["202610280103"],"not_in_published_csv")
    def test_overdue_gap_diagnosis_matches_collector_timestamp_rejections(self):
        header="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
        entries=[
            ("202610280101","not-a-time","invalid_source_timestamp"),
            ("202610280102","2026-10-28T12:00:00","invalid_source_timestamp"),
            ("202610280103","2026-10-28T13:10:00+09:00","future_source_timestamp"),
            ("202610280104","2026-10-28T12:00:00+09:00","row_present_requires_review"),
            ("202610280105","","missing_source_timestamp"),
        ]
        data=header+"".join(f"{code},{stamp},1,2,3\n" for code,stamp,_ in entries)
        now=datetime.fromisoformat("2026-10-28T13:00:00+09:00")
        result=c.source_gap_reasons("20261028", data.encode(), [item[0] for item in entries],
                                    collected_at=now)
        self.assertEqual(result,{code:reason for code,_,reason in entries})
        records=c.build_records("20261028",data.encode(),now)
        self.assertNotIn("202610280101",records)
        self.assertNotIn("202610280102",records)
        self.assertNotIn("202610280103",records)
        self.assertIn("202610280104",records)

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
    def test_hourly_bounded_historical_retry_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            forecasts=root/"four_mode_forecasts"
            forecasts.mkdir()
            for day in ("20261028","20261029","20261030","20261031","20261101","20261102"):
                code=day+"0101"
                (forecasts/(code+".json")).write_text(
                    json.dumps({"race_code":code,"deadline_jst":day[:4]+"-"+day[4:6]+"-"+day[6:]+"T12:00:00+09:00"}))
            now=datetime.fromisoformat("2026-11-03T04:03:00+09:00")
            called=[]
            result=c.collect_overdue_historical(root,now,lambda d: called.append(d) or {"day":d,"saved":0})
            self.assertEqual(called,["20261028","20261029","20261030"])
            self.assertEqual(len(result["days"]),3)
            called.clear()
            ignored=c.collect_overdue_historical(root,now.replace(minute=13),lambda d: called.append(d))
            self.assertEqual(ignored["status"],"not_hourly_window")
            self.assertFalse(called)

    def test_historical_retry_ignores_saved_or_future_and_limits_age(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            forecasts=root/"four_mode_forecasts"
            confirmed=root/"confirmed_results"
            forecasts.mkdir()
            confirmed.mkdir()
            for day in ("20260901","20261101","20261102","20261104"):
                code=day+"0101"
                (forecasts/(code+".json")).write_text(json.dumps({
                    "race_code":code,"deadline_jst":day[:4]+"-"+day[4:6]+"-"+day[6:]+"T12:00:00+09:00"}))
            (confirmed/"202611010101.json").write_text(json.dumps(self.valid_confirmation("202611010101")))
            called=[]
            r=c.collect_overdue_historical(root,datetime.fromisoformat("2026-11-03T05:01:00+09:00"),
                lambda d: called.append(d))
            self.assertEqual(called,[])
            self.assertEqual(r["days"],[])

    def test_rejects_duplicate_codes(self):
        header="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
        row="202610270101,2026-10-27T16:00:00+09:00,1,2,3\n"
        with self.assertRaises(ValueError):
            c.build_records("20261027",(header+row+row).encode(),datetime.fromisoformat("2026-10-27T17:00:00+09:00"))
    def test_rejects_duplicate_after_invalid_finish_or_timestamp(self):
        header="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n"
        valid="202610270101,2026-10-27T16:00:00+09:00,1,2,3\n"
        invalid_rows=[
            "202610270101,2026-10-27T16:00:00+09:00,1,1,3\n",
            "202610270101,not-a-time,1,2,3\n",
            "202610270101,,1,2,3\n",
            "202610270101,2026-10-27T19:00:00+09:00,1,2,3\n",
        ]
        now=datetime.fromisoformat("2026-10-27T17:00:00+09:00")
        for invalid in invalid_rows:
            with self.subTest(invalid=invalid):
                raw=(header+invalid+valid).encode()
                self.assertEqual(
                    c.source_gap_reasons("20261027",raw,["202610270101"])["202610270101"],
                    "duplicate_source_rows")
                with self.assertRaisesRegex(ValueError,"duplicate source result"):
                    c.build_records("20261027",raw,now)

    def test_no_invalid_finishes(self):
        raw="レースコード,取得日時,1着_艇番,2着_艇番,3着_艇番\n202610270101,2026-10-27T16:00:00+09:00,1,1,3\n"
        self.assertFalse(c.build_records("20261027",raw.encode(),datetime.fromisoformat("2026-10-27T17:00:00+09:00")))


if __name__=="__main__":
    unittest.main()
