import unittest
from datetime import datetime,timedelta,timezone

from scripts.entry_course_activation_watchdog import (
    dispatch_decision,run_once,preview_fallback,PREVIEW_WORKFLOW,
    PREVIEW_WATCHDOG_MARK,dispatch_payload,TARGETS,JST,
    OFFICIAL_PROBE_WORKFLOW,official_live_probe_fallback,
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

    def test_08_t12_rescue_does_not_depend_on_inactive_t2_api(self):
        early=NOW.replace(hour=8,minute=12)
        calls=[]
        dispatched=[]
        def fetch(file,event_name):
            calls.append((file,event_name))
            if file==TARGETS["t2"]:
                self.fail("08 JST must not query inactive T2")
            return []
        output=run_once(now=early,fetch_runs=fetch,
                        dispatch=lambda file:dispatched.append(file))
        self.assertEqual(calls,[(TARGETS["t12"],"schedule"),
                                (TARGETS["t12"],"workflow_dispatch")])
        self.assertEqual(dispatched,[TARGETS["t12"]])
        self.assertTrue(output["targets"]["t2"]["lookup_skipped_outside_hours"])
        self.assertEqual(output["targets"]["t2"]["decision"],
                         "outside_research_hours")
        self.assertFalse(output["targets"]["t2"]["dispatch_requested"])
        self.assertFalse(output["independent_first_seen_verified"])

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

    def test_existing_clean_schedule_can_wake_t12_without_new_cron(self):
        # Completion of an independent CLEAN schedule is only a wakeup event:
        # it is not a T12 schedule run, source receipt, or saved forecast.
        from pathlib import Path
        root=Path(__file__).resolve().parent.parent
        clean=(root/".github/workflows/clean-prospective.yml").read_text()
        watcher=(root/".github/workflows/entry-course-activation-watchdog.yml").read_text()
        self.assertIn("cron: '4,19,34,49 23 * * *'",clean)
        self.assertIn('- "Four-mode prospective capture (research only)"',watcher)
        self.assertIn('- "CLEAN prospective pre-cutoff capture"',watcher)
        self.assertIn("github.event.workflow_run.event == 'schedule'",watcher)
        self.assertIn("github.event.workflow_run.head_branch == 'main'",watcher)
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository",watcher)
        self.assertEqual(watcher.count("- cron:"),1)
        self.assertNotIn("forecast_record: true",watcher)

    def test_v236_schedule_wakes_08_t12_and_19_official_rescue(self):
        # V236 schedule completions only wake the existing guarded watchdog:
        # UTC 23:xx = JST 08:xx and UTC 10:xx = JST 19:xx.
        # The official probe itself cannot dispatch before 19:40 JST.
        from pathlib import Path
        from entry_course_t12_seed import near_t12
        root=Path(__file__).resolve().parent.parent
        v236=(root/".github/workflows/v236-verification.yml").read_text()
        watchdog=(root/".github/workflows/entry-course-activation-watchdog.yml").read_text()
        self.assertIn("name: CLEAN V236 verification queue",v236)
        self.assertIn("cron: '2,7,12,17,22,27,32,37,42,47,52,57 * * * *'",v236)
        self.assertIn('- "CLEAN V236 verification queue"',watchdog)
        self.assertIn("github.event.workflow_run.name != 'CLEAN V236 verification queue'",watchdog)
        self.assertIn("contains(github.event.workflow_run.created_at, 'T23:')",watchdog)
        self.assertIn("contains(github.event.workflow_run.created_at, 'T10:')",watchdog)
        self.assertIn("github.event.workflow_run.event == 'schedule'",watchdog)
        self.assertIn("github.event.workflow_run.head_branch == 'main'",watchdog)
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository",watchdog)
        self.assertEqual(watchdog.count("- cron:"),1)
        sample=[{"レースコード":"202611102101",
                 "電話投票締切予定":"08:35"}]
        self.assertEqual(near_t12(sample,"20261110",now=datetime(
            2026,11,10,8,11,tzinfo=JST)),["202611102101"])
        self.assertFalse(run_once(now=NOW.replace(hour=8,minute=11),
            fetch_runs=lambda file,event:[],
            dispatch=lambda file:None)["unattended_scheduled_capture_verified"])

    def test_four_mode_watchdog_existing_schedule_can_wake_eight_and_nineteen_only(self):
        # The existing independent workflow has actual 11/11 schedule runs,
        # but is not a T12 schedule event or evidence of source receipt.
        # Parent completion only wakes the same guarded rescue job at UTC
        # 23 (08 JST) or 10 (19 JST); no new Cron, no feedback loop.
        from pathlib import Path
        root=Path(__file__).resolve().parent.parent
        independent=(root/".github/workflows/four-mode-capture-watchdog.yml").read_text()
        watcher=(root/".github/workflows/entry-course-activation-watchdog.yml").read_text()
        self.assertIn("name: Four-mode capture schedule watchdog",independent)
        self.assertIn("cron: '13,28,43,58 22-23,0-12 * * *'",independent)
        self.assertIn('- "Four-mode capture schedule watchdog"',watcher)
        self.assertIn("github.event.workflow_run.name != 'Four-mode capture schedule watchdog'",watcher)
        self.assertIn("contains(github.event.workflow_run.created_at, 'T23:')",watcher)
        self.assertIn("contains(github.event.workflow_run.created_at, 'T10:')",watcher)
        self.assertIn("github.event.workflow_run.event == 'schedule'",watcher)
        self.assertIn("github.event.workflow_run.head_branch == 'main'",watcher)
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository",watcher)
        self.assertNotIn('- "Entry course missed-cron activation watchdog"',independent)
        self.assertEqual(watcher.count("- cron:"),1)
        self.assertEqual(independent.count("- cron:"),4)
        attempted=[]
        now=datetime(2026,11,11,19,44,tzinfo=JST)
        result=official_live_probe_fallback(now,lambda file,event:[],
                                           lambda file:attempted.append(file))
        self.assertEqual(attempted,[OFFICIAL_PROBE_WORKFLOW])
        self.assertEqual(result["decision"],"requested_missing_official_probe")
        self.assertFalse(result["live_24_values_verified"])
        self.assertFalse(result["trigger_is_schedule"])
        self.assertFalse(result["formal_t12_certified"])

    def test_existing_result_native_tick_wakes_only_evening_official_rescue(self):
        # On Nov 11 this independent result collector had a real native
        # schedule at 19:48 JST while the 19:35 official cron was unobserved.
        # Wake is allowed for UTC 10:40-10:59 only; never promote the
        # collector to a native official verification or a saved forecast.
        from pathlib import Path
        root=Path(__file__).resolve().parent.parent
        collector=(root/".github/workflows/collect-clean-results.yml").read_text()
        watchdog=(root/".github/workflows/entry-course-activation-watchdog.yml").read_text()
        self.assertIn("name: CLEAN independent confirmed result collection",collector)
        self.assertIn("cron: '*/10 * * * *'",collector)
        self.assertIn('- "CLEAN independent confirmed result collection"',watchdog)
        self.assertIn(
            "github.event.workflow_run.name != 'CLEAN independent confirmed result collection'",
            watchdog)
        self.assertIn("contains(github.event.workflow_run.created_at, 'T10:4')",watchdog)
        self.assertIn("contains(github.event.workflow_run.created_at, 'T10:5')",watchdog)
        self.assertIn("github.event.workflow_run.event == 'schedule'",watchdog)
        self.assertIn("github.event.workflow_run.head_branch == 'main'",watchdog)
        self.assertIn(
            "github.event.workflow_run.head_repository.full_name == github.repository",
            watchdog)
        self.assertEqual(watchdog.count("- cron:"),1)
        self.assertNotIn('- "Entry course missed-cron activation watchdog"',collector)
        callbacks=[]
        result=official_live_probe_fallback(
            datetime(2026,11,11,19,48,tzinfo=JST),
            lambda file,event:[],
            lambda file:callbacks.append(file))
        self.assertEqual(callbacks,[OFFICIAL_PROBE_WORKFLOW])
        self.assertEqual(result["decision"],"requested_missing_official_probe")
        self.assertFalse(result["trigger_is_schedule"])
        self.assertFalse(result["formal_t12_certified"])

    def test_existing_readonly_audit_completions_can_opportunistically_wake_t12(self):
        # 11/11 real GitHub schedules: AI audit completed ~08:31 JST,
        # cross-model audit completed ~08:36 JST despite 03 JST cron times.
        # These are optional wakeups, NEVER guaranteed timely schedules or
        # proof that any forecast source existed or Git first-seen succeeded.
        from pathlib import Path
        root=Path(__file__).resolve().parent.parent
        watchdog=(root/".github/workflows/entry-course-activation-watchdog.yml").read_text()
        ai=(root/".github/workflows/ai-operations-audit.yml").read_text()
        cross=(root/".github/workflows/cross-model-content-audit-tests.yml").read_text()
        self.assertIn("name: AI operations read-only audit",ai)
        self.assertIn("name: Cross-model content audit",cross)
        self.assertIn("cron: '23 18 * * *'",ai)
        self.assertIn("cron: '17 18 * * *'",cross)
        self.assertIn('- "AI operations read-only audit"',watchdog)
        self.assertIn('- "Cross-model content audit"',watchdog)
        self.assertIn("github.event.workflow_run.event == 'schedule'",watchdog)
        self.assertIn("github.event.workflow_run.head_branch == 'main'",watchdog)
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository",watchdog)
        self.assertIn("cancel-in-progress: false",watchdog)
        self.assertEqual(watchdog.count("- cron:"),1)
        # A wakeup can request a research-only dispatch; it cannot upgrade
        # evidence to a scheduled research run, first-seen, or formal T12.
        early=NOW.replace(hour=8,minute=32)
        requested=[]
        report=run_once(now=early,fetch_runs=lambda *_:[],
                        dispatch=lambda file:requested.append(file))
        self.assertEqual(requested,[TARGETS["t12"]])
        self.assertFalse(report["unattended_scheduled_capture_verified"])
        self.assertFalse(report["independent_first_seen_verified"])
        self.assertFalse(report["formal"])

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


    def test_watchdog_reports_today_schedule_separately_from_history(self):
        # API per_page=30 includes past JST days. Total returned rows
        # are NOT evidence of that many schedule launches today.
        now=datetime(2026,11,11,8,32,tzinfo=JST)
        yesterday={"event":"schedule",
                   "created_at":"2026-11-10T08:29:00+09:00",
                   "head_branch":"main","status":"completed"}
        same_day={"event":"schedule",
                  "created_at":"2026-11-11T08:24:00+09:00",
                  "head_branch":"main","status":"completed"}
        wrong_branch=dict(same_day,head_branch="feature")
        dispatch_today=dict(same_day,event="workflow_dispatch",
                            created_at="2026-11-11T08:26:00+09:00")
        def records(file,kind):
            if file!=TARGETS["t12"]:
                self.fail("08 JST must not query T2")
            return ([yesterday,same_day,wrong_branch] if kind=="schedule"
                    else [dispatch_today])
        out=run_once(now=now,fetch_runs=records,dispatch=lambda *_:None)
        counts=out["targets"]["t12"]
        self.assertEqual(counts["observed_schedule_runs"],3) # historic API rows
        self.assertEqual(counts["observed_schedule_runs_today"],1)
        self.assertEqual(counts["observed_dispatch_runs"],1)
        self.assertEqual(counts["observed_dispatch_runs_today"],1)
        self.assertEqual(out["targets"]["t2"]["observed_schedule_runs_today"],0)
        self.assertFalse(out["unattended_scheduled_capture_verified"])

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

    def test_preview_native_schedule_day_and_gap_are_separate_from_manual_rescue(self):
        # At 19:05 JST the only observed native run was at 14:24 JST.
        # The 19:04 rescue is a separate event and suppresses a duplicate.
        now=datetime(2026,11,11,19,5,tzinfo=JST)
        historic={"event":"schedule","created_at":"2026-11-10T14:24:20+09:00",
                  "head_branch":"main","status":"completed"}
        last_native={"event":"schedule","created_at":"2026-11-11T14:24:20+09:00",
                     "head_branch":"main","status":"completed"}
        wrong_branch={**last_native,"created_at":"2026-11-11T19:04:00+09:00",
                      "head_branch":"research"}
        rescue={"event":"workflow_dispatch","created_at":"2026-11-11T19:04:00+09:00",
                "head_branch":"main","status":"completed"}
        called=[]
        def fetched(file,kind):
            self.assertEqual(file,PREVIEW_WORKFLOW)
            return ([historic,last_native,wrong_branch] if kind=="schedule"
                    else [rescue])
        out=preview_fallback(now,fetched,lambda file:called.append(file))
        self.assertEqual(out["observed_schedule_runs"],3)
        self.assertEqual(out["observed_schedule_runs_today"],1)
        self.assertEqual(out["observed_dispatch_runs_today"],1)
        self.assertEqual(out["native_schedule_observation"],
                         "native_schedule_observed_with_over_20min_gap")
        self.assertEqual(out["latest_native_schedule_jst"],
                         "2026-11-11T14:24:20+09:00")
        self.assertGreater(out["latest_native_schedule_age_minutes"],280)
        self.assertEqual(out["decision"],"research_run_recently_started")
        self.assertFalse(out["dispatch_requested"])
        self.assertEqual(called,[])
        self.assertFalse(out["trigger_is_schedule"])

    def test_preview_native_schedule_unobserved_today_despite_rescue_success(self):
        now=datetime(2026,11,11,19,5,tzinfo=JST)
        yesterday={"event":"schedule","created_at":"2026-11-10T21:00:00+09:00",
                   "head_branch":"main","status":"completed"}
        rescue={"event":"workflow_dispatch","created_at":"2026-11-11T19:03:00+09:00",
                "head_branch":"main","status":"completed"}
        out=preview_fallback(now,
            lambda f,e: [yesterday] if e=="schedule" else [rescue],
            lambda _:self.fail("No duplicate dispatch after manual rescue"))
        self.assertEqual(out["observed_schedule_runs"],1)
        self.assertEqual(out["observed_schedule_runs_today"],0)
        self.assertEqual(out["observed_dispatch_runs_today"],1)
        self.assertEqual(out["native_schedule_observation"],
                         "no_native_schedule_observed_today")
        self.assertFalse(out["dispatch_requested"])
        self.assertFalse(out["saved_forecast_verified"])

    def test_preview_recent_native_schedule_is_not_a_forecast_certificate(self):
        now=datetime(2026,11,11,19,5,tzinfo=JST)
        native={"event":"schedule","created_at":"2026-11-11T19:02:00+09:00",
                "head_branch":"main","status":"completed"}
        out=preview_fallback(now,
            lambda f,e:[native] if e=="schedule" else [],
            lambda _:self.fail("recent native schedule must suppress fallback"))
        self.assertEqual(out["observed_schedule_runs_today"],1)
        self.assertEqual(out["native_schedule_observation"],
                         "native_schedule_observed_within_20min")
        self.assertEqual(out["latest_native_schedule_age_minutes"],3)
        self.assertFalse(out["dispatch_requested"])
        self.assertFalse(out["saved_forecast_verified"])

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

    def test_watchdog_dispatch_labels_only_preview_and_not_t12_or_t2(self):
        self.assertEqual(dispatch_payload(PREVIEW_WORKFLOW),
            {"ref":"main","inputs":{"rescue_origin":PREVIEW_WATCHDOG_MARK}})
        for file in TARGETS.values():
            self.assertEqual(dispatch_payload(file),{"ref":"main"})
        with self.assertRaisesRegex(ValueError,"dispatch_target_unknown"):
            dispatch_payload("other.yml")
        from pathlib import Path
        root=Path(__file__).resolve().parent.parent
        workflow=(root/".github/workflows/research-live-preview-evidence.yml").read_text()
        self.assertIn("rescue_origin:",workflow)
        self.assertIn("watchdog-requested",workflow)

    def test_official_probe_fallback_one_window_no_new_cron(self):
        now=datetime(2026,11,11,19,43,tzinfo=JST)
        requested=[]
        api=[]
        def fetch(file,event_name):
            api.append((file,event_name))
            return []
        rec=official_live_probe_fallback(
            now,fetch,lambda target:requested.append(target))
        self.assertEqual(requested,[OFFICIAL_PROBE_WORKFLOW])
        self.assertEqual(api,[(OFFICIAL_PROBE_WORKFLOW,"schedule"),
                              (OFFICIAL_PROBE_WORKFLOW,"workflow_dispatch")])
        self.assertEqual(rec["decision"],"requested_missing_official_probe")
        self.assertTrue(rec["dispatch_requested"])
        self.assertFalse(rec["trigger_is_schedule"])
        self.assertFalse(rec["live_24_values_verified"])
        self.assertFalse(rec["formal_t12_certified"])
        self.assertEqual(dispatch_payload(OFFICIAL_PROBE_WORKFLOW),{"ref":"main"})
        from pathlib import Path
        root=Path(__file__).resolve().parent.parent
        watcher=(root/".github/workflows/entry-course-activation-watchdog.yml").read_text()
        official=(root/".github/workflows/verify-real-beforeinfo.yml").read_text()
        self.assertEqual(watcher.count("- cron:"),1)
        self.assertEqual(official.count("- cron:"),1)
        self.assertIn("cron: '35 10 * * *'",official)

    def test_official_probe_does_not_dispatch_outside_single_hour(self):
        for h,m in ((18,59),(19,35),(19,39),(20,0),(22,0),(8,0)):
            with self.subTest(hour=h,minute=m):
                at=datetime(2026,11,11,h,m,tzinfo=JST)
                rec=official_live_probe_fallback(at,
                    lambda *args:self.fail("outside window API access"),
                    lambda *_:self.fail("outside window dispatch"))
                self.assertEqual(rec["decision"],"outside_official_probe_window")

    def test_official_probe_recent_schedule_or_dispatch_suppresses_duplicates(self):
        now=datetime(2026,11,11,19,43,tzinfo=JST)
        for kind,minute in (("schedule",35),("workflow_dispatch",41),
                            ("workflow_dispatch",17)):
            row={"event":kind,"created_at":now.replace(minute=minute).isoformat(),
                 "head_branch":"main","status":"completed"}
            with self.subTest(kind=kind,minute=minute):
                rec=official_live_probe_fallback(now,
                    lambda _,event_name:[row] if event_name==kind else [],
                    lambda *_:self.fail("duplicate official probe"))
                self.assertEqual(rec["decision"],"official_probe_started_already")
                self.assertFalse(rec["dispatch_requested"])
        # A separate PR or yesterday's dispatch is not evidence today.
        old={"event":"workflow_dispatch","created_at":
             datetime(2026,11,10,19,40,tzinfo=JST).isoformat(),
             "head_branch":"main","status":"completed"}
        pr=dict(old,created_at=now.isoformat(),event="pull_request")
        requested=[]
        result=official_live_probe_fallback(now,
            lambda _,event_name:[old,pr] if event_name=="workflow_dispatch" else [],
            lambda f:requested.append(f))
        self.assertTrue(result["dispatch_requested"])
        self.assertEqual(requested,[OFFICIAL_PROBE_WORKFLOW])

    def test_official_probe_retry_once_only_after_definite_primary_failure(self):
        base=datetime(2026,11,11,19,53,tzinfo=JST)
        def run(event,minute,conclusion,status="completed"):
            return {"event":event,"created_at":base.replace(minute=minute).isoformat(),
                    "head_branch":"main","status":status,"conclusion":conclusion}
        primary=run("schedule",35,"failure")
        requested=[]
        def rows_for(scheduled,dispatched=None):
            return lambda _,event: (scheduled if event=="schedule" else (dispatched or []))
        report=official_live_probe_fallback(base,rows_for([primary]),
            lambda file:requested.append(file))
        self.assertEqual(requested,[OFFICIAL_PROBE_WORKFLOW])
        self.assertEqual(report["decision"],"requested_retry_after_failed_official_probe")
        self.assertEqual(report["observed_failed_schedule_runs"],1)
        self.assertFalse(report["live_24_values_verified"])
        self.assertFalse(report["formal_t12_certified"])

        # Never retry early, or after success, unknown result, an active run,
        # an earlier dispatch (even a failed one), or multiple schedule runs.
        for label,at,scheduled,dispatched in [
            ("too_early",base.replace(minute=43),[primary],[]),
            ("success",base,[run("schedule",35,"success")],[]),
            ("unknown",base,[run("schedule",35,None)],[]),
            ("active",base,[run("schedule",35,None,"in_progress")],[]),
            ("dispatch_exists",base,[primary],[run("workflow_dispatch",45,"failure")]),
            ("two_schedules",base,[primary,run("schedule",44,"failure")],[]),
        ]:
            with self.subTest(case=label):
                record=official_live_probe_fallback(at,rows_for(scheduled,dispatched),
                    lambda *_:self.fail("duplicate or unverified retry"))
                self.assertEqual(record["decision"],"official_probe_started_already")
                self.assertFalse(record["dispatch_requested"])

    def test_official_probe_malformed_run_fails_closed(self):
        at=datetime(2026,11,11,19,43,tzinfo=JST)
        base={"event":"schedule","head_branch":"main",
              "created_at":at.isoformat(),"status":"completed"}
        for row in [None,dict(base,status="unknown"),
                    dict(base,created_at="not-a-date"),
                    dict(base,created_at=at.replace(minute=59).isoformat())]:
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    official_live_probe_fallback(at,
                        lambda _,event_name:[row] if event_name=="schedule" else [],
                        lambda *_:self.fail("malformed API triggered dispatch"))
        with self.assertRaisesRegex(ValueError,"runs_invalid"):
            official_live_probe_fallback(at,
                lambda *_:None,lambda *_:self.fail("invalid API triggered dispatch"))

    def test_preview_guard_preserves_cron_and_workflow_concurrency(self):
        from pathlib import Path
        root=Path(__file__).resolve().parent.parent
        watcher=(root/".github/workflows/entry-course-activation-watchdog.yml").read_text()
        preview=(root/".github/workflows/research-live-preview-evidence.yml").read_text()
        self.assertEqual(watcher.count("- cron:"),1)
        self.assertIn("cancel-in-progress: false",preview)
        self.assertIn("independent-late-preview-",preview)

if __name__=="__main__":unittest.main()
