import csv
import io
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

from entry_course_collector import attempt_batch,expected_t2_without_baseline,t2_cli_failure
from test_entry_waku10_pilot import fixture
from test_entry_waku10_source import waku

JST=timezone(timedelta(hours=9))
NOW=datetime(2026,11,3,18,29,tzinfo=JST)

def write_csv(rows):
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8-sig")

def setup(root,count):
    cards={}
    rows=[]
    for index in range(count):
        baseline,card,evidence=fixture()
        code=f"2026110307{8+index:02d}"
        baseline["race_code"]=code
        card["race_key"]=f"20261103-07-{8+index:02d}"
        row=waku()
        row["レースコード"]=code
        rows.append(row)
        cards[code]=card
        folder=Path(root)/"research_snapshots"
        folder.mkdir(exist_ok=True)
        (folder/(code+".json")).write_text(json.dumps(baseline))
    return cards,write_csv(rows)

class BatchTests(unittest.TestCase):
    def test_three_same_window_races_all_archived_without_history_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,3)
            archive={}
            out=attempt_batch(tmp,now=lambda:NOW,
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:bytes_,
                prefetch=lambda day:self.fail("no 62-file fallback"),
                ledger_ops=(archive.get,lambda path,data:archive.setdefault(path,data)))
            self.assertEqual(out["status"],"t2_batch_completed")
            self.assertEqual(out["attempted_count"],3)
            self.assertEqual(out["stored_count"],3)
            self.assertEqual(out["newly_stored_count"],3)
            self.assertEqual(out["reused_count"],0)
            self.assertEqual(out["not_stored_count"],0)
            self.assertEqual(out["deferred_count"],0)
            self.assertEqual(len(archive),3)
            self.assertEqual(set(archive),{
                f"waku10/20261103/2026110307{i:02d}.json" for i in (8,9,10)})
            self.assertTrue(all(r["stored"] for r in out["results"]))
    def test_repeated_batch_does_not_count_reuse_as_new_saved_forecasts(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,2)
            archive={}
            ops=(archive.get,lambda key,payload:archive.setdefault(key,payload))
            original=attempt_batch(tmp,now=lambda:NOW,
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:bytes_,
                ledger_ops=ops)
            self.assertEqual(original["newly_stored_count"],2)
            later=attempt_batch(tmp,now=lambda:NOW,
                card_reader=lambda *args:self.fail("original must be reused"),
                waku_fetch=lambda url:self.fail("no re-fetch"),
                ledger_ops=(archive.get,lambda *args:self.fail("no overwrite")))
            self.assertEqual(later["stored_count"],2)
            self.assertEqual(later["newly_stored_count"],0)
            self.assertEqual(later["reused_count"],2)
            self.assertEqual(later["not_stored_count"],0)
    def test_all_eligible_races_without_preview_are_operational_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,2)
            def no_preview(day,venue,race):
                raise ValueError("preview_not_published")
            out=attempt_batch(tmp,now=lambda:NOW,
                card_reader=no_preview,
                waku_fetch=lambda url:self.fail("no preview means no Waku10"),
                prefetch=lambda day:self.fail("no historical requests"),
                ledger_ops=(lambda key:None,lambda key,value:self.fail("no archive")))
            self.assertEqual(out["status"],"t2_batch_no_capture")
            self.assertEqual(out["attempted_count"],2)
            self.assertEqual(out["stored_count"],0)
            self.assertEqual(out["not_stored_count"],2)
            self.assertEqual(out["errors"],0)
            self.assertTrue(all(r["status"]=="preview_not_ready" for r in out["results"]))
    def test_unpublished_preview_can_arrive_within_original_t2_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,2)
            clock=[NOW]
            reads={"count":0}
            def now():return clock[0]
            def sleep(seconds):clock[0]+=timedelta(seconds=seconds)
            def preview(day,venue,race):
                reads["count"]+=1
                if clock[0] < NOW+timedelta(seconds=35):
                    raise ValueError("preview_not_yet_published")
                return cards[day+venue+race]
            storage={}
            out=attempt_batch(tmp,now=now,preview_retry_rounds=3,
                preview_retry_interval=35,sleep=sleep,
                card_reader=preview,waku_fetch=lambda url:bytes_,
                ledger_ops=(storage.get,lambda p,b:storage.setdefault(p,b)))
            self.assertEqual(out["status"],"t2_batch_completed")
            self.assertEqual(out["newly_stored_count"],2)
            self.assertEqual(out["preview_retry_sleeps"],1)
            self.assertEqual(out["preview_retry_attempts"],2)
            self.assertGreaterEqual(reads["count"],4)
            self.assertEqual(len(storage),2)
    def test_retries_stop_before_cutoff_without_faking_late_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,1)
            clock=[NOW]
            def now():return clock[0]
            def sleep(seconds):clock[0]+=timedelta(seconds=seconds)
            out=attempt_batch(tmp,now=now,preview_retry_rounds=7,
                preview_retry_interval=35,sleep=sleep,
                card_reader=lambda *a:(_ for _ in ()).throw(ValueError("no_preview")),
                waku_fetch=lambda url:self.fail("no preview means no Waku10"),
                ledger_ops=(lambda p:None,lambda p,b:self.fail("late archive")))
            self.assertEqual(out["status"],"t2_batch_no_capture")
            self.assertEqual(out["newly_stored_count"],0)
            self.assertGreater(out["preview_retry_sleeps"],0)
            self.assertLess(clock[0],datetime(2026,11,3,18,31,tzinfo=JST))
    def test_retry_does_not_starve_second_race_on_first_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,2)
            clock=[NOW];seen=[]
            def now():return clock[0]
            def sleep(seconds):clock[0]+=timedelta(seconds=seconds)
            def preview(day,venue,race):
                seen.append(race)
                if race=="08":raise ValueError("no_preview")
                return cards[day+venue+race]
            storage={}
            out=attempt_batch(tmp,now=now,preview_retry_rounds=2,
                sleep=sleep,card_reader=preview,waku_fetch=lambda url:bytes_,
                ledger_ops=(storage.get,lambda p,b:storage.setdefault(p,b)))
            self.assertEqual(seen[:2],["08","09"])
            self.assertEqual(out["status"],"t2_batch_partial_capture")
            self.assertEqual(out["newly_stored_count"],1)
            self.assertEqual(out["not_stored_count"],1)
    def test_invalid_retry_configuration_fails_closed(self):
        for rounds,interval in ((8,35),(0,35),(2,0),(2,61)):
            with self.assertRaisesRegex(ValueError,"preview_retry_bounds"):
                attempt_batch(".",now=lambda:NOW,
                    preview_retry_rounds=rounds,
                    preview_retry_interval=interval)
    def test_partial_capture_exposes_unstored_races(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,2)
            store={}
            def sometimes_unavailable(day,venue,race):
                if race=="09":
                    raise ValueError("preview_unavailable")
                return cards[day+venue+race]
            out=attempt_batch(tmp,now=lambda:NOW,
                card_reader=sometimes_unavailable,waku_fetch=lambda url:bytes_,
                ledger_ops=(store.get,lambda path,data:store.setdefault(path,data)))
            self.assertEqual(out["status"],"t2_batch_partial_capture")
            self.assertEqual(out["newly_stored_count"],1)
            self.assertEqual(out["not_stored_count"],1)
            self.assertEqual(out["errors"],0)
    def test_one_race_unavailable_does_not_block_other_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,3)
            archive={}
            def card_reader(d,v,r):
                if r=="09":
                    bad=json.loads(json.dumps(cards[d+v+r]))
                    bad["beforeinfo"]=None
                    return bad
                return cards[d+v+r]
            out=attempt_batch(tmp,now=lambda:NOW,
                card_reader=card_reader,waku_fetch=lambda url:bytes_,
                prefetch=lambda day:self.fail("no 62-file fallback"),
                sleep=lambda sec:self.fail("batch must not sleep"),
                ledger_ops=(archive.get,lambda path,data:archive.setdefault(path,data)))
            self.assertEqual(out["status"],"t2_batch_partial_capture")
            self.assertEqual(out["attempted_count"],3)
            self.assertEqual(out["stored_count"],2)
            self.assertEqual(out["newly_stored_count"],2)
            self.assertEqual(out["not_stored_count"],1)
            self.assertEqual(out["results"][1]["status"],"preview_not_ready")
            self.assertEqual(len(archive),2)
    def test_remote_failure_is_marked_and_remaining_races_still_attempted(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,2)
            archive={}
            def create(path,data):
                if path.endswith("0708.json"):
                    raise ValueError("write_denied")
                archive[path]=data
            out=attempt_batch(tmp,now=lambda:NOW,
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:bytes_,
                prefetch=lambda day:self.fail("no historical fetch"),
                ledger_ops=(archive.get,create))
            self.assertEqual(out["status"],"t2_batch_error")
            self.assertEqual(out["errors"],1)
            self.assertEqual(out["stored_count"],1)
            self.assertEqual(out["newly_stored_count"],1)
            self.assertEqual(out["errors"],1)
            self.assertEqual(out["results"][0]["status"],"collector_error")
            self.assertEqual(out["results"][1]["status"],"new_append_only_waku10_pilot")
    def test_missing_all_baselines_still_reports_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=attempt_batch(tmp,now=lambda:NOW,
                prefetch=lambda day:self.fail("unneeded historical fetch"))
            self.assertEqual(out["status"],"no_frozen_baseline_in_late_window")
            self.assertEqual(out["baseline_audit"]["status"],
                             "missing_current_day_research_snapshots")
    def test_partial_missing_baseline_not_hidden_by_two_successful_captures(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,2)
            storage={}
            out=attempt_batch(tmp,now=lambda:NOW,verify_expected_schedule=True,
                schedule_fetch=lambda snapshot:(
                    [{"レースコード":f"2026110307{i:02d}",
                      "電話投票締切予定":"18:33"} for i in (8,9,10)],
                    "20261103","a"*64,"published_daily_title"),
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:bytes_,
                ledger_ops=(storage.get,lambda p,b:storage.setdefault(p,b)))
            self.assertEqual(out["newly_stored_count"],2)
            self.assertEqual(out["stored_count"],2)
            self.assertEqual(out["status"],"t2_batch_missing_expected_t12_baselines")
            self.assertEqual(out["missing_baseline_race_codes"],["202611030710"])
            self.assertEqual(len(storage),2)
    def test_complete_t2_cohort_is_not_reported_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,2)
            storage={}
            out=attempt_batch(tmp,now=lambda:NOW,verify_expected_schedule=True,
                schedule_fetch=lambda snapshot:(
                    [{"レースコード":f"2026110307{i:02d}",
                      "電話投票締切予定":"18:33"} for i in (8,9)],
                    "20261103","a"*64,"published_daily_title"),
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:bytes_,
                ledger_ops=(storage.get,lambda p,b:storage.setdefault(p,b)))
            self.assertEqual(out["status"],"t2_batch_completed")
            self.assertEqual(out["missing_baseline_race_codes"],[])
            self.assertEqual(out["stored_count"],2)
    def test_schedule_outage_after_successful_captures_still_keeps_captures(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,bytes_=setup(tmp,1)
            storage={}
            out=attempt_batch(tmp,now=lambda:NOW,verify_expected_schedule=True,
                schedule_fetch=lambda snapshot:(_ for _ in ()).throw(OSError("schedule outage")),
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:bytes_,
                ledger_ops=(storage.get,lambda p,b:storage.setdefault(p,b)))
            self.assertEqual(out["status"],"t2_batch_expected_schedule_unavailable")
            self.assertEqual(out["schedule_error_type"],"OSError")
            self.assertEqual(out["newly_stored_count"],1)
            self.assertEqual(len(storage),1)
    def test_missing_t12_on_actual_scheduled_t2_window_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=attempt_batch(tmp,now=lambda:NOW,verify_expected_schedule=True,
                schedule_fetch=lambda now:(
                    [{"レースコード":"202611030708",
                      "電話投票締切予定":"18:33"}],
                    "20261103","a"*64,"published_daily_title"))
            self.assertEqual(out["status"],"t2_missing_expected_t12_baselines")
            self.assertEqual(out["missing_baseline_race_codes"],["202611030708"])
            self.assertEqual(out["baseline_audit"]["status"],
                             "missing_current_day_research_snapshots")
            self.assertIs(out["stored"],False)
    def test_no_expected_t2_race_is_normal_empty_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=attempt_batch(tmp,now=lambda:NOW,verify_expected_schedule=True,
                schedule_fetch=lambda now:(
                    [{"レースコード":"202611030708",
                      "電話投票締切予定":"20:33"}],
                    "20261103","a"*64,"published_daily_title"))
            self.assertEqual(out["status"],"no_frozen_baseline_in_late_window")
            self.assertEqual(out["expected_schedule"]["expected_race_codes"],[])
    def test_schedule_outage_not_mislabeled_zero_races(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=attempt_batch(tmp,now=lambda:NOW,verify_expected_schedule=True,
                schedule_fetch=lambda now:(_ for _ in ()).throw(
                    OSError("unpublished")),)
            self.assertEqual(out["status"],"t2_expected_schedule_unavailable")
            self.assertEqual(out["schedule_error_type"],"OSError")
    def test_malformed_and_wrong_day_schedule_rows_not_used(self):
        result=expected_t2_without_baseline(NOW,".",schedule_fetch=lambda now:(
            [{"レースコード":"202611030708","電話投票締切予定":"bad"},
             {"レースコード":"202611020708","電話投票締切予定":"18:33"},
             {"レースコード":"202611030709","電話投票締切予定":"18:33"}],
            "20261103","c"*64,"live_holding_schedule"))
        self.assertEqual(result["expected_race_codes"],["202611030709"])
        self.assertEqual(result["schedule_source"],"live_holding_schedule")
    def test_missing_baseline_check_is_opt_in_for_test_injection(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=attempt_batch(tmp,now=lambda:NOW,
                schedule_fetch=lambda now:self.fail("do not call schedule by default"))
            self.assertEqual(out["status"],"no_frozen_baseline_in_late_window")
    def test_partial_capture_retains_original_but_fails_actions_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,raw_csv=setup(tmp,2)
            archived={}
            def reader(d,v,r):
                if r=="09":
                    raise ValueError("preview_not_ready")
                return cards[d+v+r]
            verdict=attempt_batch(tmp,now=lambda:NOW,
                card_reader=reader,waku_fetch=lambda url:raw_csv,
                ledger_ops=(archived.get,lambda p,b:archived.setdefault(p,b)))
            self.assertEqual(verdict["status"],"t2_batch_partial_capture")
            self.assertEqual(verdict["newly_stored_count"],1)
            self.assertEqual(verdict["not_stored_count"],1)
            self.assertEqual(len(archived),1)
            self.assertTrue(t2_cli_failure(verdict))
    def test_cli_success_requires_all_candidate_races_captured(self):
        for state in ("t2_batch_completed","no_frozen_baseline_in_late_window"):
            self.assertFalse(t2_cli_failure({"status":state}))
        for state in ("t2_batch_no_capture","t2_batch_partial_capture",
                      "t2_batch_error","t2_missing_expected_t12_baselines",
                      "t2_expected_schedule_unavailable",
                      "t2_batch_missing_expected_t12_baselines",
                      "t2_batch_t12_deadline_conflict",
                      "t2_batch_expected_schedule_unavailable",
                      "course_evidence_collector_failed"):
            with self.subTest(state=state):
                self.assertTrue(t2_cli_failure({"status":state}))
        with self.assertRaisesRegex(ValueError,"t2_cli_invalid_verdict"):
            t2_cli_failure(None)
    def test_unattended_mode_rejects_local_snapshot_without_durable_t12(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,raw_csv=setup(tmp,1)
            self.assertEqual(len(__import__("entry_course_collector").candidates(
                tmp,now=NOW)),1)
            self.assertEqual(len(__import__("entry_course_collector").candidates(
                tmp,now=NOW,require_durable_t12=True)),0)
            result=attempt_batch(tmp,now=lambda:NOW,require_durable_t12=True,
                verify_expected_schedule=True,
                schedule_fetch=lambda sampled:(
                    [{"レースコード":"202611030708",
                      "電話投票締切予定":"18:33"}],
                    "20261103","a"*64,"published_daily_title"),
                card_reader=lambda *args:self.fail("local original must not be used"),
                waku_fetch=lambda url:self.fail("no unsafe Waku10 capture"))
            self.assertEqual(result["status"],"t2_missing_expected_t12_baselines")
    def test_unattended_rejects_hours_old_remote_baseline_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,_=setup(tmp,1)
            archived=__import__("test_entry_waku10_pilot").fixture()[0]
            archived.update({
                "model_version":"national-beta0.4-exploratory-v1",
                # Old predeadline forecast, generated 21 minutes before cutoff.
                "source_title_received_jst":archived["generated_at"],
                "source_cards_received_jst":archived["generated_at"]})
            folder=Path(tmp)/"entry-course-ledger"/"t12_baselines"/"20261103"
            folder.mkdir(parents=True)
            original_bytes=json.dumps(archived).encode()
            path=folder/"202611030708.json"
            path.write_bytes(original_bytes)
            selected=__import__("entry_course_collector").candidates(
                tmp,now=NOW,require_durable_t12=True)
            self.assertEqual(selected,[])
            self.assertEqual(path.read_bytes(),original_bytes)

    def test_unattended_mode_uses_durable_original_over_conflicting_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,raw_csv=setup(tmp,1)
            local=Path(tmp)/"research_snapshots"/"202611030708.json"
            altered=json.loads(local.read_text())
            altered["predictions"]=["6-5-4"]
            local.write_text(json.dumps(altered))
            durable=Path(tmp)/"entry-course-ledger"/"t12_baselines"/"20261103"
            durable.mkdir(parents=True)
            original=__import__("test_entry_waku10_pilot").fixture()[0]
            original.update({
                "model_version":"national-beta0.4-exploratory-v1",
                # This scenario models a valid *T-12* remote baseline, not
                # the intentionally earlier 18:00 generic preview fixture.
                "generated_at":"2026-11-03T18:15:00+09:00",
                "source_title_received_jst":"2026-11-03T18:15:00+09:00",
                "source_cards_received_jst":"2026-11-03T18:15:00+09:00"})
            (durable/"202611030708.json").write_text(json.dumps(original))
            selected=__import__("entry_course_collector").candidates(
                tmp,now=NOW,require_durable_t12=True)
            self.assertEqual(len(selected),1)
            self.assertEqual(selected[0][2]["predictions"],original["predictions"])
            archive={}
            out=attempt_batch(tmp,now=lambda:NOW,require_durable_t12=True,
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:raw_csv,
                ledger_ops=(archive.get,lambda p,b:archive.setdefault(p,b)))
            self.assertEqual(out["status"],"t2_batch_completed")
            self.assertEqual(out["newly_stored_count"],1)
            self.assertEqual(len(archive),1)
    def test_unattended_rejects_durable_baseline_with_rank_or_digest_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,raw_csv=setup(tmp,1)
            durable=Path(tmp)/"entry-course-ledger"/"t12_baselines"/"20261103"
            durable.mkdir(parents=True)
            original=__import__("test_entry_waku10_pilot").fixture()[0]
            original.update({
                "model_version":"national-beta0.4-exploratory-v1",
                # This scenario models a valid *T-12* remote baseline, not
                # the intentionally earlier 18:00 generic preview fixture.
                "generated_at":"2026-11-03T18:15:00+09:00",
                "source_title_received_jst":"2026-11-03T18:15:00+09:00",
                "source_cards_received_jst":"2026-11-03T18:15:00+09:00"})
            target=durable/"202611030708.json"
            for bad in ("rank","digest","future_receipt","cutoff_receipt"):
                with self.subTest(bad=bad):
                    item=json.loads(json.dumps(original))
                    if bad=="rank":
                        item["predictions"]=["6-5-4"]
                    if bad=="digest":
                        item["source_title_sha256"]="invalid"
                    if bad=="future_receipt":
                        item["source_cards_received_jst"]="2026-11-03T18:22:00+09:00"
                    if bad=="cutoff_receipt":
                        item["source_cards_received_jst"]=item["cutoff_jst"]
                    target.write_text(json.dumps(item))
                    self.assertEqual(__import__("entry_course_collector").candidates(
                        tmp,now=NOW,require_durable_t12=True),[])
                    report=attempt_batch(tmp,now=lambda:NOW,require_durable_t12=True,
                        verify_expected_schedule=True,
                        schedule_fetch=lambda when:(
                            [{"レースコード":"202611030708",
                              "電話投票締切予定":"18:33"}],
                            "20261103","a"*64,"published_daily_title"),
                        card_reader=lambda *args:self.fail("unverified T12 not usable"))
                    self.assertEqual(report["status"],
                                     "t2_missing_expected_t12_baselines")
    def test_independent_schedule_deadline_mismatch_is_fatal_even_when_archive_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,raw_csv=setup(tmp,1)
            archived={}
            verdict=attempt_batch(tmp,now=lambda:NOW,
                verify_expected_schedule=True,
                schedule_fetch=lambda snapshot:(
                    [{"レースコード":"202611030708",
                      "電話投票締切予定":"18:34"}],
                    "20261103","a"*64,"published_daily_title"),
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:raw_csv,
                ledger_ops=(archived.get,lambda path,raw:archived.setdefault(path,raw)))
            self.assertEqual(verdict["status"],"t2_batch_t12_deadline_conflict")
            self.assertEqual(verdict["baseline_deadline_conflict_race_codes"],
                             ["202611030708"])
            self.assertEqual(verdict["missing_baseline_race_codes"],[])
            self.assertTrue(t2_cli_failure(verdict))
            self.assertEqual(verdict["stored_count"],0)
            self.assertEqual(len(archived),0)
            self.assertEqual(verdict["results"][0]["status"],
                             "independent_deadline_conflict")
    def test_mismatched_deadline_cannot_publish_and_other_races_still_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,raw_csv=setup(tmp,2)
            archive={}
            observed=[]
            def reader(day,venue,race):
                observed.append(race)
                return cards[day+venue+race]
            report=attempt_batch(tmp,now=lambda:NOW,
                verify_expected_schedule=True,
                schedule_fetch=lambda snapshot:(
                    [{"レースコード":"202611030708",
                      "電話投票締切予定":"18:34"},
                     {"レースコード":"202611030709",
                      "電話投票締切予定":"18:33"}],
                    "20261103","a"*64,"published_daily_title"),
                card_reader=reader,waku_fetch=lambda url:raw_csv,
                ledger_ops=(archive.get,lambda p,b:archive.setdefault(p,b)))
            self.assertEqual(report["status"],"t2_batch_t12_deadline_conflict")
            self.assertEqual(report["baseline_deadline_conflict_race_codes"],
                             ["202611030708"])
            self.assertEqual(report["stored_count"],1)
            self.assertEqual(report["not_stored_count"],1)
            self.assertEqual(report["results"][0]["status"],
                             "independent_deadline_conflict")
            self.assertEqual(observed,["09"])
            self.assertEqual(set(archive),{"waku10/20261103/202611030709.json"})
            self.assertTrue(t2_cli_failure(report))
    def test_deadline_change_outside_original_window_still_blocks_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,raw_csv=setup(tmp,1)
            report=attempt_batch(tmp,now=lambda:NOW,
                verify_expected_schedule=True,
                schedule_fetch=lambda snapshot:(
                    [{"レースコード":"202611030708",
                      "電話投票締切予定":"18:40"}],
                    "20261103","a"*64,"published_daily_title"),
                card_reader=lambda *args:self.fail("mismatched deadline cannot collect"),
                waku_fetch=lambda *args:self.fail("mismatched deadline cannot read Waku10"))
            self.assertEqual(report["baseline_deadline_conflict_race_codes"],
                             ["202611030708"])
            self.assertEqual(report["status"],"t2_batch_t12_deadline_conflict")
            self.assertEqual(report["newly_stored_count"],0)
    def test_independent_schedule_matching_deadline_has_no_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,raw_csv=setup(tmp,1)
            archived={}
            verdict=attempt_batch(tmp,now=lambda:NOW,
                verify_expected_schedule=True,
                schedule_fetch=lambda snapshot:(
                    [{"レースコード":"202611030708",
                      "電話投票締切予定":"18:33"}],
                    "20261103","a"*64,"published_daily_title"),
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:raw_csv,
                ledger_ops=(archived.get,lambda path,raw:archived.setdefault(path,raw)))
            self.assertEqual(verdict["status"],"t2_batch_completed")
            self.assertEqual(verdict["baseline_deadline_conflict_race_codes"],[])
            self.assertFalse(t2_cli_failure(verdict))
    def test_conflicting_independent_schedule_rows_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards,raw_csv=setup(tmp,1)
            archived={}
            verdict=attempt_batch(tmp,now=lambda:NOW,
                verify_expected_schedule=True,
                schedule_fetch=lambda snapshot:(
                    [{"レースコード":"202611030708",
                      "電話投票締切予定":t} for t in ("18:33","18:34")],
                    "20261103","a"*64,"published_daily_title"),
                card_reader=lambda d,v,r:cards[d+v+r],
                waku_fetch=lambda url:raw_csv,
                ledger_ops=(archived.get,lambda path,raw:archived.setdefault(path,raw)))
            self.assertEqual(verdict["status"],"t2_batch_expected_schedule_unavailable")
            self.assertEqual(verdict["schedule_error_type"],"ValueError")
            self.assertTrue(t2_cli_failure(verdict))
    def test_batch_size_guard(self):
        with self.assertRaisesRegex(ValueError,"batch_size"):
            attempt_batch(".",now=lambda:NOW,max_per_run=100)
if __name__=="__main__":
    unittest.main()
