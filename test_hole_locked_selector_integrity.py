"""Regression coverage for immutable hole selector Git blob dependency pins."""
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from hole_future_locked_eval import (
    LOCKED_SELECTION_BLOBS, evaluate, verify_locked_selection,
)


class LockedSelectorTests(unittest.TestCase):
    def test_actual_main_selection_files_match_pinned_hashes(self):
        self.assertEqual(verify_locked_selection(), LOCKED_SELECTION_BLOBS)

    def test_dependency_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in LOCKED_SELECTION_BLOBS:
                shutil.copy2(Path(__file__).resolve().parent/name,root/name)
            self.assertEqual(verify_locked_selection(root),LOCKED_SELECTION_BLOBS)
            path=root/"hole_pair_diversification_research.py"
            path.write_bytes(path.read_bytes()+b"\n# subtle unreviewed candidate selection change\n")
            with self.assertRaisesRegex(ValueError,"locked_selector_changed"):
                verify_locked_selection(root)

    def test_missing_dependency_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"locked_selector_missing"):
                verify_locked_selection(Path(tmp))

    def test_pre_eligible_audit_still_checks_locked_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=evaluate(tmp,date(2026,11,3))
            self.assertEqual(result["status"],"not_yet_eligible")
            self.assertFalse(result["formal"])


if __name__=="__main__":
    unittest.main()
