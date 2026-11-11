"""Fail-closed independent GitHub Actions metadata inventory tests."""
import copy
import unittest
from urllib.parse import parse_qs, urlparse

from four_mode_top1_capture_run_inventory import (
    EVENTS, NAME, WORKFLOW, fetch_day, summarize,
)

DAY = "2026-11-08"


def run(run_id, event="schedule", name=NAME, attempt=1):
    return {
        "id": run_id, "event": event, "name": name,
        "path": WORKFLOW if name == NAME else ".github/workflows/unrelated.yml",
        "head_branch": "main",
        "created_at": "2026-11-08T01:17:02Z",
        "run_attempt": attempt, "status": "completed", "conclusion": "success",
        "head_sha": "a"*40,
    }


def snap(event, rows, page=1, total=None, day=DAY):
    return {
        "utc_day": day, "event": event, "page": page,
        "total_count": len(rows) if total is None else total,
        "workflow_runs": rows,
    }


def valid():
    return [
        snap("schedule", [run(11), run(12, name="Unrelated job")]),
        snap("workflow_dispatch", [run(13, event="workflow_dispatch")]),
    ]


class RunInventoryTests(unittest.TestCase):
    def test_two_event_enumeration_is_reference_not_formal(self):
        report = summarize(valid(), DAY)
        self.assertEqual(report["observed_capture_runs"], 2)
        self.assertEqual([x["run_id"] for x in report["capture_runs"]], [11,13])
        self.assertFalse(report["complete_expected_schedule_inventory_verified"])
        self.assertFalse(report["complete_job_attempts_verified"])
        self.assertFalse(report["candidate_first_remote_receipt_verified"])
        self.assertFalse(report["model_promotion_allowed"])
        self.assertFalse(report["formal"])

    def test_missing_event_page_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "missing_github_api_event_pages"):
            summarize(valid()[:1], DAY)

    def test_truncated_page_and_inconsistent_total_fail(self):
        for mutation in ("wrong_total", "truncated", "duplicate_page", "wrong_day"):
            with self.subTest(mutation=mutation):
                rows = valid()
                if mutation == "wrong_total":
                    rows[0]["total_count"] = 3
                elif mutation == "truncated":
                    rows[1]["workflow_runs"].clear()
                elif mutation == "duplicate_page":
                    rows.append(copy.deepcopy(rows[0]))
                else:
                    rows[0]["utc_day"] = "2026-11-07"
                with self.assertRaises(ValueError):
                    summarize(rows, DAY)

    def test_forged_run_metadata_fails_closed(self):
        for field, value in (
            ("path", ".github/workflows/malicious.yml"),
            ("head_branch", "feature/preview"),
            ("created_at", "2026-11-09T00:17:00Z"),
            ("event", "pull_request"),
            ("run_attempt", 0),
        ):
            with self.subTest(field=field):
                rows = valid()
                rows[0]["workflow_runs"][0][field] = value
                with self.assertRaises(ValueError):
                    summarize(rows, DAY)

    def test_renamed_capture_workflow_is_not_silently_dropped(self):
        rows=valid()
        rows[0]["workflow_runs"][0]["name"]="Four-mode renamed unexpectedly"
        with self.assertRaisesRegex(ValueError, "wrong_capture_workflow_identity"):
            summarize(rows, DAY)

    def test_duplicate_run_in_separate_event_is_rejected(self):
        rows = valid()
        rows[1]["workflow_runs"][0]["id"] = 11
        with self.assertRaisesRegex(ValueError, "duplicate_or_invalid_github_run_id"):
            summarize(rows, DAY)

    def test_rerun_attempt_requires_separate_check(self):
        rows = valid()
        rows[0]["workflow_runs"][0]["run_attempt"] = 2
        r = summarize(rows, DAY)
        self.assertTrue(r["capture_runs"][0]["needs_all_attempts_audit"])
        self.assertFalse(r["complete_job_attempts_verified"])

    def test_valid_many_pages_exact_count(self):
        first = [run(i, name="Other workflow") for i in range(1, 101)]
        final = [run(101), run(102)]
        rows = [
            snap("schedule", first, page=1, total=102),
            snap("schedule", final, page=2, total=102),
            snap("workflow_dispatch", []),
        ]
        r = summarize(rows, DAY)
        self.assertEqual(r["all_workflow_runs_listed_by_event"]["schedule"], 102)
        self.assertEqual(r["observed_capture_runs"], 2)
        rows[1]["workflow_runs"].pop()
        with self.assertRaises(ValueError):
            summarize(rows, DAY)

    def test_fetch_day_paginates_without_trusting_partial_data(self):
        seen = []
        def reader(url):
            args = parse_qs(urlparse(url).query)
            event = args["event"][0]
            day = args["created"][0]
            page = int(args["page"][0])
            seen.append((event, day, page))
            if event == "schedule":
                count = 101
                rows = [run(i) for i in range(1, 101)] if page == 1 else [run(101)]
            else:
                count = 0
                rows = []
            return {"total_count":count, "workflow_runs":rows}
        pages = fetch_day(DAY,reader=reader)
        self.assertEqual(len(pages),3)
        self.assertEqual(seen,[("schedule",DAY,1),("schedule",DAY,2),
                               ("workflow_dispatch",DAY,1)])
        self.assertEqual(summarize(pages,DAY)["observed_capture_runs"],101)

    def test_fetch_rejects_changing_total_count(self):
        def reader(url):
            args = parse_qs(urlparse(url).query)
            event=args["event"][0]
            page=int(args["page"][0])
            if event=="schedule":
                return {"total_count":101 if page==1 else 100,
                        "workflow_runs":[run(i) for i in range(1,101)] if page==1 else [run(101)]}
            return {"total_count":0,"workflow_runs":[]}
        with self.assertRaisesRegex(ValueError, "unstable_github_api_pagination"):
            fetch_day(DAY,reader=reader)


if __name__ == "__main__":
    unittest.main()
