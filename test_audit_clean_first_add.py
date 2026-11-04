import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import audit_clean_first_add as audit

class FirstAddAuditTests(unittest.TestCase):
    def test_first_add_before_cutoff_only_not_formal(self):
        obj={"race_code":"202610281201","status":"prospective_candidate","formal":False,"scoring":False,
             "source_deadline_jst":"2026-10-28T14:00:00+09:00",
             "cutoff_jst":"2026-10-28T13:48:00+09:00",
             "generated_at":"2026-10-28T10:00:00+09:00",
             "source_title_received_jst":"2026-10-28T09:59:00+09:00",
             "source_cards_received_jst":"2026-10-28T09:59:01+09:00"}
        with patch.object(audit,"first_add",return_value=(json.dumps(obj).encode(),"a"*40,datetime.fromisoformat("2026-10-28T10:01:00+09:00"))):
            x=audit.inspect("prospective_predictions/202610281201.json")
        self.assertFalse(x["formal"])
        self.assertFalse(x["remote_first_seen_verified"])
    def test_late_commit_denied(self):
        obj={"race_code":"202610281201","status":"prospective_candidate","formal":False,"scoring":False,
             "source_deadline_jst":"2026-10-28T14:00:00+09:00",
             "cutoff_jst":"2026-10-28T13:48:00+09:00",
             "generated_at":"2026-10-28T10:00:00+09:00",
             "source_title_received_jst":"2026-10-28T09:59:00+09:00",
             "source_cards_received_jst":"2026-10-28T09:59:01+09:00"}
        with patch.object(audit,"first_add",return_value=(json.dumps(obj).encode(),"a"*40,datetime.fromisoformat("2026-10-28T13:50:00+09:00"))):
            with self.assertRaises(ValueError):
                audit.inspect("prospective_predictions/202610281201.json")
    def test_first_commit_before_generation_is_not_valid_freeze_evidence(self):
        obj={"race_code":"202611050404","status":"prospective_candidate",
             "formal":False,"scoring":False,
             "source_deadline_jst":"2026-11-05T12:16:00+09:00",
             "cutoff_jst":"2026-11-05T12:04:00+09:00",
             "generated_at":"2026-11-05T10:00:00+09:00",
             "source_title_received_jst":"2026-11-05T09:59:00+09:00",
             "source_cards_received_jst":"2026-11-05T09:59:01+09:00"}
        with patch.object(audit,"first_add",return_value=(
            json.dumps(obj).encode(),"b"*40,
            datetime.fromisoformat("2026-11-05T09:59:59+09:00"))):
            with self.assertRaisesRegex(ValueError,
                                        "first Git commit predates candidate generation"):
                audit.inspect("prospective_predictions/202611050404.json")

    def test_receipts_after_forecast_generation_denied_even_before_cutoff(self):
        # Observed in 202611040404: generated 11:01:33.627, title and cards
        # not received until 11:01:33.708 and 11:01:33.766 respectively.
        obj={"race_code":"202611040404","status":"prospective_candidate",
             "formal":False,"scoring":False,
             "source_deadline_jst":"2026-11-04T12:16:00+09:00",
             "cutoff_jst":"2026-11-04T12:04:00+09:00",
             "generated_at":"2026-11-04T11:01:33.627045+09:00",
             "source_title_received_jst":"2026-11-04T11:01:33.708274+09:00",
             "source_cards_received_jst":"2026-11-04T11:01:33.766393+09:00"}
        with patch.object(audit,"first_add",return_value=(
            json.dumps(obj).encode(),"b"*40,
            datetime.fromisoformat("2026-11-04T11:02:00+09:00"))):
            with self.assertRaisesRegex(ValueError, "source received after candidate generation"):
                audit.inspect("prospective_predictions/202611040404.json")

    def test_either_source_receipt_after_generation_denied_independently(self):
        template={"race_code":"202611040404","status":"prospective_candidate",
                  "formal":False,"scoring":False,
                  "source_deadline_jst":"2026-11-04T12:16:00+09:00",
                  "cutoff_jst":"2026-11-04T12:04:00+09:00",
                  "generated_at":"2026-11-04T11:01:34+09:00",
                  "source_title_received_jst":"2026-11-04T11:01:33+09:00",
                  "source_cards_received_jst":"2026-11-04T11:01:33+09:00"}
        for source_key in ("source_title_received_jst","source_cards_received_jst"):
            obj=dict(template)
            obj[source_key]="2026-11-04T11:01:35+09:00"
            with self.subTest(source_key=source_key):
                with patch.object(audit,"first_add",return_value=(
                    json.dumps(obj).encode(),"b"*40,
                    datetime.fromisoformat("2026-11-04T11:02:00+09:00"))):
                    with self.assertRaisesRegex(ValueError,"source received after candidate generation"):
                        audit.inspect("prospective_predictions/202611040404.json")

    def test_equal_or_earlier_input_receipts_remain_eligible_for_research(self):
        obj={"race_code":"202611040404","status":"prospective_candidate",
             "formal":False,"scoring":False,
             "source_deadline_jst":"2026-11-04T12:16:00+09:00",
             "cutoff_jst":"2026-11-04T12:04:00+09:00",
             "generated_at":"2026-11-04T11:01:33.627045+09:00",
             "source_title_received_jst":"2026-11-04T11:01:33.620000+09:00",
             "source_cards_received_jst":"2026-11-04T11:01:33.627045+09:00"}
        with patch.object(audit,"first_add",return_value=(
            json.dumps(obj).encode(),"b"*40,
            datetime.fromisoformat("2026-11-04T11:02:00+09:00"))):
            result=audit.inspect("prospective_predictions/202611040404.json")
        self.assertFalse(result["formal"])
        self.assertFalse(result["remote_first_seen_verified"])

    def test_first_add_bounds_git_history_without_skipping_ambiguity(self):
        root = Path("/tmp/first-add-check")
        rel = "prospective_predictions/202610281201.json"
        stamp = "2026-10-28T09:00:00+09:00"
        with patch.object(audit.subprocess, "check_output",
                          side_effect=["false\n", "a"*40+" "+stamp+"\n", b"original"]) as run, \
                patch.object(Path, "read_bytes", return_value=b"original"):
            original, sha, when = audit.first_add(rel, root)
        self.assertEqual(sha, "a"*40)
        self.assertEqual(original, b"original")
        self.assertEqual(when.isoformat(), stamp)
        self.assertEqual(run.call_args_list[0].args[0],
                         ["git", "rev-parse", "--is-shallow-repository"])
        self.assertEqual(run.call_args_list[1].args[0][:3],
                         ["git", "log", "--max-count=2"])

    def test_single_record_refuses_shallow_history(self):
        root=Path("/tmp/first-add-check")
        with patch.object(audit.subprocess,"check_output",
                          return_value="true\n") as run:
            with self.assertRaisesRegex(ValueError,"incomplete local git history"):
                audit.first_add("prospective_predictions/202610281201.json",root)
        self.assertEqual(run.call_count,1)
        self.assertEqual(run.call_args.args[0],
                         ["git","rev-parse","--is-shallow-repository"])

    def test_single_record_refuses_indeterminate_history(self):
        root=Path("/tmp/first-add-check")
        with patch.object(audit.subprocess,"check_output",
                          return_value="unknown\n") as run:
            with self.assertRaisesRegex(ValueError,"incomplete local git history"):
                audit.first_add("prospective_predictions/202610281201.json",root)
        self.assertEqual(run.call_count,1)

    def test_bulk_refuses_shallow_history_before_reading_additions(self):
        root = Path("/tmp/first-add-check")
        with patch.object(audit.subprocess, "check_output",
                          return_value="true\n") as run:
            with self.assertRaisesRegex(ValueError, "incomplete local git history"):
                with audit.bulk_first_add(root):
                    self.fail("shallow evidence must never be examined")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0],
                         ["git", "rev-parse", "--is-shallow-repository"])

    def test_bulk_full_history_still_checks_unique_additions(self):
        root = Path("/tmp/first-add-check")
        with patch.object(audit.subprocess, "check_output",
                          side_effect=["false\n", "COMMIT " + "a"*40 + " 2026-10-28T09:00:00+09:00\nprospective_predictions/202610281201.json\n"]) as run:
            with audit.bulk_first_add(root):
                self.assertEqual(audit._BULK.state[1]["prospective_predictions/202610281201.json"][0][0], "a"*40)
        self.assertEqual(run.call_count, 2)

    def test_mixed_candidate_batch_preserves_rejections_and_other_valid_rows(self):
        paths=["prospective_predictions/202611040404.json",
               "prospective_predictions/202611040405.json"]
        def local_inspect(path,root):
            if path.endswith("0404.json"):
                raise ValueError("source received after candidate generation")
            return {"race_code":"202611040405","formal":False,
                    "remote_first_seen_verified":False}
        from contextlib import nullcontext
        with patch.object(audit,"bulk_first_add",return_value=nullcontext()) as scan:
            result=audit.audit_records(paths,inspector=local_inspect)
        scan.assert_called_once()
        self.assertEqual(result["total"],2)
        self.assertEqual(result["local_audit_passed"],1)
        self.assertEqual(result["rejected"],1)
        self.assertEqual(result["rejection_reasons"],
                         {"source_receipt_after_generation":1})
        self.assertEqual(result["by_day"],{"20261104":{
            "total":2,"local_audit_passed":1,"rejected":1,
            "rejection_reasons":{"source_receipt_after_generation":1}}})
        self.assertEqual(result["rejected_records"][0]["race_code"],"202611040404")
        self.assertFalse(result["formal"])
        self.assertFalse(result["remote_first_seen_verified"])

    def test_corrupted_original_does_not_suppress_other_candidate_verdicts(self):
        paths=["prospective_predictions/202611050404.json",
               "prospective_predictions/202611050405.json",
               "prospective_predictions/202611050406.json"]
        def inspect_one(path,root):
            if path.endswith("0404.json"):
                raise UnicodeDecodeError("utf-8",b"\\xff",0,1,"invalid start byte")
            if path.endswith("0405.json"):
                raise FileNotFoundError("original frozen record missing")
            return {"race_code":"202611050406","formal":False,
                    "remote_first_seen_verified":False}
        from contextlib import nullcontext
        with patch.object(audit,"bulk_first_add",return_value=nullcontext()):
            result=audit.audit_records(paths,inspector=inspect_one)
        self.assertEqual(result["total"],3)
        self.assertEqual(result["local_audit_passed"],1)
        self.assertEqual(result["rejected"],2)
        self.assertEqual(len(result["rejected_records"]),2)
        self.assertEqual(result["rejection_reasons"],{"other_rejection":2})
        self.assertFalse(result["formal"])
        self.assertFalse(result["remote_first_seen_verified"])

    def test_unreadable_original_git_blob_rejects_only_that_record(self):
        paths=["prospective_predictions/202611050404.json",
               "prospective_predictions/202611050405.json"]
        def inspector(path,root):
            if path.endswith("0404.json"):
                raise subprocess.CalledProcessError(
                    128,["git","show","badsha:prospective_predictions/202611050404.json"])
            return {"race_code":"202611050405","formal":False,
                    "remote_first_seen_verified":False}
        from contextlib import nullcontext
        with patch.object(audit,"bulk_first_add",return_value=nullcontext()):
            report=audit.audit_records(paths,inspector=inspector)
        self.assertEqual(report["total"],2)
        self.assertEqual(report["local_audit_passed"],1)
        self.assertEqual(report["rejected"],1)
        self.assertEqual(report["rejection_reasons"],{"other_rejection":1})
        self.assertEqual(report["by_day"]["20261105"]["rejected"],1)
        self.assertFalse(report["formal"])
        self.assertFalse(report["remote_first_seen_verified"])

    def test_daily_counts_separate_legacy_rejection_from_new_candidate(self):
        paths=["prospective_predictions/202610280101.json",
               "prospective_predictions/202611040404.json",
               "prospective_predictions/202611050404.json"]
        def inspect_one(path,root):
            if "20261105" in path:
                return {"race_code":"202611050404","formal":False,
                        "remote_first_seen_verified":False}
            raise ValueError("source received after candidate generation")
        from contextlib import nullcontext
        with patch.object(audit,"bulk_first_add",return_value=nullcontext()):
            output=audit.audit_records(paths,inspector=inspect_one)
        self.assertEqual(output["total"],3)
        self.assertEqual(output["local_audit_passed"],1)
        self.assertEqual(output["rejected"],2)
        self.assertEqual(output["by_day"],{
            "20261028":{"total":1,"local_audit_passed":0,"rejected":1,
                         "rejection_reasons":{"source_receipt_after_generation":1}},
            "20261104":{"total":1,"local_audit_passed":0,"rejected":1,
                         "rejection_reasons":{"source_receipt_after_generation":1}},
            "20261105":{"total":1,"local_audit_passed":1,"rejected":0,
                         "rejection_reasons":{}}})
        self.assertFalse(output["formal"])
        self.assertFalse(output["remote_first_seen_verified"])

    def test_batch_rejects_duplicate_or_untrusted_paths_before_history_scan(self):
        p="prospective_predictions/202611040404.json"
        for paths in ([p,p],["../" + p],[p,"prospective_predictions/missing.json"]):
            with self.assertRaises(ValueError):
                audit.audit_records(paths)

    def test_real_full_git_history_accepts_only_original_valid_research_candidate(self):
        # Use an actual temporary Git repository rather than mocked Git replies.
        # This verifies the first-add SHA, immutable blob and the same chronology
        # used to admit future post-fix candidate records locally.
        path="prospective_predictions/202611050404.json"
        candidate={
            "race_code":"202611050404","status":"prospective_candidate",
            "formal":False,"scoring":False,
            "source_deadline_jst":"2026-11-05T12:16:00+09:00",
            "cutoff_jst":"2026-11-05T12:04:00+09:00",
            "generated_at":"2026-11-05T10:00:00+09:00",
            "source_title_received_jst":"2026-11-05T09:59:00+09:00",
            "source_cards_received_jst":"2026-11-05T09:59:01+09:00"}
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            subprocess.run(["git","init","-q"],cwd=root,check=True)
            subprocess.run(["git","config","user.name","CLEAN test"],cwd=root,check=True)
            subprocess.run(["git","config","user.email","clean@example.invalid"],cwd=root,check=True)
            original=root/path
            original.parent.mkdir(parents=True)
            original.write_text(json.dumps(candidate,sort_keys=True),encoding="utf-8")
            subprocess.run(["git","add","--",path],cwd=root,check=True)
            env={**os.environ,"GIT_AUTHOR_DATE":"2026-11-05T10:01:00+09:00",
                 "GIT_COMMITTER_DATE":"2026-11-05T10:01:00+09:00"}
            subprocess.run(["git","commit","-qm","freeze test research candidate"],
                           cwd=root,env=env,check=True)
            direct=audit.inspect(path,root)
            self.assertEqual(len(direct["first_add_sha"]),40)
            self.assertTrue(direct["candidate_unchanged"])
            self.assertFalse(direct["formal"])
            self.assertFalse(direct["remote_first_seen_verified"])
            report=audit.audit_records([path],root)
            self.assertEqual((report["total"],report["local_audit_passed"],
                              report["rejected"]),(1,1,0))
            self.assertEqual(report["by_day"]["20261105"]["rejection_reasons"],{})
            self.assertFalse(report["remote_first_seen_verified"])
            # A post-commit edit must never be accepted as the first-added blob.
            original.write_text(json.dumps({**candidate,"generated_at":
                "2026-11-05T10:02:00+09:00"}),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"candidate changed since first add"):
                audit.inspect(path,root)

    def test_cli_mixed_archive_gate_remains_fail_closed(self):
        source=(Path(__file__).parent/"audit_clean_first_add.py").read_text()
        self.assertIn('if output["local_audit_passed"]==0:',source)
        self.assertIn('if output["rejected"]>0:',source)
        self.assertIn('Mixed archive contains rejected candidates',source)

    def test_untrusted_path(self):
        with self.assertRaises(ValueError):
            audit.first_add("../legacy/anything.json")
if __name__=="__main__":
    unittest.main()
