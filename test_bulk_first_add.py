"""Regression: batch lookup never bypasses byte and uniqueness evidence."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import audit_clean_first_add as audit

SHA = "a" * 40
STAMP = "2026-10-30T10:00:00+09:00"
CODES = ["202610300101", "202610300102"]

class BatchFirstAddTests(unittest.TestCase):
    def test_one_history_scan_and_each_original_blob_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "prospective_predictions"
            folder.mkdir()
            for code in CODES:
                (folder / (code + ".json")).write_bytes(code.encode())
            def git(argv, **kwargs):
                if argv[1] == "log":
                    return ("COMMIT " + SHA + " " + STAMP + "\n" +
                            "\n".join("prospective_predictions/" + c + ".json" for c in CODES) + "\n")
                if argv[1] == "show":
                    return argv[2].split("/")[-1].removesuffix(".json").encode()
                raise AssertionError(argv)
            with patch.object(audit.subprocess, "check_output", side_effect=git) as called:
                with audit.bulk_first_add(root):
                    for code in CODES:
                        data, sha, stamp = audit.first_add("prospective_predictions/" + code + ".json", root)
                        self.assertEqual(data, code.encode())
                        self.assertEqual(sha, SHA)
                self.assertEqual(called.call_count, 3)

    def test_duplicate_addition_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = "prospective_predictions/202610300101.json"
            with patch.object(audit.subprocess, "check_output", return_value=
                              "COMMIT " + SHA + " " + STAMP + "\n" + path + "\n" +
                              "COMMIT " + "b"*40 + " " + STAMP + "\n" + path + "\n"):
                with audit.bulk_first_add(root):
                    with self.assertRaises(ValueError):
                        audit.first_add(path, root)

if __name__ == "__main__":
    unittest.main()
