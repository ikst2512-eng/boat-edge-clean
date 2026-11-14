"""Synthetic offline regression for a secondary-source 1C exception ledger."""
import csv
import tempfile
import unittest
from pathlib import Path

from scripts.research_official_c1_exception_ledger import git_blob_sha, exception, scan_day

def row(f="", winner="2", finish=None, st="0.13"):
    record = {"レースコード": "202608010301", "決まり手": "差　し",
              "風速(m)": "2", "風向": "1", "1着_艇番": winner,
              "1コース_F": f, "1コース_スタートタイミング": st}
    record.update({f"{i}コース_艇番": str(i) for i in range(1, 7)})
    finish = finish or ["2", "3", "4", "5", "6", ""]
    record.update({f"{i}着_艇番": finish[i-1] for i in range(1, 7)})
    return record

class TestC1Exceptions(unittest.TestCase):
    def test_nonf_unranked_kept_unknown(self):
        record = exception(row(), {"code": "202608010301", "venue": "03"})
        self.assertEqual(record["reason"], "first_course_unranked_nonF")
        self.assertEqual(record["official_K_status"], "unverified")
        self.assertIsNone(record["first_course_finish_rank"])

    def test_f_is_not_assumed_official_exclusion(self):
        record = exception(row(f="F", st="-0.04"), {"code": "202608010301", "venue": "03"})
        self.assertEqual(record["reason"], "first_course_F_mark")
        self.assertEqual(record["official_K_status"], "unverified")

    def test_ranked_nonf_is_not_exception(self):
        self.assertIsNone(exception(
            row(finish=["2", "1", "3", "4", "5", "6"]),
            {"code": "202608010301", "venue": "03"}))

    def test_duplicate_finish_fails(self):
        with self.assertRaisesRegex(ValueError, "duplicate_finish_boat"):
            exception(row(finish=["2", "2", "3", "4", "5", ""]),
                      {"code": "202608010301", "venue": "03"})

    def test_git_blob_sha_and_daily_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "day.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(row()))
                writer.writeheader()
                writer.writerow(row())
            source = {"day": "2026-08-01", "sha": git_blob_sha(path.read_bytes()),
                      "rows": 1, "accepted": 1}
            counts, exceptions = scan_day(path, source)
            self.assertEqual(counts["03:eligible"], 1)
            self.assertEqual(counts["03:nonf_unranked"], 1)
            self.assertEqual(len(exceptions), 1)
            source["sha"] = "0" * 40
            with self.assertRaisesRegex(ValueError, "git_blob_sha_mismatch"):
                scan_day(path, source)


class VerifiedReceiptGateTests(unittest.TestCase):
    def test_wrong_frozen_period_rejected(self):
        from scripts.research_official_c1_exception_ledger import from_verified_rows
        with self.assertRaisesRegex(ValueError, "unexpected_frozen_source_period"):
            from_verified_rows([], [], {"period": "wrong", "sources": []})

    def test_missing_receipts_rejected(self):
        import datetime as dt
        from scripts.research_official_c1_exception_ledger import from_verified_rows
        days = [dt.date(2026, 8, 1) + dt.timedelta(days=i) for i in range(92)]
        evidence = {"period": "2026-08-01/2026-10-31",
                    "sources": [{"day": str(day), "rows": 0, "accepted": 0, "sha": "0" * 40}
                                for day in days]}
        with self.assertRaisesRegex(ValueError, "verified_receipt_or_raw_count_mismatch"):
            from_verified_rows([], [], evidence)

if __name__ == "__main__":
    unittest.main()
