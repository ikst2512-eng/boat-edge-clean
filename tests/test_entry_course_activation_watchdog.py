import unittest
from datetime import datetime,timedelta,timezone

from scripts.entry_course_activation_watchdog import (
    dispatch_decision,run_once,preview_fallback,PREVIEW_WORKFLOW,TARGETS,JST,
)

NOW=datetime(2026,11,4,10,12,tzinfo=JST)

def event(*,minutes=0,kind="schedule",status="completed",branch="main",
          conclusion="success"):
    return {"event":kind,"created_at":(NOW-timedelta(minutes=minutes)).isoformat(),
            "status":status,"head_branch":branch,"conclusion":conclusion}

class ActivationTests(unittest.TestCase):
    def test_empty_active_hour_dispatches_both_separately(self):
        requested=[]
        out=run_once(now=NOW,fetch_runs=lambda f,e:[],
                     dispatch=lambda f:requested.append(f))
        self.assertEqual(requested,list(TARGETS.values()))
        self.assertEqual(out["targets"]["t12"]["decision"],
                         "dispatch_missing_research_job")
        self.assertTrue(out["targets"]["t2"]["dispatch_requested"])
        self.assertFalse(out["unattended_scheduled_capture_verified"])
        self.assertFalse(out["forecast_record"])
        self.assertFalse(out["independent_first_seen_verified"])
    def test_outside_research_hours_never_dispatch(self):
        for hour in (0,7,23):
            with self.subTest(hour=hour):
                out=run_once(now=NOW.replace(hour=hour),
                    fetch_runs=lambda f,e:[],
                    dispatch=lambda f:self.fail("outside hours"))
                self.assertEqual(out["targets"]["t12"]["decision"],
                                 "outside_research_hours")
    def test_early_08_jst_t12_only_and_no_early_t2(self):
        # 08:35 JST race: T-12 is 08:23 and eligible selection 08:09-08:21.
        early=NOW.replace(hour=8,minute=12)
        dispatched=[]
        output=run_once(now=early,fetch_runs=lambda f,e:[],
                        dispatch=lambda f:dispatched.append(f))
        self.assertEqual(dispatched,[TARGETS["t12"]])
        self.assertEqual(output["targets"]["t12"]["decision"],
                         "dispatch_missing_research_job")
        self.assertEqual(output["targets"]["t2"]["decision"],
                         "outside_research_hours")
        self.assertFalse(output["targets"]["t2"]["dispatch_requested"])
        self.assertFalse(output["independent_first_seen_verified"])
        self.assertFalse(output["unattended_scheduled_capture_verified"])

    def test_early_t12_respects_recent_run_and_active_guard(self):
        early=NOW.replace(hour=8,minute=12)
        recent={"event":"workflow_dispatch","created_at":
                (early-timedelta(minutes=2)).isoformat(),"status":"completed",
                "head_branch":"main","conclusion":"failure"}
        self.assertEqual(dispatch_decision(early,[recent],kind="t12"),
                         "research_run_recently_started")
        active=dict(recent,created_at=(early-timedelta(minutes=16)).isoformat(),
                    status="in_progress",conclusion=None)
        self.assertEqual(dispatch_decision(early,[active],kind="t12"),
                         "research_job_already_active")
        with self.assertRaisesRegex(ValueError,"target_invalid"):
            dispatch_decision(early,[],kind="unknown")

    def test_existing_crons_cover_08_jst_without_new_workflow(self):
        from pathlib import Path
        root=Path(__file__).resolve().parent.parent
        seed=(root/".github/workflows/entry-course-t12-baseline.yml").read_text()
        rescue=(root/".github/workflows/entry-course-activation-watchdog.yml").read_text()
        self.assertIn("cron: '*/5 23,0-13 * * *'",seed)
        self.assertIn("cron: '3,13,23,33,43,53 23,0-13 * * *'",rescue)
        self.assertEqual(seed.count("- cron:"),1)
        self.assertEqual(rescue.count("- cron:"),1)
        from entry_course_t12_seed import near_t12
        rows=[{"レースコード":"202611102101",
               "電話投票締切予定":"08:35"}]
        self.assertEqual(near_t12(rows,"20261110",now=datetime(
            2026,11,10,8,12,tzinfo=JST)),["202611102101"])
        self.assertEqual(near_t12(rows,"20261110",now=datetime(
            2026,11,10,8,24,tzinfo=JST)),[])

    def test_single_existing_watchdog_cron_can_theoretically_cover_all_day_races(self):
        # This checks scheduled-time *possibility*, not actual GitHub runs,
        # collector execution, on-time official source, or first remote write.
        from pathlib import Path
        import json
        root=Path(__file__).resolve().parent.parent
        schedule=json.loads((root/"schedule_snapshots/20261110.json").read_text())
        self.assertEqual(sum(len(v["races"]) for v in schedule["venues"]),156)
        # UTC hours 23,0-13 map to JST hours 08-22; six slots each hour.
        ticks={60*h+m for h in range(8,23)
               for m in (3,13,23,33,43,53)}
        for venue in schedule["venues"]:
            for race in venue["races"]:
                h,m=map(int,race["deadline"].split(":"))
                deadline=h*60+m
                # near_t12 accepts 2..14min before cutoff (deadline-12).
                with self.subTest(venue=venue["jcd"],race=race["race_no"]):
                    self.assertTrue(any(deadline-26<=t<=deadline-14
                                        for t in ticks),
                                    "missing theoretical T12 watchdog tick")
        # A recovery invocation does not assert a saved or formal forecast.
        self.assertFalse(run_once(
            now=NOW.replace(hour=8,minute=13),
            fetch_runs=lambda f,e:[],
            dispatch=lambda f:None)["independent_first_seen_verified"])

    def test_recent_real_schedule_prevents_duplicate_dispatch(self):
        self.assertEqual(dispatch_decision(NOW,[event(minutes=4)]),
                         "research_run_recently_started")
    def test_recent_fallback_prevents_duplicate_dispatch(self):
        self.assertEqual(dispatch_decision(NOW,[event(
            kind="workflow_dispatch",minutes=2,conclusion="failure")]),
            "research_run_recently_started")
    def test_older_failed_job_allows_bounded_recovery(self):
        self.assertEqual(dispatch_decision(NOW,[event(minutes=6,
                         conclusion="failure")]),
                         "dispatch_missing_research_job")
    def test_running_job_prevents_overlapping_recovery(self):
        self.assertEqual(dispatch_decision(NOW,[event(
            minutes=16,status="in_progress",conclusion=None)]),
            "research_job_already_active")
    def test_wrong_branch_and_pr_runs_are_never_evidence_of_capture(self):
        self.assertEqual(dispatch_decision(NOW,[
            event(minutes=1,kind="pull_request"),
            event(minutes=2,kind="workflow_dispatch",branch="feature")]),
            "dispatch_missing_research_job")
    def test_event_queries_are_distinct_and_fail_closed(self):
        called=[]
        def fetch(f,event_name):
            called.append((f,event_name))
            return [event(minutes=2,kind=event_name)]
        output=run_once(now=NOW,fetch_runs=fetch,
                        dispatch=lambda _:self.fail("recent run exists"))
        self.assertEqual(len(called),4)
        self.assertEqual(output["targets"]["t12"]["observed_schedule_runs"],1)
        self.assertEqual(output["targets"]["t12"]["observed_dispatch_runs"],1)
        with self.assertRaisesRegex(ValueError,"runs_invalid"):
            run_once(now=NOW,fetch_runs=lambda f,e:None,dispatch=lambda f:None)
    def test_second_target_api_failure_never_partially_dispatches_first(self):
        calls=[]
        requested=[]
        def fetch(file,kind):
            calls.append((file,kind))
            if file==TARGETS["t2"]:
                raise ValueError("simulated_t2_api_error")
            return []
        with self.assertRaisesRegex(ValueError,"simulated_t2_api_error"):
            run_once(now=NOW,fetch_runs=fetch,
                     dispatch=lambda f:requested.append(f))
        self.assertEqual(requested,[])
        self.assertEqual(calls[:2],[(TARGETS["t12"],"schedule"),
                                    (TARGETS["t12"],"workflow_dispatch")])

    def test_second_target_invalid_receipt_never_partially_dispatches_first(self):
        requested=[]
        def fetch(file,kind):
            return [event(minutes=40,status="unknown")] if file==TARGETS["t2"] else []
        with self.assertRaisesRegex(ValueError,"run_status_invalid"):
            run_once(now=NOW,fetch_runs=fetch,
                     dispatch=lambda f:requested.append(f))
        self.assertEqual(requested,[])

    def test_invalid_clock_and_run_receipts_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"clock_invalid"):
            dispatch_decision(datetime(2026,11,4,10,12),[])
        with self.assertRaisesRegex(ValueError,"timestamp_naive"):
            dispatch_decision(NOW,[{"event":"schedule",
                "created_at":"2026-11-04T10:11:00",
                "head_branch":"main","status":"completed"}])
        with self.assertRaisesRegex(ValueError,"future_run_timestamp"):
            dispatch_decision(NOW,[event(minutes=-2)])
        with self.assertRaisesRegex(ValueError,"run_invalid"):
            dispatch_decision(NOW,[None])
        # Missing or unknown GitHub status must not allow recovery dispatch.
        for bad_status in (None, "", "mystery", 123):
            with self.subTest(bad_status=bad_status):
                malformed=event(minutes=40)
                malformed["status"]=bad_status
                with self.assertRaisesRegex(ValueError,"run_status_invalid"):
                    dispatch_decision(NOW,[malformed])
                with self.assertRaisesRegex(ValueError,"run_status_invalid"):
                    run_once(now=NOW,
                        fetch_runs=lambda f,e:[malformed],
                        dispatch=lambda _:self.fail("malformed run triggered dispatch"))

    def test_preview_fallback_uses_existing_event_without_new_cron(self):
        requested=[]
        called=[]
        def fetch(file,kind):
            called.append((file,kind))
            return []
        result=preview_fallback(NOW,fetch,lambda file:requested.append(file))
        self.assertEqual(called,[(PREVIEW_WORKFLOW,"schedule"),
                                 (PREVIEW_WORKFLOW,"workflow_dispatch")])
        self.assertEqual(requested,[PREVIEW_WORKFLOW])
        self.assertTrue(result["dispatch_requested"])
        self.assertFalse(result["trigger_is_schedule"])
        self.assertFalse(result["saved_forecast_verified"])

    def test_preview_fallback_does_not_run_at_8_or_after_22(self):
        for hour in (7,8,22,23):
            with self.subTest(hour=hour):
                result=preview_fallback(NOW.replace(hour=hour),
                    lambda *a:self.fail("outside preview hours should not query API"),
                    lambda _:self.fail("outside preview hours dispatched"))
                self.assertEqual(result["decision"],"outside_preview_hours")
                self.assertFalse(result["dispatch_requested"])

    def test_preview_recent_or_active_prevents_duplicate_dispatch(self):
        for row,expected in (
            (event(minutes=3,kind="schedule"),"research_run_recently_started"),
            (event(minutes=2,kind="workflow_dispatch"),"research_run_recently_started"),
            (event(minutes=15,kind="workflow_dispatch",status="in_progress"),
             "research_job_already_active"),
        ):
            with self.subTest(expected=expected):
                result=preview_fallback(NOW,
                    lambda file,event_name:[row] if row["event"]==event_name else [],
                    lambda _:self.fail("Duplicate preview capture"))
                self.assertEqual(result["decision"],expected)
                self.assertFalse(result["dispatch_requested"])

    def test_preview_failure_is_separate_from_primary_t12_t2_preflight(self):
        requested=[]
        run_once(now=NOW,fetch_runs=lambda file,kind:[],
                 dispatch=lambda file:requested.append(file))
        self.assertEqual(requested,list(TARGETS.values()))
        with self.assertRaisesRegex(ValueError,"preview_watchdog_api_runs_invalid"):
            preview_fallback(NOW,lambda file,kind:None,
                             lambda _:self.fail("malformed preview triggered dispatch"))
        self.assertEqual(requested,list(TARGETS.values()))

    def test_preview_guard_preserves_cron_and_workflow_concurrency(self):
        from pathlib import Path
        root=Path(__file__).resolve().parent.parent
        watcher=(root/".github/workflows/entry-course-activation-watchdog.yml").read_text()
        preview=(root/".github/workflows/research-live-preview-evidence.yml").read_text()
        self.assertEqual(watcher.count("- cron:"),1)
        self.assertIn("cancel-in-progress: false",preview)
        self.assertIn("independent-late-preview-",preview)

if __name__=="__main__":unittest.main()
