"""Synthetic GitHub event metadata, never official original or model data."""
import unittest
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from scripts.audit_t12_cross_workflow_schedule import compare, WORKFLOWS

REPO = "ikst2512-eng/boat-edge-clean"
NOW = datetime(2026, 11, 10, 1, tzinfo=timezone.utc)
START = "20261106"
END = "20261108"


def example(date, *, id_start=100):
    entries = []
    specs = (
        ("official_pair", 5, "success"),
        ("official_pair", 17, "success"),
        ("entry_t12_control", 6, "success"),
        ("entry_t12_control", 13, "failure"),
        ("clean_capture_control", 3, "success"),
        ("clean_capture_control", 6, "success"),
        ("clean_capture_control", 17, "success"),
    )
    for i, (name, hour, verdict) in enumerate(specs):
        entries.append({
            "id": id_start+i, "event": "schedule",
            "path": WORKFLOWS[name]["path"],
            "created_at": f"{date}T{hour:02d}:01:12Z",
            "conclusion": verdict, "status": "completed",
        })
    entries.append({
        "id": id_start+90, "event": "schedule",
        "path": ".github/workflows/unrelated.yml",
        "created_at": f"{date}T05:04:21Z",
        "conclusion": "success",
    })
    return entries


def mock_fetch(*, override=None, days=None, failure=None):
    if days is None:
        days = {
            "2026-11-06": example("2026-11-06", id_start=600),
            "2026-11-07": example("2026-11-07", id_start=700),
            "2026-11-08": example("2026-11-08", id_start=800),
        }
    def fetch(url):
        parsed = urlsplit(url)
        if parsed.path != f"/repos/{REPO}/actions/runs":
            raise AssertionError("unexpected GitHub endpoint")
        params = parse_qs(parsed.query)
        if params.get("event") != ["schedule"] or params.get("per_page") != ["100"]:
            raise AssertionError("audit must use schedule-only pagination")
        if failure is not None:
            raise HTTPError(url, 403, "GitHub denied API", {}, None)
        date = params["created"][0]
        if date not in days:
            raise AssertionError("non-requested day")
        if override is not None:
            return override(date, int(params["page"][0]))
        if params["page"] != ["1"]:
            raise AssertionError("unexpected second page")
        return {"total_count": len(days[date]), "workflow_runs": days[date]}
    return fetch


class CrossWorkflowT12ScheduleControl(unittest.TestCase):
    def test_all_three_controls_have_distinct_nominal_cadence(self):
        report = compare(REPO, START, END, fetch=mock_fetch(), as_of=NOW)
        self.assertEqual(report["schema"],
                         "T12_CROSS_WORKFLOW_SCHEDULE_CONTROL_V1")
        official = report["controls"]["official_pair"]
        entry = report["controls"]["entry_t12_control"]
        clean = report["controls"]["clean_capture_control"]
        self.assertEqual([x["nominal_common_window_slots"]
                          for x in (official, entry, clean)], [468, 468, 156])
        self.assertEqual([x["created_in_common_hours"]
                          for x in (official, entry, clean)], [3, 3, 6])
        self.assertEqual([x["created_outside_common_hours"]
                          for x in (official, entry, clean)], [3, 3, 3])
        self.assertEqual([x["creation_hour_coverage_pct"]
                          for x in (official, entry, clean)], [0.64, 0.64, 3.85])
        self.assertEqual(len(report["daily"]), 3)
        self.assertEqual(sum(x["total_repository_schedule_events"]
                             for x in report["daily"]), 24)

    def test_no_root_cause_or_formal_source_certificates_from_green_runs(self):
        result = compare(REPO, START, END, fetch=mock_fetch(), as_of=NOW)
        for key in ("github_root_cause_verified",
                    "cross_workflow_scheduler_failure_proved",
                    "absent_run_http_failures_proved",
                    "raw_official_source_bytes_replayed",
                    "formal", "accuracy_scoring_allowed", "t12_eligible"):
            self.assertIs(result[key], False)
        self.assertIsNone(result["formal_accuracy_denominator"])
        self.assertEqual(result["new_formal_certifications"], 0)
        self.assertTrue(result["observed_run_creation_cannot_prove_scheduled_slot"])
        for control in result["controls"].values():
            self.assertFalse(control["scheduled_slot_identity_verified"])
            self.assertFalse(control["source_http_attempts_verified"])
            self.assertFalse(control["formal"])

    def test_off_hour_runs_cannot_fill_common_hour_count(self):
        xs = example("2026-11-06")
        xs[0]["created_at"] = "2026-11-06T20:00:00Z"
        result = compare(REPO, START, START,
                         fetch=mock_fetch(days={"2026-11-06": xs}), as_of=NOW)
        target = result["controls"]["official_pair"]
        self.assertEqual(target["created_in_common_hours"], 0)
        self.assertEqual(target["created_outside_common_hours"], 2)
        self.assertEqual(target["creation_hour_coverage_pct"], 0.0)
        self.assertEqual(target["nominal_creation_count_shortfall"], 156)

    def test_malformed_total_count_or_missing_pagination_is_rejected(self):
        for payload in (
            {"total_count": 101, "workflow_runs": example("2026-11-06")},
            {"total_count": True, "workflow_runs": []},
            {"total_count": 3, "workflow_runs": []},
            {"workflow_runs": []},
            {"total_count": 2, "workflow_runs": {}},
        ):
            def override(date, page):
                return payload
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                compare(REPO, START, START, fetch=mock_fetch(override=override),
                        as_of=NOW)

    def test_duplicate_run_id_even_on_other_workflow_is_rejected(self):
        rows = example("2026-11-06")
        rows[-1]["id"] = rows[0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            compare(REPO, START, START,
                    fetch=mock_fetch(days={"2026-11-06": rows}), as_of=NOW)

    def test_non_schedule_run_inside_schedule_only_response_is_rejected(self):
        rows = example("2026-11-06")
        rows[0]["event"] = "workflow_dispatch"
        with self.assertRaisesRegex(ValueError, "non-schedule"):
            compare(REPO, START, START,
                    fetch=mock_fetch(days={"2026-11-06": rows}), as_of=NOW)

    def test_cross_date_future_or_timezone_mismatch_is_rejected(self):
        for value in ("2026-11-07T06:10:00Z",
                      "2026-11-06T06:10:00+09:00",
                      "2026-11-06T11:00:00"):
            rows = example("2026-11-06")
            rows[0]["created_at"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                compare(REPO, START, START,
                        fetch=mock_fetch(days={"2026-11-06": rows}), as_of=NOW)

    def test_end_day_must_finish_its_nominal_1255_utc_slot(self):
        with self.assertRaisesRegex(ValueError, "unfinished"):
            compare(REPO, START, END, fetch=mock_fetch(),
                    as_of=datetime(2026, 11, 8, 12, 54, tzinfo=timezone.utc))

    def test_date_or_historical_cron_revision_or_broad_range_rejected(self):
        for start, end in (("20261105", "20261106"),
                           ("20261106", "20261115"),
                           ("20261108", "20261107"),
                           ("20260230", END),
                           (START, "20261301"),
                           (START, "20261108/../20261109")):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                compare(REPO, start, end, fetch=mock_fetch(), as_of=NOW)

    def test_invalid_repo_and_absent_auth_rejected(self):
        for repo in ("bad", "owner/repo/branch", "../repo"):
            with self.subTest(repo=repo), self.assertRaises(ValueError):
                compare(repo, START, END, fetch=mock_fetch(), as_of=NOW)
        with self.assertRaisesRegex(ValueError, "authenticated"):
            compare(REPO, START, END, token=None, as_of=NOW)

    def test_github_denied_api_fails_closed_never_returns_zero_events(self):
        with self.assertRaises(HTTPError):
            compare(REPO, START, END,
                    fetch=mock_fetch(failure=True), as_of=NOW)

    def test_actual_snapshot_has_independent_three_workflow_run_ids(self):
        result = compare(REPO, START, END, fetch=mock_fetch(), as_of=NOW)
        all_ids = []
        for row in result["controls"].values():
            all_ids += row["in_hours_run_ids"] + row["outside_hours_run_ids"]
        self.assertEqual(len(all_ids), len(set(all_ids)))
        self.assertEqual(len(all_ids), 21)


if __name__ == "__main__":
    unittest.main()
