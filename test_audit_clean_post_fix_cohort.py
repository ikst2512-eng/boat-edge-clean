import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from audit_clean_post_fix_cohort import POST_FIX_START, inspect_post_fix, inspect_post_fix_record, post_fix_paths, with_execution_receipt, diagnostic_summary, verify_model_provenance


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
        self.assertIn("POST_FIX_REJECTIONS", workflow)
        self.assertIn("report.get('rejection_reasons',{})", workflow)
        self.assertIn("report.get('by_day',{})", workflow)

    @staticmethod
    def valid_tickets():
        return ["-".join(map(str, t)) for t in (
            (1,2,3),(1,2,4),(1,3,2),(1,3,4),(1,4,2),
            (1,4,3),(2,1,3),(2,1,4),(2,3,1),(2,3,4))]

    def test_post_fix_source_provenance_validates_digests_without_remote_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            directory=root/"prospective_predictions"
            directory.mkdir()
            path="prospective_predictions/202611050404.json"
            title="a"*64
            cards="b"*64
            digest=hashlib.sha256((title+":"+cards).encode()).hexdigest()
            record={"race_code":"202611050404",
                    "source_deadline_jst":"2026-11-05T12:16:00+09:00",
                    "input_source_kind":"public_pre_race_csv",
                    "validated":False, "predictions":self.valid_tickets(),
                    "source_title_sha256":title,"source_cards_sha256":cards,
                    "input_sha256":digest}
            (root/path).write_text(json.dumps(record))
            with patch("audit_clean_post_fix_cohort.inspect",
                       return_value={"race_code":"202611050404","formal":False,"first_add_sha":"b"*40}), \
                 patch("audit_clean_post_fix_cohort.verify_model_provenance",return_value={}):
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
            with patch("audit_clean_post_fix_cohort.inspect",return_value={"first_add_sha":"b"*40}), \
                 patch("audit_clean_post_fix_cohort.verify_model_provenance",return_value={}):
                self.assertEqual(inspect_post_fix_record(path,root)["input_source_kind"],
                                 "nonofficial_openapi_v1")
            record["input_sha256"]="0"*64
            (root/path).write_text(json.dumps(record))
            with patch("audit_clean_post_fix_cohort.inspect",return_value={}):
                with self.assertRaisesRegex(ValueError,"source digest mismatch"):
                    inspect_post_fix_record(path,root)

    def test_post_fix_rejects_invalid_race_id_or_deadline_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            d=root/"prospective_predictions"
            d.mkdir()
            path="prospective_predictions/202611050404.json"
            title="a"*64
            cards="b"*64
            record={
                "race_code":"202611050404",
                "source_deadline_jst":"2026-11-05T12:16:00+09:00",
                "validated":False,
                "predictions":self.valid_tickets(),
                "input_source_kind":"public_pre_race_csv",
                "source_title_sha256":title,
                "source_cards_sha256":cards,
                "input_sha256":hashlib.sha256((title+":"+cards).encode()).hexdigest(),
            }
            for race in ("202611050004","202611052501","202611050413"):
                (d/"202611050404.json").write_text(json.dumps({**record,"race_code":race}))
                with patch("audit_clean_post_fix_cohort.inspect",return_value={}):
                    with self.assertRaisesRegex(ValueError,"race identity"):
                        inspect_post_fix_record(path,root)
            for deadline in ("2026-11-06T12:16:00+09:00","not-a-timestamp"):
                (d/"202611050404.json").write_text(json.dumps({
                    **record,"source_deadline_jst":deadline}))
                with patch("audit_clean_post_fix_cohort.inspect",return_value={}):
                    with self.assertRaisesRegex(ValueError,"race identity"):
                        inspect_post_fix_record(path,root)
            (d/"202611050404.json").write_text(json.dumps(record))
            with patch("audit_clean_post_fix_cohort.inspect",return_value={"first_add_sha":"b"*40}), \
                 patch("audit_clean_post_fix_cohort.verify_model_provenance",return_value={}):
                result=inspect_post_fix_record(path,root)
            self.assertEqual(result["input_source_kind"],"public_pre_race_csv")
            self.assertFalse(result["raw_remote_receipt_verified"])

    def test_post_fix_missing_or_unrecognized_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            directory=root/"prospective_predictions"
            directory.mkdir()
            path="prospective_predictions/202611050404.json"
            for kind in (None, "unverified_post_results"):
                (root/path).write_text(json.dumps({"input_source_kind":kind,"validated":False,
                                                "predictions":self.valid_tickets()}))
                with patch("audit_clean_post_fix_cohort.inspect",return_value={}):
                    with self.assertRaisesRegex(ValueError,"source kind"):
                        inspect_post_fix_record(path,root)

    def test_reject_invalid_ticket_shape_duplicate_and_nonresearch_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            directory=root/"prospective_predictions"
            directory.mkdir()
            path="prospective_predictions/202611050404.json"
            record={"validated":False,"predictions":self.valid_tickets()}
            for tickets in (
                ["1-1-2"]+self.valid_tickets()[1:],
                ["1-2-7"]+self.valid_tickets()[1:],
                self.valid_tickets()[:9],
                [self.valid_tickets()[0]]*10,
                [123]+self.valid_tickets()[1:],
            ):
                record["predictions"]=tickets
                (root/path).write_text(json.dumps(record))
                with patch("audit_clean_post_fix_cohort.inspect",return_value={}):
                    with self.assertRaisesRegex(ValueError,"trifecta tickets"):
                        inspect_post_fix_record(path,root)
            record["predictions"]=self.valid_tickets()
            for flag in (True,None,0):
                record["validated"]=flag
                (root/path).write_text(json.dumps(record))
                with patch("audit_clean_post_fix_cohort.inspect",return_value={}):
                    with self.assertRaisesRegex(ValueError,"research classification"):
                        inspect_post_fix_record(path,root)

    def test_diagnostic_summary_preserves_rejection_categories_and_days(self):
        report = {"status":"post_fix_evidence_rejected", "candidate_count":2,
                  "rejection_reasons":{"source_digest_invalid":1},
                  "by_day":{"20261105":{"total":2,"local_audit_passed":1,"rejected":1}}}
        result = json.loads(diagnostic_summary(report))
        self.assertEqual(result["rejection_reasons"]["source_digest_invalid"],1)
        self.assertEqual(result["by_day"]["20261105"]["rejected"],1)
        self.assertEqual(result["status"],"post_fix_evidence_rejected")
        self.assertEqual(json.loads(diagnostic_summary({
            "status":"pending_no_new_capture","candidate_count":0
        }))["rejection_reasons"],{})

    def test_model_provenance_uses_real_git_ancestry_and_original_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            subprocess.run(["git","init","-q"],cwd=root,check=True)
            subprocess.run(["git","config","user.name","Audit test"],cwd=root,check=True)
            subprocess.run(["git","config","user.email","audit@example.invalid"],cwd=root,check=True)
            original=b"# frozen research model\\n"
            (root/"research_model.py").write_bytes(original)
            subprocess.run(["git","add","research_model.py"],cwd=root,check=True)
            subprocess.run(["git","commit","-qm","model source"],cwd=root,check=True)
            model_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
            (root/"candidate.txt").write_text("new candidate")
            subprocess.run(["git","add","candidate.txt"],cwd=root,check=True)
            subprocess.run(["git","commit","-qm","first freeze"],cwd=root,check=True)
            first_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
            record={"model_git_sha":model_sha,
                    "model_source_sha256":hashlib.sha256(original).hexdigest(),
                    "model_dependency_scope":"research_model.py_only_not_complete_environment"}
            result=verify_model_provenance(record,first_sha,root)
            self.assertEqual(result["model_git_sha"],model_sha)
            self.assertEqual(result["model_source_sha256"],record["model_source_sha256"])
            with self.assertRaisesRegex(ValueError,"model provenance"):
                verify_model_provenance({**record,"model_source_sha256":"0"*64},first_sha,root)
            with self.assertRaisesRegex(ValueError,"model provenance"):
                verify_model_provenance({**record,"model_dependency_scope":"complete"},first_sha,root)
            (root/"research_model.py").write_text("later new model")
            subprocess.run(["git","add","research_model.py"],cwd=root,check=True)
            subprocess.run(["git","commit","-qm","new unrelated model"],cwd=root,check=True)
            late_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
            with self.assertRaisesRegex(ValueError,"model provenance"):
                verify_model_provenance({**record,"model_git_sha":late_sha,
                                         "model_source_sha256":hashlib.sha256(
                                             b"later new model").hexdigest()},first_sha,root)

    def test_model_provenance_invalid_sha_cannot_invoke_git(self):
        with patch("audit_clean_post_fix_cohort.subprocess.check_output") as git:
            with self.assertRaisesRegex(ValueError,"model provenance"):
                verify_model_provenance({"model_git_sha":"notasha",
                    "model_source_sha256":"a"*64,
                    "model_dependency_scope":"research_model.py_only_not_complete_environment"},
                    "b"*40,Path("/tmp"))
            git.assert_not_called()

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
