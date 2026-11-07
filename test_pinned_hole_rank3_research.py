import tempfile
import unittest
from pathlib import Path

from pinned_hole_rank3_research import (
    paired_exact_two_sided_p, run, score_one
)


class LockedHoleRecheckTests(unittest.TestCase):
    def test_selection_precedes_outcome_read(self):
        hole = ["1-2-3", "1-2-4", "1-3-2", "2-3-1", "2-3-4",
                "3-4-1", "3-4-2", "1-2-5", "2-3-5", "3-4-5"]
        seen = []

        def archive_reader(code, root):
            seen.append("archive")
            return 200, {"modes": {
                "hole": {"tickets": [{"combo": x} for x in hole]},
                "hit": {"tickets": [{"combo": "1-4-2"}]},
            }}

        def selector(base, donor, rank):
            seen.append("select")
            self.assertEqual(rank, 3)
            self.assertEqual(donor, ["1-4-2"])
            return list(base)

        def result_reader(code, root):
            seen.append("result")
            return {"status": "historical_comparison_only", "formal": False,
                    "remote_first_seen_verified": False, "winning_ticket": "1-2-3"}

        item = score_one("202610280101", Path("."),
                         archive_loader=archive_reader, selector=selector,
                         result_loader=result_reader)
        self.assertEqual(seen, ["archive", "select", "result"])
        self.assertEqual(item["topn"]["top1"]["baseline"], True)
        self.assertEqual(item["topn"]["top1"]["candidate"], True)
        self.assertFalse(item["changed"])

    def test_exact_p_is_descriptive_and_symmetric(self):
        self.assertAlmostEqual(paired_exact_two_sided_p(7, 1), 0.0703125)
        self.assertAlmostEqual(paired_exact_two_sided_p(1, 7), 0.0703125)
        self.assertIsNone(paired_exact_two_sided_p(0, 0))

    def test_locked_240_reproduces_existing_retrospective_comparison(self):
        report = run()
        self.assertEqual(report["status"], "historical_complete")
        self.assertEqual(report["requested"], 240)
        self.assertEqual(report["comparable"], 240)
        self.assertFalse(report["formal"])
        self.assertFalse(report["prospective_validation"])
        self.assertEqual(len(report["per_race"]), 240)
        self.assertEqual(len(set(row["race_code"] for row in report["per_race"])), 240)
        top10 = report["topn"]["top10"]
        self.assertEqual(top10["baseline_hits_on_valid_only"], 7)
        self.assertEqual(top10["candidate_hits_on_valid_only"], 13)
        self.assertEqual(top10["gained"], 7)
        self.assertEqual(top10["lost"], 1)
        self.assertEqual(report["topn"]["top1"]["gained"], 0)
        self.assertEqual(report["topn"]["top1"]["lost"], 0)

    def test_no_archive_never_claims_accuracy(self):
        with tempfile.TemporaryDirectory() as folder:
            report = run(root=Path(folder))
        self.assertEqual(report["status"], "incomplete_historical_evidence")
        self.assertEqual(report["comparable"], 0)
        self.assertEqual(len(report["unavailable"]), 240)
        self.assertIsNone(report["topn"])


if __name__ == "__main__":
    unittest.main()
