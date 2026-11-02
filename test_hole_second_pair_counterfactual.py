"""Safety and determinism checks for read-only second-place simulations."""
import unittest

from hole_second_pair_counterfactual import propose


class HoleSecondPairCounterfactualTest(unittest.TestCase):
    def setUp(self):
        self.hole = ["1-2-3", "1-2-4", "2-3-1", "2-3-4", "1-2-5",
                     "3-4-1", "3-4-2", "2-3-5", "1-2-6", "3-4-5"]

    def test_inserts_new_second_pair_without_increasing_bets(self):
        result = propose(self.hole, ["1-3-2"], 3)
        self.assertEqual(result[2], "1-3-2")
        self.assertEqual(len(result), 10)
        self.assertEqual(len(result), len(set(result)))
        self.assertEqual(result[:2], self.hole[:2])

    def test_no_pair_candidate_no_change(self):
        self.assertEqual(propose(self.hole, ["1-2-6", "4-1-2"], 3), self.hole)

    def test_candidate_selection_does_not_depend_on_result(self):
        donor = ["1-4-2", "1-3-2"]
        self.assertEqual(propose(self.hole, donor, 5), propose(self.hole, donor, 5))
        self.assertEqual(propose(self.hole, donor, 5)[4], "1-4-2")

    def test_top10_replacement_does_not_change_top3_top5(self):
        result = propose(self.hole, ["1-3-2"], 10)
        self.assertEqual(result[:5], self.hole[:5])
        self.assertEqual(len(result), 10)

    def test_bad_rank_fails_closed(self):
        with self.assertRaises(ValueError):
            propose(self.hole, ["1-3-2"], 6)


if __name__ == "__main__":
    unittest.main()
