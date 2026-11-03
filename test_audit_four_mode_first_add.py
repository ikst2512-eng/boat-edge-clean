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
            "source_sha256": {"title": "a"*64, "race_cards": "b"*64},
            "generated_at_jst": "2026-10-28T10:00:00+09:00",
            "deadline_jst": "2026-10-28T11:00:00+09:00",
            "source_title_received_jst": "2026-10-28T09:59:00+09:00",
            "source_cards_received_jst": "2026-10-28T09:59:10+09:00",
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

    def test_utc_git_commit_is_valid_if_before_deadline(self):
        result = self.check(stamped="2026-10-28T01:01:00+00:00")
        self.assertTrue(result["git_committer_before_deadline"])

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

    def test_missing_source_digest_rejected(self):
        self.record["source_sha256"].pop("race_cards")
        with self.assertRaisesRegex(ValueError, "invalid_source_digests"):
            self.check()

    def test_bad_source_digest_rejected(self):
        self.record["source_sha256"]["title"] = "not-a-sha"
        with self.assertRaisesRegex(ValueError, "invalid_source_digests"):
            self.check()

    def test_source_receipt_after_generation_rejected(self):
        self.record["source_cards_received_jst"] = "2026-10-28T10:00:01+09:00"
        with self.assertRaisesRegex(ValueError, "source_receipt_after_generation"):
            self.check()

    def test_missing_source_receipt_rejected(self):
        del self.record["source_cards_received_jst"]
        with self.assertRaisesRegex(ValueError, "missing_source_receipts"):
            self.check()

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_path"):
            inspect("../four_mode_forecasts/202610280101.json", self.root)


if __name__ == "__main__":
    unittest.main()
