"""Offline fail-closed tests of reported GitHub job/attempt pagination."""
import copy
import unittest
from urllib.parse import parse_qs, urlparse

from four_mode_capture_attempt_inventory import (
    STEP_FREEZE, STEP_LEDGER, STEP_ORIGINAL, fetch_job_pages, review,
)

DAY = "2026-11-09"


def runs(attempts=1):
    return {
        "schema": "FOUR_MODE_TOP1_GITHUB_RUN_METADATA_INVENTORY_V1",
        "utc_day": DAY, "formal": False,
        "complete_expected_schedule_inventory_verified": False,
        "capture_runs": [
            {"run_id": 42, "attempts_reported": attempts, "event": "workflow_dispatch",
             "head_sha": "a"*40},
        ],
    }


def step(name, conclusion="success"):
    return {"name": name, "status": "completed", "conclusion": conclusion}


def job(job_id, name, attempt, stages=None, status="completed", conclusion="success"):
    return {
        "id": job_id, "run_id": 42, "run_attempt": attempt,
        "name": name, "status": status, "conclusion": conclusion,
        "steps": ([step("Set up job")] + list(stages or []))
                 if conclusion != "skipped" else None,
    }


def page(attempt=1, candidates=False):
    stages = [step(STEP_ORIGINAL)]
    if candidates:
        stages += [step(STEP_FREEZE), step(STEP_LEDGER)]
    return [{
        "run_id": 42, "attempt": attempt, "page": 1, "total_count": 2,
        "jobs": [job(100 + attempt*10, "capture", attempt, stages),
                 job(101 + attempt*10, "test", attempt)],
    }]


class JobAttemptInventoryTests(unittest.TestCase):
    def test_realistic_manual_capture_without_candidate_stages(self):
        r = review(DAY, runs(), page())
        self.assertEqual(r["observed_capture_runs"], 1)
        self.assertEqual(r["observed_run_attempts_with_complete_job_metadata"], 1)
        self.assertEqual(r["attempts_with_candidate_stage_pair"], 0)
        self.assertTrue(r["attempts"][0]["original_capture_step_present"])
        self.assertFalse(r["candidate_artifact_publication_verified"])
        self.assertFalse(r["complete_expected_schedule_inventory_verified"])
        self.assertEqual(r["admitted_prospective_pairs"], 0)
        self.assertFalse(r["formal"])

    def test_even_successful_candidate_steps_cannot_be_formal(self):
        r = review(DAY, runs(), page(candidates=True))
        self.assertEqual(r["candidate_stages_succeeded_not_publication"], 1)
        self.assertFalse(r["candidate_independent_first_remote_receipt_verified"])
        self.assertFalse(r["official_three_original_t12_verified"])
        self.assertFalse(r["model_promotion_allowed"])

    def test_rerun_checks_each_attempt(self):
        all_pages = page(attempt=1) + page(attempt=2, candidates=True)
        r = review(DAY, runs(attempts=2), all_pages)
        self.assertEqual(r["observed_run_attempts_with_complete_job_metadata"], 2)
        self.assertEqual(r["attempts_with_candidate_stage_pair"], 1)
        self.assertFalse(r["complete_expected_schedule_inventory_verified"])
        with self.assertRaisesRegex(ValueError, "missing_observed_job_attempt"):
            review(DAY, runs(attempts=2), page(attempt=2))

    def test_missing_duplicate_extra_page_rejected(self):
        for mutation in ("missing", "duplicate", "unknown", "short", "wrong_total"):
            with self.subTest(mutation=mutation):
                p = page()
                if mutation == "missing":
                    p = []
                elif mutation == "duplicate":
                    p += copy.deepcopy(p)
                elif mutation == "unknown":
                    p[0]["run_id"] = 99
                elif mutation == "short":
                    p[0]["jobs"].pop()
                else:
                    p[0]["total_count"] = 3
                with self.assertRaises(ValueError):
                    review(DAY, runs(), p)

    def test_wrong_job_identity_and_duplicate_job_rejected(self):
        for mutation in ("run_id", "attempt", "duplicate", "job_type", "status"):
            with self.subTest(mutation=mutation):
                p = page()
                j = p[0]["jobs"][0]
                if mutation == "run_id":
                    j["run_id"] = 99
                elif mutation == "attempt":
                    j["run_attempt"] = 2
                elif mutation == "duplicate":
                    p[0]["jobs"][1]["id"] = j["id"]
                elif mutation == "job_type":
                    j["name"] = "deploy"
                else:
                    j["status"] = "not_a_job_status"
                with self.assertRaises(ValueError):
                    review(DAY, runs(), p)

    def test_partial_or_duplicate_candidate_stage_rejected(self):
        p = page(candidates=True)
        p[0]["jobs"][0]["steps"] = [
            s for s in p[0]["jobs"][0]["steps"]
            if s["name"] != STEP_LEDGER]
        with self.assertRaisesRegex(ValueError, "partial_candidate"):
            review(DAY, runs(), p)
        p = page(candidates=True)
        p[0]["jobs"][0]["steps"].append(step(STEP_FREEZE))
        with self.assertRaisesRegex(ValueError, "duplicate_pipeline"):
            review(DAY, runs(), p)

    def test_misplaced_candidate_stage_and_missing_finished_steps(self):
        p = page(candidates=True)
        p[0]["jobs"][1]["steps"].append(step(STEP_FREEZE))
        with self.assertRaisesRegex(ValueError, "non_capture"):
            review(DAY, runs(), p)
        p = page()
        p[0]["jobs"][0]["steps"] = None
        with self.assertRaisesRegex(ValueError, "completed_job_missing"):
            review(DAY, runs(), p)

    def test_untrusted_run_roster_rejected(self):
        bad = runs()
        bad["complete_expected_schedule_inventory_verified"] = True
        with self.assertRaisesRegex(ValueError, "untrusted"):
            review(DAY, bad, page())
        bad = runs()
        bad["capture_runs"][0]["head_sha"] = "HEAD"
        with self.assertRaisesRegex(ValueError, "invalid_capture_run_identity"):
            review(DAY, bad, page())
        bad = runs()
        bad["capture_runs"][0]["run_id"] = "42"
        with self.assertRaisesRegex(ValueError, "invalid_capture_run_identity"):
            review(DAY, bad, page())

    def test_skipped_capture_distinguished_from_successful_test(self):
        p = page()
        p[0]["jobs"][0] = job(110, "capture", 1, status="completed",
                              conclusion="skipped")
        r = review(DAY, runs(), p)
        self.assertFalse(r["attempts"][0]["original_capture_step_present"])
        self.assertEqual(r["attempts"][0]["job_conclusions"]["capture"], "skipped")
        self.assertFalse(r["formal"])

    def test_fetch_job_pages_uses_attempt_specific_url_and_exact_counts(self):
        seen = []
        def reader(url):
            q = parse_qs(urlparse(url).query)
            page_n = int(q["page"][0])
            seen.append((urlparse(url).path, page_n))
            n = 101
            jobs = [job(i, "test", 2) for i in range(1,101)] if page_n == 1 \
                else [job(101, "capture", 2, [step(STEP_ORIGINAL)])]
            return {"total_count": n, "jobs": jobs}
        p = fetch_job_pages(42, 2, reader=reader)
        self.assertEqual(len(p), 2)
        self.assertEqual(seen, [
            ("/repos/ikst2512-eng/boat-edge-clean/actions/runs/42/attempts/2/jobs",1),
            ("/repos/ikst2512-eng/boat-edge-clean/actions/runs/42/attempts/2/jobs",2)])
        self.assertEqual(p[1]["total_count"], 101)

    def test_fetch_rejects_unstable_total_and_invalid_attempt(self):
        def reader(url):
            page_n = int(parse_qs(urlparse(url).query)["page"][0])
            return {"total_count": 101 if page_n == 1 else 100,
                    "jobs": [job(i, "test", 2) for i in range(100)]
                    if page_n == 1 else [job(101, "test", 2)]}
        with self.assertRaisesRegex(ValueError, "truncated_or_unstable"):
            fetch_job_pages(42, 2, reader=reader)
        with self.assertRaisesRegex(ValueError, "invalid_run_or_attempt"):
            fetch_job_pages(42, 0, reader=reader)


if __name__ == "__main__":
    unittest.main()
