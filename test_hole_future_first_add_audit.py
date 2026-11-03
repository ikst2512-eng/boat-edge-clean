import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from hole_future_first_add_audit import first_add,audit

CODE="202611040101"
SHA="a"*40
RAW=b'{"sample":"frozen"}\n'


class FirstAddEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        folder=self.root/"four_mode_forecasts"
        folder.mkdir()
        self.file=folder/(CODE+".json")
        self.file.write_bytes(RAW)
        self.source={"deadline_jst":"2026-11-04T12:00:00+09:00"}

    def git(self,*args):
        if args[0]=="log":
            return (SHA+"\n").encode()
        if args[0]=="show" and "--no-patch" in args:
            return b"2026-11-04T11:45:00+09:00\n"
        if args[0]=="show":
            return RAW
        raise AssertionError(args)

    def test_git_first_add_matches_exact_bytes_but_not_remote_receipt(self):
        with patch("hole_future_first_add_audit.archived_four_modes",
                   return_value=(200,self.source)):
            row=first_add(CODE,self.root,self.git)
        self.assertEqual(row["status"],"local_git_first_add_clock_before_t12_unverified")
        self.assertEqual(row["first_add_commit"],SHA)
        self.assertTrue(row["content_exact_first_add_match"])
        self.assertFalse(row["remote_first_receipt_verified"])
        self.assertFalse(row["formal"])

    def test_git_clock_late_excludes_early_label(self):
        def late(*args):
            if args[0]=="show" and "--no-patch" in args:
                return b"2026-11-04T11:48:00+09:00\n"
            return self.git(*args)
        with patch("hole_future_first_add_audit.archived_four_modes",
                   return_value=(200,self.source)):
            row=first_add(CODE,self.root,late)
        self.assertEqual(row["status"],"local_git_first_add_clock_late")

    def test_exact_first_add_blob_mismatch_is_never_approved(self):
        def corrupt(*args):
            if args[0]=="show" and "--no-patch" not in args:
                return b'{"altered":true}\n'
            return self.git(*args)
        with patch("hole_future_first_add_audit.archived_four_modes",
                   return_value=(200,self.source)):
            row=first_add(CODE,self.root,corrupt)
        self.assertEqual(row["status"],"current_archive_differs_from_first_add")
        self.assertNotIn("remote_first_receipt_verified",row)

    def test_duplicate_or_absent_first_add_is_undetermined(self):
        def double(*args):
            if args[0]=="log":
                return (SHA+"\n"+("b"*40)+"\n").encode()
            return self.git(*args)
        with patch("hole_future_first_add_audit.archived_four_modes",
                   return_value=(200,self.source)):
            row=first_add(CODE,self.root,double)
        self.assertEqual(row["status"],"unique_first_add_not_found")
        self.assertEqual(row["candidate_commit_count"],2)

    def test_audit_excludes_nov3_and_reconciles_day_inventory(self):
        (self.file.parent/"202611030101.json").write_bytes(RAW)
        with patch("hole_future_first_add_audit.archived_four_modes",
                   return_value=(200,self.source)):
            report=audit(self.root,date(2026,11,4),git=self.git)
        self.assertEqual(report["scanned_forecasts"],1)
        self.assertEqual(report["by_day"],{"2026-11-04":1})
        self.assertEqual(sum(report["counts"].values()),1)
        self.assertFalse(report["independent_remote_first_receipt_verified"])
        self.assertFalse(report["eligible_for_formal_accuracy"])

    def test_no_future_forecasts_is_zero_not_false_positive(self):
        self.file.unlink()
        report=audit(self.root,date(2026,11,4))
        self.assertEqual(report["scanned_forecasts"],0)
        self.assertEqual(report["counts"],{})
        self.assertFalse(report["eligible_for_formal_accuracy"])

    def test_unavailable_history_is_non_approving(self):
        def fail(*args):
            raise OSError("git history not available")
        with patch("hole_future_first_add_audit.archived_four_modes",
                   return_value=(200,self.source)):
            row=first_add(CODE,self.root,fail)
        self.assertEqual(row["status"],"git_history_unavailable")

if __name__=="__main__":
    unittest.main()
