import unittest
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
        self.assertFalse(result["per_slot_schedule_delivery_verified"])
        self.assertFalse(result["forecast_publication_verified"])

    def test_nominal_slot_count_matches_current_capture_cron(self):
        from pathlib import Path
        text = Path(".github/workflows/four-mode-prospective-capture.yml").read_text(
            encoding="utf-8")
        self.assertIn("cron: '7,22,37,52 22 * * *'", text)
        self.assertIn("cron: '7,22,37,52 23 * * *'", text)
        self.assertIn("cron: '7,22,37,52 0-11 * * *'", text)


if __name__ == "__main__":
    unittest.main()
