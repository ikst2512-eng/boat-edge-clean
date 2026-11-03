import unittest
from datetime import datetime,timedelta,timezone

from scripts.entry_course_activation_watchdog import (
    dispatch_decision,run_once,TARGETS,JST,
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
        for hour in (0,8,23):
            with self.subTest(hour=hour):
                out=run_once(now=NOW.replace(hour=hour),
                    fetch_runs=lambda f,e:[],
                    dispatch=lambda f:self.fail("outside hours"))
                self.assertEqual(out["targets"]["t12"]["decision"],
                                 "outside_research_hours")
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
if __name__=="__main__":unittest.main()
