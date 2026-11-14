"""Synthetic-only job reconciliation; no real network and no publication."""
from copy import deepcopy
from datetime import datetime
import unittest

from position_sensitive_run_job_reconcile import (
    SCHEMA, reconcile_jobs, jobs_url, get_jobs_json,
)
from position_sensitive_schedule_run_inventory import audit_run_inventory
from test_position_sensitive_schedule_run_inventory import (
    DAY, NOW, WORKFLOW_BYTES, page, run,
)


def fixture():
    schedule = [run(11, at="2026-11-09T01:37:58Z"),
                run(12, at="2026-11-09T02:36:27Z")]
    manual = [run(13, at="2026-11-09T08:59:08Z", event="workflow_dispatch")]
    inventory = audit_run_inventory(
        DAY, NOW, WORKFLOW_BYTES, [page(schedule)], [page(manual)])
    jobs = {
        11: [dict(id=111, run_id=11, name="test", status="completed", conclusion="success"),
             dict(id=112, run_id=11, name="capture", status="completed", conclusion="success")],
        12: [dict(id=121, run_id=12, name="test", status="completed", conclusion="success"),
             dict(id=122, run_id=12, name="capture", status="completed", conclusion="failure")],
        13: [dict(id=131, run_id=13, name="test", status="completed", conclusion="success"),
             dict(id=132, run_id=13, name="capture", status="completed", conclusion="success")],
    }
    return inventory, jobs


def fetcher(jobs):
    calls = []
    def fetch(url):
        calls.append(url)
        for run_id, rows in jobs.items():
            if url == jobs_url(run_id, 1):
                return {"total_count": len(rows), "jobs": rows}
        raise AssertionError("unexpected remote GET")
    return fetch, calls


class ResearchCaptureJobReconcileTests(unittest.TestCase):
    def test_one_failed_capture_not_misclassified_as_published(self):
        inventory, jobs = fixture()
        fetch, calls = fetcher(jobs)
        report = reconcile_jobs(inventory, fetch)
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["matching_schedule_runs"], 2)
        self.assertEqual(report["matching_schedule_capture_jobs_success"], 1)
        self.assertEqual(report["matching_manual_dispatch_runs"], 1)
        self.assertEqual(report["matching_manual_main_capture_jobs_success"], 1)
        self.assertEqual(report["individual_run_jobs_verified"], 3)
        self.assertEqual(len(calls), 3)
        self.assertFalse(report["original_publication_verified_from_job_status"])
        self.assertFalse(report["position_candidate_publication_verified_from_job_status"])
        self.assertFalse(report["run_to_cron_slot_mapping_verified"])
        self.assertFalse(report["complete_scheduled_and_rescue_run_inventory_verified"])
        self.assertFalse(report["formal"])
        self.assertEqual(report["candidate_first_remote_receipts_independently_verified"], 0)
        self.assertEqual(report["jobs"][1]["classification"], "main_capture_job_not_completed_success")

    def test_nonmain_dispatch_never_counted_as_prod_capture(self):
        inventory, jobs = fixture()
        item = inventory["matching_manual_dispatch_runs"][0]
        item["branch"] = "research/shadow-only"
        item["main_capture_branch"] = False
        fetch, calls = fetcher(jobs)
        x = reconcile_jobs(inventory, fetch)
        self.assertEqual(x["matching_manual_main_capture_jobs_success"], 0)
        self.assertEqual(x["jobs"][-1]["classification"], "nonmain_dispatch_not_a_production_capture")
        self.assertFalse(x["promotion_allowed"])

    def test_false_inventory_promotion_rejected_before_jobs_get(self):
        inv, jobs = fixture()
        inv["formal"] = True
        fetch, calls = fetcher(jobs)
        with self.assertRaisesRegex(ValueError, "untrusted_source_schedule_inventory"):
            reconcile_jobs(inv, fetch)
        self.assertEqual(calls, [])

    def test_wrong_job_run_id_duplicate_job_and_missing_capture_rejected(self):
        for corruption in ("wrong_run_id", "duplicate", "missing"):
            inv, jobs = fixture()
            if corruption == "wrong_run_id":
                jobs[11][1]["run_id"] = 999
            elif corruption == "duplicate":
                jobs[11].append(dict(jobs[11][1], id=113))
            else:
                jobs[11].pop()
            fetch, calls = fetcher(jobs)
            with self.subTest(change=corruption), self.assertRaises(ValueError):
                reconcile_jobs(inv, fetch)

    def test_unsafe_conclusion_invalid_job_status_and_no_jobs_fail(self):
        for change in ("invalid_conclusion", "invalid_status", "empty"):
            inv,jobs=fixture()
            if change == "invalid_conclusion":
                jobs[11][0]["conclusion"] = "we_saved_the_prediction"
            elif change == "invalid_status":
                jobs[11][0]["status"] = "success"
            else:
                jobs[11].clear()
            fetch,_=fetcher(jobs)
            with self.subTest(change=change), self.assertRaises(ValueError):
                reconcile_jobs(inv, fetch)

    def test_missing_pagination_on_job_list_is_hard_failure(self):
        inv,jobs=fixture()
        fetch,calls=fetcher(jobs)
        def truncated(url):
            if url == jobs_url(11,1):
                return {"total_count": 101, "jobs": jobs[11]}
            if url == jobs_url(11,2):
                return {"total_count": 101, "jobs": []}
            return fetch(url)
        with self.assertRaisesRegex(ValueError,"pagination_incomplete"):
            reconcile_jobs(inv,truncated)

    def test_duplicate_or_missing_run_identity_in_inventory_fail(self):
        inv,jobs=fixture()
        inv["matching_manual_dispatch_runs"][0]["run_id"]=11
        fetch,_=fetcher(jobs)
        with self.assertRaisesRegex(ValueError,"source_run_identity_or_status_invalid"):
            reconcile_jobs(inv,fetch)
        inv,jobs=fixture()
        inv["matching_manual_dispatch_runs"]=[]
        fetch,_=fetcher(jobs)
        with self.assertRaisesRegex(ValueError,"source_run_count_inconsistent"):
            reconcile_jobs(inv,fetch)

    def test_allowlisted_jobs_api_only_and_bad_ids(self):
        for url in ("https://example.com", "https://api.github.com/repos/other/repo/actions/runs/5/jobs?per_page=100&page=1",
                    "https://api.github.com/repos/ikst2512-eng/boat-edge-clean/actions/runs/5/jobs?per_page=10&page=1"):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError,"unapproved_actions_jobs_endpoint"):
                get_jobs_json(url)
        for rid in (0, -1, 1.1, "abc"):
            with self.subTest(rid=rid), self.assertRaises(ValueError):
                jobs_url(rid,1)
        self.assertEqual(jobs_url(12,1).split("?")[1],"per_page=100&page=1")


if __name__ == "__main__":
    unittest.main()
