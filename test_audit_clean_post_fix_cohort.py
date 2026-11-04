import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from audit_clean_post_fix_cohort import POST_FIX_START, inspect_post_fix, inspect_post_fix_record, post_fix_paths, with_execution_receipt


class PostFixCohortTests(unittest.TestCase):
    def test_execution_receipt_correlates_run_without_certifying_remote_visibility(self):
        with patch("audit_clean_post_fix_cohort.subprocess.check_output",
                   return_value="a"*40) as git:
            report=with_execution_receipt(
                {"status":"local_first_add_passed", "formal":True,
                 "remote_first_seen_verified":True},
                root=Path("/tmp"),environ={
                    "GITHUB_RUN_ID":"12345","GITHUB_EVENT_NAME":"workflow_dispatch"})
        self.assertEqual(report["audit_run_id"],"12345")
        self.assertEqual(report["audit_event_name"],"workflow_dispatch")
        self.assertEqual(report["audit_checkout_sha"],"a"*40)
        self.assertFalse(report["remote_first_seen_verified"])
        self.assertFalse(report["formal"])
        git.assert_called_once()

    def test_execution_receipt_rejects_invalid_checkout_hash(self):
        with patch("audit_clean_post_fix_cohort.subprocess.check_output",
                   return_value="not-a-sha"):
            with self.assertRaisesRegex(ValueError,"invalid checkout commit"):
                with_execution_receipt({"status":"pending_no_new_capture"},environ={})

    def test_scheduled_backup_only_runs_independent_post_fix_evidence(self):
        workflow=(Path(__file__).resolve().parent/".github/workflows/clean-prospective-evaluation.yml").read_text(encoding="utf-8")
        self.assertIn("  schedule:", workflow)
        self.assertIn("    - cron: '30 3,12 * * *'", workflow)
        self.assertIn("  post-fix-cohort-evidence:", workflow)
        self.assertIn("  unit-tests:\\n    if: github.event_name != 'schedule'".replace("\\n","\n"), workflow)
        self.assertIn("  immutable-archive-gate:\\n    if: github.event_name != 'schedule'".replace("\\n","\n"), workflow)
        self.assertIn("  workflow_dispatch:", workflow)
        self.assertIn("  push:", workflow)

    def test_post_fix_source_provenance_validates_digests_without_remote_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            directory=root/"prospective_predictions"
            directory.mkdir()
            path="prospective_predictions/202611050404.json"
            title="a"*64
            cards="b"*64
            digest=hashlib.sha256((title+":"+cards).encode()).hexdigest()
            record={"input_source_kind":"public_pre_race_csv",
                    "source_title_sha256":title,"source_cards_sha256":cards,
                    "input_sha256":digest}
            (root/path).write_text(json.dumps(record))
            with patch("audit_clean_post_fix_cohort.inspect",
                       return_value={"race_code":"202611050404","formal":False}):
                result=inspect_post_fix_record(path,root)
            self.assertEqual(result["input_source_kind"],"public_pre_race_csv")
            self.assertFalse(result["raw_remote_receipt_verified"])
            record["input_source_kind"]="nonofficial_openapi_v1"
            (root/path).write_text(json.dumps(record))
            with patch("audit_clean_post_fix_cohort.inspect",return_value={}):
                with self.assertRaisesRegex(ValueError,"source digest mismatch"):
                    inspect_post_fix_record(path,root)
            record["source_cards_sha256"]=title
            record["input_sha256"]=hashlib.sha256((title+":"+title).encode()).hexdigest()
            (root/path).write_text(json.dumps(record))
            with patch("audit_clean_post_fix_cohort.inspect",return_value={}):
                self.assertEqual(inspect_post_fix_record(path,root)["input_source_kind"],
                                 "nonofficial_openapi_v1")
            record["input_sha256"]="0"*64
            (root/path).write_text(json.dumps(record))
            with patch("audit_clean_post_fix_cohort.inspect",return_value={}):
                with self.assertRaisesRegex(ValueError,"source digest mismatch"):
                    inspect_post_fix_record(path,root)

    def test_post_fix_missing_or_unrecognized_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            directory=root/"prospective_predictions"
            directory.mkdir()
            path="prospective_predictions/202611050404.json"
            for kind in (None, "unverified_post_results"):
                (root/path).write_text(json.dumps({"input_source_kind":kind}))
                with patch("audit_clean_post_fix_cohort.inspect",return_value={}):
                    with self.assertRaisesRegex(ValueError,"source kind"):
                        inspect_post_fix_record(path,root)

    def test_no_new_capture_is_pending_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = inspect_post_fix(Path(tmp))
        self.assertEqual(result["status"], "pending_no_new_capture")
        self.assertEqual(result["candidate_count"], 0)
        self.assertFalse(result["remote_first_seen_verified"])
        self.assertFalse(result["formal"])

    def test_filters_legacy_and_malformed_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "prospective_predictions"
            d.mkdir()
            for name in (
                "202611040404.json",
                "202611050404.json",
                "202611060101.json",
                "notes.json",
                "2026110504.json",
            ):
                (d / name).write_text("{}")
            self.assertEqual(post_fix_paths(Path(tmp)), [
                "prospective_predictions/202611050404.json",
                "prospective_predictions/202611060101.json",
            ])
        self.assertEqual(POST_FIX_START, "20261105")

    def test_valid_new_records_remain_research_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "prospective_predictions"
            d.mkdir()
            (d / "202611050404.json").write_text("{}")
            calls = []
            def passing(paths, root):
                calls.append(paths)
                return {"total": 1, "local_audit_passed": 1, "rejected": 0,
                        "local_passed_records": [{"race_code": "202611050404"}],
                        "rejected_records": []}
            result = inspect_post_fix(Path(tmp), passing)
        self.assertEqual(calls, [["prospective_predictions/202611050404.json"]])
        self.assertEqual(result["status"], "local_first_add_passed")
        self.assertFalse(result["remote_first_seen_verified"])
        self.assertFalse(result["formal"])

    def test_mixed_new_records_are_rejected_not_averaged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "prospective_predictions"
            d.mkdir()
            for name in ("202611050404.json", "202611050405.json"):
                (d / name).write_text("{}")
            def mixed(paths, root):
                self.assertEqual(len(paths), 2)
                return {"total": 2, "local_audit_passed": 1, "rejected": 1,
                        "rejected_records": [{"race_code": "202611050405"}]}
            result = inspect_post_fix(Path(tmp), mixed)
        self.assertEqual(result["status"], "post_fix_evidence_rejected")
        self.assertEqual(result["local_audit_passed"], 1)
        self.assertEqual(result["rejected"], 1)


if __name__ == "__main__":
    unittest.main()
