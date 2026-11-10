"""Result-access chronology gate for research-only hole selectors."""
import unittest
from itertools import permutations
from unittest.mock import patch

import hole_out_of_cohort_validation as out
import hole_strict_temporal_holdout as strict

CODE = "202611040101"
def archive():
    combos = ["-".join(map(str, p)) for p in list(permutations(range(1, 7), 3))[:10]]
    tickets = [{"combo": t} for t in combos]
    return {"modes": {m: {"tickets": tickets} for m in ("hole", "hit", "balance")}}

class ResultBlindChronologyTest(unittest.TestCase):
    def test_out_of_cohort_freezes_before_result(self):
        calls = []
        def select(base, donors, rank):
            calls.append("candidate")
            return list(base)
        def result(code, root):
            calls.append("result")
            return {"status": "historical_comparison_only", "winning_ticket": "1-2-3"}
        with patch.object(out, "historical_cohort", return_value={
                "status": "historical_research_only", "cohort_codes": ["202610280101"]}), \
             patch.object(out, "holdout_codes", return_value=[CODE]), \
             patch.object(out, "archived_four_modes", return_value=(200, archive())), \
             patch.object(out, "propose", side_effect=select), \
             patch.object(out, "compare_race", side_effect=result):
            data = out.run(root=".", limit=1)
        self.assertEqual(calls, ["candidate"] * 6 + ["result"])
        self.assertEqual(data["heldout_comparable"], 1)

    def test_strict_temporal_freezes_before_result(self):
        calls = []
        def select(base, donors, rank):
            calls.append("candidate")
            return list(base)
        def result(code, root):
            calls.append("result")
            return {"status": "historical_comparison_only", "winning_ticket": "1-2-3"}
        with patch.object(strict, "training_run", return_value={
                "status": "historical_research_only", "cohort_codes": ["202610280101"]}), \
             patch.object(strict, "later_date_codes", return_value=[CODE]), \
             patch.object(strict, "archived_four_modes", return_value=(200, archive())), \
             patch.object(strict, "propose", side_effect=select), \
             patch.object(strict, "compare_race", side_effect=result):
            data = strict.run(root=".", limit=1)
        self.assertEqual(calls, ["candidate"] * 6 + ["result"])
        self.assertEqual(data["heldout_comparable"], 1)

    def test_invalid_archive_never_accesses_outcome(self):
        with patch.object(out, "historical_cohort", return_value={
                "status": "historical_research_only", "cohort_codes": ["202610280101"]}), \
             patch.object(out, "holdout_codes", return_value=[CODE]), \
             patch.object(out, "archived_four_modes", return_value=(404, None)), \
             patch.object(out, "compare_race", side_effect=AssertionError("early outcome read")):
            data = out.run(root=".", limit=1)
        self.assertEqual(data["heldout_comparable"], 0)
        self.assertEqual(len(data["unavailable"]), 1)

if __name__ == "__main__":
    unittest.main()
