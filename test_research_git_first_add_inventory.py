import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from research_git_first_add_inventory import audit

class FirstAddInventoryTests(unittest.TestCase):
    def test_existing_frozen_repository_fail_closed(self):
        root=Path(__file__).resolve().parent
        result=audit(root, root/"research_snapshots")
        self.assertGreater(result["counts"]["local_candidates"],0)
        self.assertEqual(result["trusted_remote_receipts_verified"],0)
        self.assertEqual(result["outcomes_verified"],0)
        self.assertEqual(result["status"],"GIT_LOCAL_AUDIT_NOT_FORMAL_SCORING")

    def test_unverified_metadata_is_never_promoted(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"research_snapshots").mkdir()
            (root/"research_snapshots"/"202610270101.json").write_text(
                json.dumps({"race_code":"202610270101","status":"research","validated":False}),
                encoding="utf-8")
            result=audit(root,root/"research_snapshots")
            self.assertEqual(result["counts"].get("local_candidates",0),0)
            self.assertEqual(result["exclusions"]["missing_or_invalid_local_metadata"],1)
if __name__=="__main__":
    unittest.main()
