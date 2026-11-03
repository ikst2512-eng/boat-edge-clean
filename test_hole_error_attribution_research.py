"""Frozen-result-blind selection and second-pair/third-miss attribution tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hole_error_attribution_research import failure_class, inspect

CODE = "202611040101"
BASE = ["1-2-3", "1-2-4", "1-3-2", "1-3-4", "1-4-2",
        "1-4-3", "1-4-5", "1-2-5", "1-3-5", "1-2-6"]
DONOR = BASE[:5] + ["1-5-2", "1-6-2"] + BASE[5:8]
SCORE = BASE[:5] + ["1-5-3", "1-6-3"] + BASE[5:8]


class AttributionTests(unittest.TestCase):
    def test_failure_hierarchy_head_second_pair_third(self):
        self.assertEqual(failure_class(BASE, "2-3-4"), "first_head_absent")
        self.assertEqual(failure_class(BASE, "1-5-3"), "second_pair_absent")
        self.assertEqual(failure_class(BASE, "1-2-5"), "hit")
        self.assertEqual(failure_class(BASE, "1-2-6"), "hit")
        self.assertEqual(failure_class(BASE[:2], "1-2-5"), "third_boat_absent")

    def test_wrong_third_is_separate_from_new_second_pair(self):
        # Candidate construction must complete before confirmed result access.
        events = []
        def selector(archive, rates):
            events.append("select")
            return {"baseline": BASE, "donor_order": DONOR,
                    "max_ticket_score": SCORE,
                    "third_national_rate": SCORE}
        def outcome(code, root):
            events.append("result")
            return {"status": "historical_comparison_only",
                    "winning_ticket": "1-5-3"}
        archive = {"modes": {
            "hit": {"tickets": [{"combo": "1-5-2"}, {"combo": "1-5-3"}]},
            "balance": {"tickets": [{"combo": "1-6-3"}]}}}
        with tempfile.TemporaryDirectory() as directory, patch(
            "hole_error_attribution_research.archived_four_modes",
            return_value=(200, archive)), patch(
            "hole_error_attribution_research.national_rates",
            return_value=None), patch(
            "hole_error_attribution_research.variants",
            side_effect=selector), patch(
            "hole_error_attribution_research.compare_race",
            side_effect=outcome):
            output = inspect([CODE], directory)
        self.assertEqual(events, ["select", "result"])
        self.assertEqual(output["comparable"], 1)
        self.assertEqual(output["miss_reasons"]["baseline"], {"second_pair_absent": 1})
        self.assertEqual(output["miss_reasons"]["donor_order"], {"third_boat_absent": 1})
        self.assertEqual(output["miss_reasons"]["third_national_rate"], {"hit": 1})
        self.assertEqual(output["missing_pair_recovery"]["donor_order"]["third_still_wrong"], 1)
        self.assertEqual(output["missing_pair_recovery"]["third_national_rate"]["full_ticket_added"], 1)
        self.assertEqual(output["topn"]["third_national_rate"]["top10"]["gained"], 1)
        self.assertEqual(output["topn"]["third_national_rate"]["top5"]["gained"], 0)
        self.assertEqual(output["missing_pair_recovery"]["donor_order"]["winner_in_donor_tickets"], 1)
        self.assertEqual(output["third_choice_gaps"]["donor_order"]["correct_pair_wrong_third"], 1)
        self.assertEqual(output["third_choice_gaps"]["donor_order"]["winner_available_in_donors"], 1)
        self.assertEqual(output["third_choice_gaps"]["donor_order"]["multiple_donor_thirds"], 1)
        self.assertEqual(output["missing_pair_recovery"]["donor_order"]["third_wrong_but_winner_in_donors"], 1)

    def test_correct_pair_wrong_third_without_donor_candidate_is_distinct(self):
        archive = {"modes": {
            "hit": {"tickets": [{"combo": "1-5-2"}]},
            "balance": {"tickets": []}}}
        chosen = {"baseline": BASE, "donor_order": DONOR,
                  "max_ticket_score": DONOR, "third_national_rate": DONOR}
        with patch("hole_error_attribution_research.archived_four_modes",
                   return_value=(200, archive)), patch(
             "hole_error_attribution_research.national_rates", return_value=None), patch(
             "hole_error_attribution_research.variants", return_value=chosen), patch(
             "hole_error_attribution_research.compare_race",
             return_value={"status": "historical_comparison_only",
                           "winning_ticket": "1-5-3"}):
            result = inspect([CODE], Path("."))
        gap=result["third_choice_gaps"]["donor_order"]
        self.assertEqual(gap["correct_pair_wrong_third"], 1)
        self.assertEqual(gap["winner_absent_from_donors"], 1)
        self.assertEqual(gap["one_donor_third"], 1)
        self.assertEqual(result["missing_pair_recovery"]["donor_order"]
                         ["third_wrong_and_winner_not_in_donors"], 1)

    def test_same_existing_pair_wrong_third_not_mislabelled_as_pair_recovery(self):
        archive = {"modes": {"hit": {"tickets": [{"combo": "1-2-6"}]},
                             "balance": {"tickets": []}}}
        chosen = {p: BASE for p in
                  ("baseline", "donor_order",
                   "max_ticket_score", "third_national_rate")}
        with patch("hole_error_attribution_research.archived_four_modes",
                   return_value=(200, archive)), patch(
             "hole_error_attribution_research.national_rates", return_value=None), patch(
             "hole_error_attribution_research.variants", return_value=chosen), patch(
             "hole_error_attribution_research.compare_race",
             return_value={"status": "historical_comparison_only",
                           "winning_ticket": "1-2-6"}):
            result = inspect([CODE], Path("."))
        self.assertEqual(result["third_choice_gaps"]["baseline"], {})
        self.assertEqual(result["missing_pair_recovery"]["donor_order"], {})

    def test_pending_result_not_used_as_a_scored_hit(self):
        archive = {"modes": {"hit": {"tickets": []}, "balance": {"tickets": []}}}
        with patch("hole_error_attribution_research.archived_four_modes",
                   return_value=(200, archive)), patch(
             "hole_error_attribution_research.national_rates", return_value=None), patch(
             "hole_error_attribution_research.variants",
             return_value={p: BASE for p in
                           ("baseline", "donor_order",
                            "max_ticket_score", "third_national_rate")}), patch(
             "hole_error_attribution_research.compare_race",
             return_value={"status": "result_pending"}):
            out = inspect([CODE], Path("."))
        self.assertEqual(out["comparable"], 0)
        self.assertEqual(out["unavailable"], {"result_unconfirmed": 1})
        self.assertEqual(out["topn"]["baseline"]["top10"]["hits"], 0)


if __name__ == "__main__":
    unittest.main()
