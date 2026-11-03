import unittest
from scripts.audit_four_mode_daily_schedule_runs import audit_day


class DailyScheduleRunMetadataTest(unittest.TestCase):
    @staticmethod
    def run(run_id, timestamp, status="completed", conclusion="success"):
        return {"event": "schedule", "id": run_id, "created_at": timestamp,
                "status": status, "conclusion": conclusion}

    def test_full_day_detects_early_failure_outside_last_twelve_artifacts(self):
        rows = [
            self.run(300 - i, f"2026-11-04T{19 - i // 4:02d}:{(i % 4)*15:02d}:00+09:00")
            for i in range(48)
        ]
        rows[47]["conclusion"] = "failure"
        rows.append(self.run(100, "2026-11-03T20:52:00+09:00"))
        result = audit_day("owner/repo", "20261104", "token",
                           lambda _: {"total_count": len(rows), "workflow_runs": rows})
        self.assertTrue(result["full_day_metadata_coverage"])
        self.assertEqual(result["same_day_scheduled_run_count"], 48)
        self.assertEqual(result["failed_run_ids"], [253])
        self.assertFalse(result["forecast_publication_verified"])

    def test_full_page_same_day_without_boundary_is_incomplete(self):
        rows = [self.run(200-i, "2026-11-04T07:07:00+09:00")
                for i in range(100)]
        result = audit_day("owner/repo", "20261104", "token",
                           lambda _: {"total_count": 101, "workflow_runs": rows})
        self.assertFalse(result["full_day_metadata_coverage"])

    def test_pending_and_prior_day_not_misclassified_as_failure(self):
        rows = [self.run(5, "2026-11-03T15:07:00Z", "in_progress", None),
                self.run(4, "2026-11-03T14:52:00Z", "completed", "failure")]
        result = audit_day("owner/repo", "20261104", "token",
                           lambda _: {"total_count": 2, "workflow_runs": rows})
        self.assertEqual(result["failed_run_ids"], [])
        self.assertEqual(result["pending_or_unknown_run_ids"], [5])
        self.assertTrue(result["full_day_metadata_coverage"])

    def test_invalid_timestamp_and_unsorted_data_fail_closed(self):
        for rows in ([self.run(1, "not-a-date")],
                     [self.run(1, "2026-11-04T07:07:00"),
                      self.run(2, "2026-11-04T07:08:00+09:00")],
                     [self.run(1, "2026-11-04T07:07:00+09:00"),
                      self.run(2, "2026-11-04T07:08:00+09:00")]):
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


if __name__ == "__main__":
    unittest.main()
