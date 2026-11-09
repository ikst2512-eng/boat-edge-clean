import unittest
import contextlib
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from scripts.audit_four_mode_daily_schedule_runs import (
    audit_day, nominal_schedule_slots_due, NOMINAL_DAILY_CAPTURE_SLOTS,
)


class DailyScheduleRunMetadataTest(unittest.TestCase):
    @staticmethod
    def make_run(run_id, timestamp, status="completed", conclusion="success"):
        return {"event": "schedule", "id": run_id, "created_at": timestamp,
                "status": status, "conclusion": conclusion}

    def test_failed_daily_metadata_does_not_suppress_detail_artifact_audit(self):
        from pathlib import Path
        workflow = Path(".github/workflows/four-mode-schedule-inventory.yml").read_text(
            encoding="utf-8")
        self.assertIn(
            "name: Check complete JST-day scheduled capture execution metadata\n"
            "        if: always()", workflow)
        self.assertIn(
            "name: Inspect recent capture artifacts without inferring remote push proof\n"
            "        if: always()", workflow)
        self.assertIn("reports/four_mode_schedule_publications.json", workflow)
        self.assertIn("reports/four_mode_daily_schedule_metadata.json", workflow)

    def test_independent_fallback_diagnostics_run_despite_upstream_failure(self):
        from pathlib import Path
        workflow = Path(".github/workflows/four-mode-schedule-inventory.yml").read_text(
            encoding="utf-8")
        for step in (
            "Compare scheduled runs with fallback dispatch and watchdog history",
            "Audit fallback dispatch publication artifacts using existing evidence checks",
            "Audit watchdog decision artifacts and subsequent capture timing",
        ):
            with self.subTest(step=step):
                self.assertIn("name: " + step + "\n        if: always()", workflow)
        self.assertIn("reports/four_mode_watchdog_dispatch.json", workflow)
        self.assertIn("reports/four_mode_dispatch_publications.json", workflow)
        self.assertIn("reports/four_mode_watchdog_artifact_decisions.json", workflow)
        self.assertIn("name: Confirm today's first-add archive presence in checked-out Git main\n        if: always()", workflow)

    def test_full_day_detects_early_failure_outside_last_twelve_artifacts(self):
        latest = datetime(2026, 11, 4, 20, 52,
                          tzinfo=timezone(timedelta(hours=9)))
        rows = [self.make_run(300 - i, (latest - timedelta(minutes=15*i)).isoformat())
                for i in range(48)]
        rows[47]["conclusion"] = "failure"
        rows.append(self.make_run(100, "2026-11-03T20:52:00+09:00"))
        result = audit_day("owner/repo", "20261104", "token",
                           lambda _: {"total_count": len(rows), "workflow_runs": rows})
        self.assertTrue(result["full_day_metadata_coverage"])
        self.assertEqual(result["same_day_scheduled_run_count"], 48)
        self.assertEqual(result["failed_run_ids"], [253])
        self.assertFalse(result["forecast_publication_verified"])

    def test_full_page_same_day_without_boundary_is_incomplete(self):
        rows = [self.make_run(200-i, "2026-11-04T07:07:00+09:00")
                for i in range(100)]
        result = audit_day("owner/repo", "20261104", "token",
                           lambda _: {"total_count": 101, "workflow_runs": rows})
        self.assertFalse(result["full_day_metadata_coverage"])

    def test_pending_and_prior_day_not_misclassified_as_failure(self):
        rows = [self.make_run(5, "2026-11-03T15:07:00Z", "in_progress", None),
                self.make_run(4, "2026-11-03T14:52:00Z", "completed", "failure")]
        result = audit_day("owner/repo", "20261104", "token",
                           lambda _: {"total_count": 2, "workflow_runs": rows})
        self.assertEqual(result["failed_run_ids"], [])
        self.assertEqual(result["pending_or_unknown_run_ids"], [5])
        self.assertTrue(result["full_day_metadata_coverage"])

    def test_all_pending_runs_cannot_be_credited_as_a_healthy_day(self):
        rows = [self.make_run(9, "2026-11-04T20:52:00+09:00",
                              status="in_progress", conclusion=None),
                self.make_run(8, "2026-11-04T20:37:00+09:00",
                              status="completed", conclusion=None),
                self.make_run(7, "2026-11-04T20:22:00+09:00",
                              status="completed", conclusion="success"),
                self.make_run(6, "2026-11-03T20:52:00+09:00")]
        result = audit_day("owner/repo", "20261104", "token",
                           lambda _: {"total_count": len(rows),
                                      "workflow_runs": rows})
        self.assertTrue(result["full_day_metadata_coverage"])
        self.assertEqual(result["failed_run_ids"], [])
        self.assertEqual(result["pending_or_unknown_run_ids"], [8, 9])
        from pathlib import Path
        source = Path("scripts/audit_four_mode_daily_schedule_runs.py").read_text(
            encoding="utf-8")
        self.assertIn('if result["pending_or_unknown_run_ids"]:', source)
        self.assertIn("day cannot be certified", source)

    def test_invalid_timestamp_and_unsorted_data_fail_closed(self):
        for rows in ([self.make_run(1, "not-a-date")],
                     [self.make_run(1, "2026-11-04T07:07:00"),
                      self.make_run(2, "2026-11-04T07:08:00+09:00")],
                     [self.make_run(1, "2026-11-04T07:07:00+09:00"),
                      self.make_run(2, "2026-11-04T07:08:00+09:00")]):
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    audit_day("owner/repo", "20261104", "token",
                              lambda _: {"total_count": len(rows),
                                         "workflow_runs": rows})

    def test_empty_history_has_no_success_claim(self):
        result = audit_day("owner/repo", "20261104", "token",
                           lambda _: {"total_count": 0, "workflow_runs": []})
        self.assertEqual(result["same_day_scheduled_run_count"], 0)
        self.assertEqual(result["failed_run_ids"], [])

    def test_nominal_schedule_due_is_time_scoped_and_never_delivery_proof(self):
        jst = timezone(timedelta(hours=9))
        cases = [
            (datetime(2026, 11, 8, 3, 3, tzinfo=jst), "20261108", 0),
            (datetime(2026, 11, 8, 7, 11, tzinfo=jst), "20261108", 0),
            (datetime(2026, 11, 8, 7, 12, tzinfo=jst), "20261108", 1),
            (datetime(2026, 11, 8, 8, 0, tzinfo=jst), "20261108", 4),
            (datetime(2026, 11, 8, 9, 20, tzinfo=jst), "20261108", 9),
            (datetime(2026, 11, 8, 20, 56, tzinfo=jst), "20261108", 55),
            (datetime(2026, 11, 8, 20, 57, tzinfo=jst), "20261108", 56),
            (datetime(2026, 11, 9, 3, 3, tzinfo=jst), "20261108", 56),
            (datetime(2026, 11, 8, 3, 3, tzinfo=jst), "20261107", 56),
        ]
        self.assertEqual(NOMINAL_DAILY_CAPTURE_SLOTS, 56)
        for now, day, expected in cases:
            with self.subTest(now=now.isoformat(), day=day):
                self.assertEqual(nominal_schedule_slots_due(day, now), expected)
        with self.assertRaises(ValueError):
            nominal_schedule_slots_due("20261108", datetime(2026, 11, 8))

    def test_successful_run_is_not_full_slot_coverage(self):
        jst = timezone(timedelta(hours=9))
        now = datetime(2026, 11, 8, 19, 15, tzinfo=jst)
        rows = [
            self.make_run(10, "2026-11-08T15:52:00+09:00"),
            self.make_run(9, "2026-11-08T10:22:00+09:00"),
            self.make_run(8, "2026-11-08T07:07:00+09:00"),
            self.make_run(7, "2026-11-07T20:52:00+09:00"),
        ]
        result = audit_day(
            "owner/repo", "20261108", "token",
            lambda _: {"total_count": len(rows), "workflow_runs": rows},
            as_of=now,
        )
        self.assertEqual(result["same_day_scheduled_run_count"], 3)
        self.assertEqual(result["failed_run_ids"], [])
        self.assertEqual(result["nominal_schedule_slots_due_as_of_audit"], 49)
        self.assertEqual(result["observed_runs_below_nominal_due_by"], 46)
        self.assertFalse(result["per_slot_schedule_delivery_verified"])
        self.assertFalse(result["forecast_publication_verified"])

    def test_delayed_overnight_run_is_only_observed_not_slot_proven(self):
        jst = timezone(timedelta(hours=9))
        rows = [
            self.make_run(30, "2026-11-08T03:03:00+09:00"),
            self.make_run(29, "2026-11-07T20:52:00+09:00"),
        ]
        result = audit_day(
            "owner/repo", "20261108", "token",
            lambda _: {"total_count": len(rows), "workflow_runs": rows},
            as_of=datetime(2026, 11, 8, 9, 20, tzinfo=jst),
        )
        # created_at=03:03 might be an extremely delayed previous-night slot;
        # it cannot certify any actual 07:07+ slot for the new JST day.
        self.assertEqual(result["same_day_scheduled_run_count"], 1)
        self.assertEqual(result["nominal_schedule_slots_due_as_of_audit"], 9)
        self.assertEqual(result["observed_runs_below_nominal_due_by"], 8)
        self.assertEqual(result["same_day_pre_first_nominal_run_ids"], [30])
        self.assertEqual(result["same_day_at_or_after_first_nominal_run_count"], 0)
        self.assertEqual(result["observed_after_first_runs_below_nominal_due_by"], 9)
        self.assertFalse(result["per_slot_schedule_delivery_verified"])
        self.assertFalse(result["forecast_publication_verified"])

    def test_api_history_coverage_does_not_certify_unfinished_day(self):
        jst = timezone(timedelta(hours=9))
        rows = [
            self.make_run(21, "2026-11-08T07:07:00+09:00"),
            self.make_run(20, "2026-11-07T20:52:00+09:00"),
        ]
        data = {"total_count": len(rows), "workflow_runs": rows}
        run = lambda at: audit_day("owner/repo", "20261108", "token",
                                   lambda _: data, as_of=at)
        for hour, minute, due, elapsed in (
                (9, 20, 9, False),
                (20, 57, 56, False),
        ):
            with self.subTest(hour=hour, minute=minute):
                result = run(datetime(2026, 11, 8, hour, minute, tzinfo=jst))
                # The API page contains all currently visible runs, but
                # could never prove all day-long schedule delivery.
                self.assertTrue(result["full_day_metadata_coverage"])
                self.assertEqual(result["nominal_schedule_slots_due_as_of_audit"], due)
                self.assertEqual(result["jst_calendar_day_elapsed_at_audit"], elapsed)
                self.assertFalse(result["full_calendar_day_schedule_delivery_verified"])
                self.assertFalse(result["forecast_publication_verified"])
                self.assertTrue(result["audit_as_of_jst"].startswith("2026-11-08T"))
        following = run(datetime(2026, 11, 9, 3, 3, tzinfo=jst))
        self.assertTrue(following["jst_calendar_day_elapsed_at_audit"])
        self.assertTrue(following["all_nominal_daily_slots_due_at_audit"])
        self.assertFalse(following["full_calendar_day_schedule_delivery_verified"])

    def test_calendar_day_elapsed_flag_rejects_naive_scan_time(self):
        rows = [self.make_run(1, "2026-11-08T07:07:00+09:00")]
        with self.assertRaises(ValueError):
            audit_day("owner/repo", "20261108", "token",
                      lambda _: {"total_count": 1, "workflow_runs": rows},
                      as_of=datetime(2026, 11, 8, 12, 0))

    def test_nominal_slot_count_matches_current_capture_cron(self):
        from pathlib import Path
        text = Path(".github/workflows/four-mode-prospective-capture.yml").read_text(
            encoding="utf-8")
        self.assertIn("cron: '7,22,37,52 22 * * *'", text)
        self.assertIn("cron: '7,22,37,52 23 * * *'", text)
        self.assertIn("cron: '7,22,37,52 0-11 * * *'", text)


    def test_overnight_schedule_cannot_silence_main_daily_zero_execution_gate(self):
        jst = timezone(timedelta(hours=9))
        rows = [
            self.make_run(30, "2026-11-08T03:03:00+09:00"),
            self.make_run(29, "2026-11-07T20:52:00+09:00"),
        ]
        report = audit_day(
            "owner/repo", "20261108", "token",
            lambda _: {"total_count": len(rows), "workflow_runs": rows},
            as_of=datetime(2026, 11, 8, 9, 20, tzinfo=jst))
        self.assertTrue(report["full_day_metadata_coverage"])
        self.assertEqual(report["same_day_scheduled_run_count"], 1)
        self.assertEqual(report["same_day_at_or_after_first_nominal_run_count"], 0)
        self.assertEqual(report["failed_run_ids"], [])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "daily.json"
            with (patch("scripts.audit_four_mode_daily_schedule_runs.audit_day",
                        return_value=report),
                  patch.dict(os.environ, {
                      "GITHUB_TOKEN": "synthetic-token",
                      "GITHUB_EVENT_NAME": "schedule",
                      "GITHUB_REF": "refs/heads/main",
                  }),
                  patch("sys.argv", ["audit", "--repo", "owner/repo",
                                     "--output", str(output),
                                     "--day-jst", "20261108"])):
                from scripts.audit_four_mode_daily_schedule_runs import main
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    with self.assertRaises(SystemExit) as raised:
                        main()
                self.assertEqual(raised.exception.code, 2)
                self.assertIn("pre-opening delayed runs cannot certify",
                              stdout.getvalue())
            disk = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(disk["same_day_scheduled_run_count"], 1)
            self.assertEqual(disk["same_day_at_or_after_first_nominal_run_count"], 0)

    def test_mixed_pre_opening_and_daytime_runs_do_not_rewrite_raw_counts(self):
        jst = timezone(timedelta(hours=9))
        rows = [
            self.make_run(32, "2026-11-08T08:10:00+09:00"),
            self.make_run(31, "2026-11-08T07:07:00+09:00"),
            self.make_run(30, "2026-11-08T03:03:00+09:00"),
            self.make_run(29, "2026-11-07T20:52:00+09:00"),
        ]
        report = audit_day(
            "owner/repo", "20261108", "token",
            lambda _: {"total_count": len(rows), "workflow_runs": rows},
            as_of=datetime(2026, 11, 8, 9, 20, tzinfo=jst))
        self.assertEqual(report["same_day_scheduled_run_count"], 3)
        self.assertEqual(report["same_day_pre_first_nominal_run_ids"], [30])
        self.assertEqual(report["same_day_at_or_after_first_nominal_run_count"], 2)
        self.assertEqual(report["observed_runs_below_nominal_due_by"], 6)
        self.assertEqual(report["observed_after_first_runs_below_nominal_due_by"], 7)
        self.assertFalse(report["full_calendar_day_schedule_delivery_verified"])
        self.assertFalse(report["forecast_publication_verified"])

    def test_pre_first_slot_boundary_does_not_count_as_daytime_capture(self):
        jst = timezone(timedelta(hours=9))
        rows = [
            self.make_run(13, "2026-11-08T07:07:00+09:00"),
            self.make_run(12, "2026-11-08T07:06:59+09:00"),
            self.make_run(11, "2026-11-07T20:52:00+09:00"),
        ]
        report = audit_day(
            "owner/repo", "20261108", "token",
            lambda _: {"total_count": 3, "workflow_runs": rows},
            as_of=datetime(2026, 11, 8, 9, 20, tzinfo=jst))
        self.assertEqual(report["same_day_pre_first_nominal_run_ids"], [12])
        self.assertEqual(report["same_day_at_or_after_first_nominal_run_count"], 1)
        self.assertFalse(report["per_slot_schedule_delivery_verified"])


    def test_future_schedule_run_rejected_before_it_can_count_as_liveness(self):
        jst = timezone(timedelta(hours=9))
        as_of = datetime(2026, 11, 8, 9, 20, tzinfo=jst)
        for future_stamp in (
            "2026-11-08T09:20:01+09:00",
            "2026-11-08T00:21:00Z",
            "2026-11-09T07:07:00+09:00",
        ):
            with self.subTest(future_stamp=future_stamp):
                rows = [
                    self.make_run(32, future_stamp),
                    self.make_run(31, "2026-11-08T08:22:00+09:00"),
                    self.make_run(30, "2026-11-07T20:52:00+09:00"),
                ]
                with self.assertRaisesRegex(
                    ValueError, "future_schedule_run_timestamp"
                ):
                    audit_day(
                        "owner/repo", "20261108", "token",
                        lambda _: {"total_count": len(rows), "workflow_runs": rows},
                        as_of=as_of,
                    )

    def test_schedule_at_exact_observation_time_is_not_future(self):
        jst = timezone(timedelta(hours=9))
        at = datetime(2026, 11, 8, 9, 20, tzinfo=jst)
        rows = [
            self.make_run(11, "2026-11-08T09:20:00+09:00"),
            self.make_run(10, "2026-11-07T20:52:00+09:00"),
        ]
        report = audit_day(
            "owner/repo", "20261108", "token",
            lambda _: {"total_count": len(rows), "workflow_runs": rows},
            as_of=at)
        self.assertEqual(report["same_day_at_or_after_first_nominal_run_count"], 1)
        self.assertFalse(report["per_slot_schedule_delivery_verified"])
        self.assertFalse(report["forecast_publication_verified"])

    def test_default_observation_time_is_taken_after_fetch(self):
        # A response generated during an API call is only valid if the audit
        # observation time is captured *after* the response arrives.
        jst = timezone(timedelta(hours=9))
        before_fetch = datetime(2026, 11, 8, 9, 0, tzinfo=jst)
        during_fetch = datetime(2026, 11, 8, 9, 15, tzinfo=jst)
        after_fetch = datetime(2026, 11, 8, 9, 30, tzinfo=jst)
        state = {"fetched": False}

        class FetchBoundaryClock(datetime):
            @classmethod
            def now(cls, tz=None):
                selected = after_fetch if state["fetched"] else before_fetch
                selected = selected.astimezone(tz) if tz else selected.replace(tzinfo=None)
                # Preserve the patched datetime subclass for the audit's
                # explicit isinstance(as_of, datetime) contract.
                return cls(
                    selected.year, selected.month, selected.day,
                    selected.hour, selected.minute, selected.second,
                    selected.microsecond, tzinfo=selected.tzinfo)

        def fetch(_):
            state["fetched"] = True
            return {"total_count": 1, "workflow_runs": [
                self.make_run(11, during_fetch.isoformat()),
            ]}

        with patch("scripts.audit_four_mode_daily_schedule_runs.datetime",
                   FetchBoundaryClock):
            report = audit_day("owner/repo", "20261108", "token", fetch)
        self.assertTrue(state["fetched"])
        self.assertEqual(
            datetime.fromisoformat(report["audit_as_of_jst"]), after_fetch)
        self.assertEqual(report["same_day_scheduled_run_count"], 1)
        self.assertEqual(report["same_day_at_or_after_first_nominal_run_count"], 1)
        self.assertFalse(report["forecast_publication_verified"])


    def test_late_only_night_run_cannot_satisfy_day_window_gate(self):
        # Reproduces the actual Nov 8 22:14 delayed successful run:
        # an execution is observable but cannot fill a daytime capture gap.
        jst = timezone(timedelta(hours=9))
        rows = [
            self.make_run(40, "2026-11-08T22:14:34+09:00"),
            self.make_run(39, "2026-11-07T20:52:00+09:00"),
        ]
        report = audit_day(
            "owner/repo", "20261108", "token",
            lambda _: {"total_count": len(rows), "workflow_runs": rows},
            as_of=datetime(2026, 11, 9, 3, 3, tzinfo=jst))
        self.assertEqual(report["same_day_scheduled_run_count"], 1)
        self.assertEqual(report["same_day_at_or_after_first_nominal_run_count"], 1)
        self.assertEqual(report["same_day_within_nominal_window_run_count"], 0)
        self.assertEqual(report["same_day_after_final_nominal_grace_run_ids"], [40])
        self.assertEqual(report["observed_within_window_below_nominal_due_by"], 56)
        self.assertFalse(report["per_slot_schedule_delivery_verified"])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "daily.json"
            with (patch("scripts.audit_four_mode_daily_schedule_runs.audit_day",
                        return_value=report),
                  patch.dict(os.environ, {
                      "GITHUB_TOKEN": "synthetic-token",
                      "GITHUB_EVENT_NAME": "schedule",
                      "GITHUB_REF": "refs/heads/main",
                  }),
                  patch("sys.argv", [
                      "audit", "--repo", "owner/repo",
                      "--output", str(output), "--day-jst", "20261108",
                  ])):
                from scripts.audit_four_mode_daily_schedule_runs import main
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    with self.assertRaises(SystemExit) as raised:
                        main()
            self.assertEqual(raised.exception.code, 2)
            self.assertIn("post-window late runs", stdout.getvalue())
            self.assertIn(
                "In-window schedule observations below nominal due by 56",
                stdout.getvalue())
            self.assertIn("numerical shortfall ONLY", stdout.getvalue())
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))[
                    "same_day_within_nominal_window_run_count"], 0)

    def test_final_slot_grace_boundary_and_one_second_late(self):
        jst = timezone(timedelta(hours=9))
        rows = [
            self.make_run(13, "2026-11-08T20:57:01+09:00"),
            self.make_run(12, "2026-11-08T20:57:00+09:00"),
            self.make_run(11, "2026-11-07T20:52:00+09:00"),
        ]
        report = audit_day(
            "owner/repo", "20261108", "token",
            lambda _: {"total_count": 3, "workflow_runs": rows},
            as_of=datetime(2026, 11, 8, 21, 10, tzinfo=jst))
        self.assertEqual(report["same_day_scheduled_run_count"], 2)
        self.assertEqual(report["same_day_within_nominal_window_run_count"], 1)
        self.assertEqual(report["same_day_after_final_nominal_grace_run_ids"], [13])
        self.assertEqual(report["observed_within_window_below_nominal_due_by"], 55)
        self.assertFalse(report["per_slot_schedule_delivery_verified"])

    def test_preopening_and_late_runs_preserved_without_daytime_inflation(self):
        jst = timezone(timedelta(hours=9))
        rows = [
            self.make_run(16, "2026-11-08T22:14:34+09:00"),
            self.make_run(15, "2026-11-08T10:22:00+09:00"),
            self.make_run(14, "2026-11-08T03:03:00+09:00"),
            self.make_run(13, "2026-11-07T20:52:00+09:00"),
        ]
        report = audit_day(
            "owner/repo", "20261108", "token",
            lambda _: {"total_count": 4, "workflow_runs": rows},
            as_of=datetime(2026, 11, 9, 3, 3, tzinfo=jst))
        self.assertEqual(report["same_day_scheduled_run_count"], 3)
        self.assertEqual(report["same_day_pre_first_nominal_run_ids"], [14])
        self.assertEqual(report["same_day_at_or_after_first_nominal_run_count"], 2)
        self.assertEqual(report["same_day_after_final_nominal_grace_run_ids"], [16])
        self.assertEqual(report["same_day_within_nominal_window_run_count"], 1)
        self.assertEqual(report["observed_runs_below_nominal_due_by"], 53)
        self.assertEqual(report["observed_after_first_runs_below_nominal_due_by"], 54)
        self.assertEqual(report["observed_within_window_below_nominal_due_by"], 55)
        self.assertFalse(report["full_calendar_day_schedule_delivery_verified"])
        self.assertFalse(report["forecast_publication_verified"])



    def test_latest_daytime_observation_silence_is_reported_without_slot_proof(self):
        jst = timezone(timedelta(hours=9))
        rows = [
            self.make_run(32, "2026-11-09T15:10:20+09:00"),
            self.make_run(31, "2026-11-09T10:37:58+09:00"),
            self.make_run(30, "2026-11-08T20:52:00+09:00"),
        ]
        report = audit_day(
            "owner/repo", "20261109", "token",
            lambda _: {"total_count": 3, "workflow_runs": rows},
            as_of=datetime(2026, 11, 9, 16, 53, 2, tzinfo=jst))
        self.assertEqual(report["same_day_within_nominal_window_run_count"], 2)
        self.assertEqual(report["latest_in_window_run_created_at_jst"],
                         "2026-11-09T15:10:20+09:00")
        self.assertEqual(report["minutes_since_latest_in_window_observation"],
                         102.7)
        self.assertEqual(report["in_window_silence_observation_end_jst"],
                         "2026-11-09T16:53:02+09:00")
        self.assertFalse(report["per_slot_schedule_delivery_verified"])
        self.assertFalse(report["forecast_publication_verified"])

    def test_overnight_scan_caps_daytime_silence_at_final_grace(self):
        jst = timezone(timedelta(hours=9))
        rows = [self.make_run(9, "2026-11-09T15:10:20+09:00")]
        fetch = lambda _: {"total_count": 1, "workflow_runs": rows}
        first = audit_day(
            "owner/repo", "20261109", "token", fetch,
            as_of=datetime(2026, 11, 9, 22, 20, tzinfo=jst))
        later = audit_day(
            "owner/repo", "20261109", "token", fetch,
            as_of=datetime(2026, 11, 10, 9, 20, tzinfo=jst))
        for result in (first, later):
            self.assertEqual(
                result["minutes_since_latest_in_window_observation"], 346.67)
            self.assertEqual(
                result["in_window_silence_observation_end_jst"],
                "2026-11-09T20:57:00+09:00")
            self.assertFalse(result["full_calendar_day_schedule_delivery_verified"])

    def test_only_off_window_runs_yield_unknown_not_zero_silence(self):
        jst = timezone(timedelta(hours=9))
        rows = [
            self.make_run(9, "2026-11-09T22:14:34+09:00"),
            self.make_run(8, "2026-11-09T03:03:00+09:00"),
            self.make_run(7, "2026-11-08T20:52:00+09:00"),
        ]
        result = audit_day(
            "owner/repo", "20261109", "token",
            lambda _: {"total_count": len(rows), "workflow_runs": rows},
            as_of=datetime(2026, 11, 10, 3, 3, tzinfo=jst))
        self.assertEqual(result["same_day_scheduled_run_count"], 2)
        self.assertEqual(result["same_day_within_nominal_window_run_count"], 0)
        self.assertIsNone(result["latest_in_window_run_created_at_jst"])
        self.assertIsNone(result["minutes_since_latest_in_window_observation"])
        self.assertFalse(result["per_slot_schedule_delivery_verified"])



if __name__ == "__main__":
    unittest.main()
