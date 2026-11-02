import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from audit_four_mode_first_add import inspect


class FourModeFirstAddTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "four_mode_forecasts").mkdir()
        self.rel = "four_mode_forecasts/202610280101.json"
        self.record = {
            "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
            "race_code": "202610280101", "status": "provisional",
            "validated": False,
            "generated_at_jst": "2026-10-28T10:00:00+09:00",
            "deadline_jst": "2026-10-28T11:00:00+09:00",
            "modes": {m: {"tickets": [{"combo": "1-2-3", "p": 5.0}]}
                      for m in ("hit", "balance", "hole", "narrow")},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, stamped="2026-10-28T10:01:00+09:00", changes=False):
        saved = json.dumps(self.record).encode()
        (self.root / self.rel).write_bytes(saved + (b" " if changes else b""))
        def git(args, **kwargs):
            if args[1] == "log":
                return "a" * 40 + "\n"
            if args[1] == "show" and "-s" in args:
                return stamped + "\n"
            return saved
        with patch("audit_four_mode_first_add.subprocess.check_output", side_effect=git):
            return inspect(self.rel, self.root)

    def test_valid_local_commit_is_not_formal(self):
        result = self.check()
        self.assertEqual(result["modes"], ["hit", "balance", "hole", "narrow"])
        self.assertFalse(result["remote_first_seen_verified"])
        self.assertFalse(result["performance_eligible"])

    def test_late_git_commit_rejected(self):
        with self.assertRaisesRegex(ValueError, "first_add"):
            self.check(stamped="2026-10-28T11:05:00+09:00")

    def test_changed_archive_rejected(self):
        with self.assertRaisesRegex(ValueError, "changed"):
            self.check(changes=True)

    def test_wrong_mode_set_rejected(self):
        del self.record["modes"]["narrow"]
        with self.assertRaisesRegex(ValueError, "invalid_four_mode_archive"):
            self.check()

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_path"):
            inspect("../four_mode_forecasts/202610280101.json", self.root)


if __name__ == "__main__":
    unittest.main()
