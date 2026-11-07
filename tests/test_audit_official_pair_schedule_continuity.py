import unittest
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from scripts.audit_official_pair_schedule_continuity import (
    WORKFLOW_PATH, inventory,
)

REPO = "sample/repo"
DAY = "20261107"
END = datetime(2026, 11, 8, 0, 0, tzinfo=timezone.utc)


def run(rid, when, *, event="schedule", path=WORKFLOW_PATH,
        conclusion="success", status="completed"):
    return {"id": rid, "event": event, "path": path,
            "created_at": when, "status": status, "conclusion": conclusion}


def fetch_pages(pages, total):
    def fake(url):
        query = parse_qs(urlparse(url).query)
        assert query["event"] == ["schedule"]
        assert query["created"] == ["2026-11-07"]
        assert query["per_page"] == ["100"]
        return {"total_count": total,
                "workflow_runs": pages.get(int(query["page"][0]), [])}
    return fake


class OfficialPairContinuityAuditTests(unittest.TestCase):
    def audit(self, rows, *, at=END):
        return inventory(REPO, DAY, "unit-test-token",
                         fetch=fetch_pages({1: rows}, len(rows)), as_of=at)

    def test_actual_nov7_two_runs_in_156_nominal_slots(self):
        rows = [
            run(42342115412, "2026-11-07T05:17:49Z", conclusion="failure"),
            run(42369814345, "2026-11-07T11:49:44Z"),
            run(9, "2026-11-07T11:59:00Z", path=".github/workflows/other.yml"),
        ]
        result = self.audit(rows)
        self.assertEqual(result["expected_slots_full_day"], 156)
        self.assertEqual(result["elapsed_nominal_slots_at_snapshot"], 156)
        self.assertEqual(result["observed_official_pair_schedule_runs"], 2)
        self.assertEqual(result["nominal_invocation_count_deficit"], 154)
        self.assertEqual(result["observed_to_elapsed_slot_pct"], 1.28)
        self.assertEqual((result["run_failure"], result["run_success"]), (1, 1))
        self.assertFalse(result["raw_official_source_receipts_verified"])
        self.assertFalse(result["full_t12_source_certified"])
        self.assertFalse(result["schedule_slot_identity_verified"])

    def test_pr_manual_and_workflow_run_cannot_become_scheduled_evidence(self):
        with self.assertRaisesRegex(ValueError, "non-schedule"):
            self.audit([run(1, "2026-11-07T10:00:00Z", event="pull_request")])
        with self.assertRaisesRegex(ValueError, "non-schedule"):
            self.audit([run(1, "2026-11-07T10:00:00Z", event="workflow_run")])

    def test_zero_runs_reports_gap_but_not_source_failures(self):
        report = self.audit([])
        self.assertEqual(report["observed_official_pair_schedule_runs"], 0)
        self.assertEqual(report["nominal_invocation_count_deficit"], 156)
        self.assertFalse(report["missing_trigger_root_cause_verified"])
        self.assertFalse(report["forecast_usable"])

    def test_partial_day_does_not_count_future_slots(self):
        at = datetime(2026, 11, 7, 6, 1, tzinfo=timezone.utc)
        report = self.audit([run(1, "2026-11-07T05:17:49Z")], at=at)
        self.assertEqual(report["elapsed_nominal_slots_at_snapshot"], 73)
        self.assertEqual(report["future_nominal_slots"], 83)
        self.assertEqual(report["nominal_invocation_count_deficit"], 72)

    def test_before_day_not_misreported_as_full_day_failure(self):
        report = self.audit([], at=datetime(2026, 11, 6, 23, 59, tzinfo=timezone.utc))
        self.assertEqual(report["elapsed_nominal_slots_at_snapshot"], 0)
        self.assertIsNone(report["observed_to_elapsed_slot_pct"])

    def test_complete_second_page_is_counted(self):
        irrelevant = [run(i, "2026-11-07T04:00:00Z",
                          path=".github/workflows/other.yml") for i in range(1, 101)]
        target = run(101, "2026-11-07T05:17:49Z")
        report = inventory(REPO, DAY, "test",
                           fetch=fetch_pages({1: irrelevant, 2: [target]}, 101), as_of=END)
        self.assertEqual(report["total_repository_schedule_runs"], 101)
        self.assertEqual(report["observed_official_pair_schedule_runs"], 1)

    def test_incomplete_or_changing_pagination_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "pagination"):
            inventory(REPO, DAY, "test",
                      fetch=fetch_pages({1: [run(1, "2026-11-07T04:00:00Z")]}, 101),
                      as_of=END)
        full = [run(i, "2026-11-07T04:00:00Z") for i in range(1, 101)]
        def mismatch(url):
            page = int(parse_qs(urlparse(url).query)["page"][0])
            return {"total_count": 101 if page == 1 else 102,
                    "workflow_runs": full if page == 1 else [run(101, "2026-11-07T05:00:00Z")]}
        with self.assertRaisesRegex(ValueError, "pagination"):
            inventory(REPO, DAY, "test", fetch=mismatch, as_of=END)

    def test_duplicate_or_unscoped_ids_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.audit([run(1, "2026-11-07T02:00:00Z"),
                        run(1, "2026-11-07T03:00:00Z")])
        with self.assertRaisesRegex(ValueError, "run ID"):
            self.audit([run(True, "2026-11-07T03:00:00Z")])

    def test_invalid_timestamps_and_out_of_day_fail_closed(self):
        for stamp in ["wrong", "2026-11-07T09:00:00", "2026-11-06T23:00:00Z"]:
            with self.subTest(stamp=stamp):
                with self.assertRaises(ValueError):
                    self.audit([run(1, stamp)])

    def test_green_run_does_not_prove_raw_input_or_formal_forecast(self):
        report = self.audit([run(1, "2026-11-07T11:49:44Z")])
        self.assertEqual(report["run_success"], 1)
        self.assertFalse(report["full_t12_source_certified"])
        self.assertFalse(report["forecast_usable"])

    def test_invalid_date_repo_and_token_fail_closed(self):
        for repo, day, token in [
            ("bad-repo", DAY, "test"),
            (REPO, "20261131", "test"),
            (REPO, DAY, ""),
        ]:
            with self.assertRaises(ValueError):
                inventory(repo, day, token,
                          fetch=fetch_pages({1: []}, 0), as_of=END)


if __name__ == "__main__":
    unittest.main()
