import json
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
                          side_effect=["a"*40+" "+stamp+"\n", b"original"]) as run, \
                patch.object(Path, "read_bytes", return_value=b"original"):
            original, sha, when = audit.first_add(rel, root)
        self.assertEqual(sha, "a"*40)
        self.assertEqual(original, b"original")
        self.assertEqual(when.isoformat(), stamp)
        self.assertEqual(run.call_args_list[0].args[0][:3],
                         ["git", "log", "--max-count=2"])

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
        self.assertEqual(result["rejected_records"][0]["race_code"],"202611040404")
        self.assertFalse(result["formal"])
        self.assertFalse(result["remote_first_seen_verified"])

    def test_batch_rejects_duplicate_or_untrusted_paths_before_history_scan(self):
        p="prospective_predictions/202611040404.json"
        for paths in ([p,p],["../" + p],[p,"prospective_predictions/missing.json"]):
            with self.assertRaises(ValueError):
                audit.audit_records(paths)

    def test_untrusted_path(self):
        with self.assertRaises(ValueError):
            audit.first_add("../legacy/anything.json")
if __name__=="__main__":
    unittest.main()
