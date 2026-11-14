"""Coverage contract: all finish permutations and all attack-initiator roles."""
from collections import Counter
import unittest
from scenario_full_pathway_catalog import complete_pathway_catalog


class FullCoverage(unittest.TestCase):
    def test_exactly_120_unique_outcomes_20_per_head(self):
        rows = complete_pathway_catalog()["outcomes"]
        self.assertEqual(len(rows), 120)
        self.assertEqual(len({r["ticket"] for r in rows}), 120)
        self.assertEqual(Counter(r["first_course"] for r in rows), {c: 20 for c in range(1, 7)})

    def test_each_attack_initiator_can_win_place_or_miss(self):
        rows = complete_pathway_catalog()["outcomes"]
        for course in range(2, 7):
            counts = Counter(row["initiator_candidate_roles"][str(course)] for row in rows)
            self.assertEqual(counts, {"first": 20, "second": 20,
                                      "third": 20, "outside_top3": 60})

    def test_no_assumed_2_course_makuri_sashi(self):
        rows = complete_pathway_catalog()["outcomes"]
        head2 = [r for r in rows if r["first_course"] == 2]
        self.assertEqual(len(head2), 20)
        self.assertTrue(all("makuri_sashi" not in r["first_possible_official_winning_methods"]
                            for r in head2))
        head3 = next(r for r in rows if r["first_course"] == 3)
        self.assertIn("makuri_sashi", head3["first_possible_official_winning_methods"])

    def test_course_swap_keeps_120_and_tracks_course_not_boat(self):
        x = complete_pathway_catalog({1: 3, 2: 2, 3: 1, 4: 4, 5: 5, 6: 6})
        rows = {r["ticket"]: r for r in x["outcomes"]}
        self.assertEqual(x["outcome_count"], 120)
        self.assertEqual(rows["3-4-5"]["first_course"], 1)
        self.assertIn("escape", rows["3-4-5"]["first_possible_official_winning_methods"])
        self.assertEqual(rows["1-4-5"]["first_course"], 3)
        self.assertNotIn("escape", rows["1-4-5"]["first_possible_official_winning_methods"])

    def test_all_5_attackers_x_all_rows_have_eligible_beneficiaries(self):
        for r in complete_pathway_catalog()["outcomes"]:
            self.assertEqual(set(r["initiator_candidate_roles"]), {"2", "3", "4", "5", "6"})
            self.assertEqual(set(r["hypothetical_attack_beneficiaries"]), {"2", "3", "4", "5", "6"})
            for course in range(2, 7):
                vals = r["hypothetical_attack_beneficiaries"][str(course)]
                self.assertEqual(len(vals), 2 if course in r["finish_courses"] else 3)
                self.assertTrue(all(v["beneficiary_course"] != course for v in vals))
            self.assertIsNone(r["actual_attack_observed"])
            self.assertIsNone(r["actual_beneficiary_causality_observed"])

    def test_invalid_permutations_rejected(self):
        bad = [{1:1}, {1:1,2:2,3:3,4:4,5:5,6:5},
               {1:1,2:2,3:3,4:4,5:5,6:"6"}, [1,2,3,4,5,6]]
        for x in bad:
            with self.subTest(x=x), self.assertRaisesRegex(ValueError, "six_unique"):
                complete_pathway_catalog(x)

    def test_no_probability_or_prod_claim(self):
        out = complete_pathway_catalog()
        for field in ("predicted_probabilities", "source_authenticated",
                      "results_read", "trained", "production_changed", "promotion_allowed"):
            self.assertIs(out[field], False)


if __name__ == "__main__":
    unittest.main()
