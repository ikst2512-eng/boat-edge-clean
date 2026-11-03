import unittest
from datetime import date
from urllib.parse import parse_qs,urlparse
from entry_course_schedule_audit import operational_audit

DAY="20261103"
def response(path, *, t12=True, t2=True, archive=True, workflow_dispatch=False,
             failed=False):
    if "/git/trees/" in path:
        return {"truncated":False,"tree":([
            {"type":"blob","path":"t12_baselines/20261103/202611030708.json"},
            {"type":"blob","path":"waku10/20261103/202611030708.json"},
            {"type":"blob","path":"operations/entry-course-write-access-v1.json"},
            {"type":"blob","path":"waku10/20261102/202611020708.json"}
        ] if archive else [])}
    if "/actions/workflows/" in path:
        is_t12="entry-course-t12-baseline.yml" in path
        if not (t12 if is_t12 else t2):
            return {"workflow_runs":[]}
        if parse_qs(urlparse(path).query).get("page")!=["1"]:
            return {"workflow_runs":[]}
        event="workflow_dispatch" if workflow_dispatch else "schedule"
        status="failure" if failed else "success"
        return {"workflow_runs":[
            {"id":1 if is_t12 else 2,"created_at":"2026-11-03T12:15:00Z",
             "event":event,"status":"completed","conclusion":status,
             "head_sha":"a"*40},
            {"id":9,"created_at":"2026-11-02T12:15:00Z",
             "event":"schedule","status":"completed","conclusion":"success"},
        ]}
    raise AssertionError(path)

class ScheduledLedgerAuditTests(unittest.TestCase):
    def test_counts_schedule_and_archive_paths_without_claiming_valid_forecasts(self):
        item=operational_audit(DAY,fetch=response,today=date(2026,11,4))
        self.assertEqual(item["t12"]["scheduled_run_count"],1)
        self.assertEqual(item["t2"]["scheduled_run_count"],1)
        self.assertEqual(item["t12"]["archived_candidate_path_count"],1)
        self.assertEqual(item["t2"]["archived_candidate_path_count"],1)
        self.assertTrue(item["archive_paths_not_byte_verified"])
        self.assertFalse(item["pre_cutoff_provenance_verified"])
        self.assertFalse(item["prediction_hit_rate_verified"])
    def test_pr_or_manual_workflow_is_not_counted_as_unattended(self):
        out=operational_audit(DAY,
            fetch=lambda path:response(path,workflow_dispatch=True),today=date(2026,11,4))
        self.assertEqual(out["t12"]["scheduled_run_count"],0)
        self.assertEqual(out["t12"]["status"],"missing_scheduled_runs")
        self.assertEqual(out["t2"]["scheduled_run_count"],0)
    def test_probe_is_not_a_forecast_even_if_branch_responds(self):
        out=operational_audit(DAY,fetch=lambda path:response(path,archive=False),
                              today=date(2026,11,4))
        self.assertEqual(out["t12"]["archived_candidate_path_count"],0)
        self.assertEqual(out["t12"]["status"],"no_candidate_archive_paths")
    def test_missing_t12_schedule_but_t2_schedule_keeps_them_separate(self):
        out=operational_audit(DAY,fetch=lambda path:response(path,t12=False),
                              today=date(2026,11,4))
        self.assertEqual(out["t12"]["scheduled_run_count"],0)
        self.assertEqual(out["t2"]["scheduled_run_count"],1)
        self.assertEqual(out["t12"]["archived_candidate_path_count"],1)
    def test_failed_schedule_not_success(self):
        out=operational_audit(DAY,fetch=lambda path:response(path,failed=True),
                              today=date(2026,11,4))
        self.assertEqual(out["t12"]["completed_failure_run_count"],1)
        self.assertEqual(out["t12"]["completed_success_run_count"],0)
    def test_unfinished_day_never_scored_as_final(self):
        with self.assertRaisesRegex(ValueError,"completed_jst_day"):
            operational_audit(DAY,fetch=response,today=date(2026,11,3))
    def test_truncated_tree_blocks_partial_coverage_claim(self):
        with self.assertRaisesRegex(ValueError,"tree_truncated"):
            operational_audit(DAY,fetch=lambda path:{"truncated":True}
                              if "/git/trees/" in path else response(path),
                              today=date(2026,11,4))
    def test_github_api_exception_propagates_instead_of_zero(self):
        with self.assertRaises(OSError):
            operational_audit(DAY,fetch=lambda path:(_ for _ in ()).throw(OSError("api_down")),
                              today=date(2026,11,4))

if __name__=="__main__":unittest.main()
