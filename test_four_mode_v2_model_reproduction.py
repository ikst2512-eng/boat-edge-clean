import json
import tempfile
import unittest
from pathlib import Path

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_v2_model_reproduction import audit, VERSION

RATES = [6.2, 5.1, 4.5, 5.4, 3.8, 4.9]


def fixture(root, race_code="202611030101", tamper=False, rates=None):
    rates = RATES if rates is None else rates
    folder = root / "four_mode_forecasts"
    folder.mkdir(exist_ok=True)
    modes = rank_modes(probabilities(rates))
    if tamper:
        modes["hit"]["tickets"][0]["p"] += 0.01
    obj = {
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "race_code": race_code,
        "generated_at_jst": "2026-11-03T11:00:00+09:00",
        "deadline_jst": "2026-11-03T12:00:00+09:00",
        "model_version": VERSION,
        "input_national_win_rates": rates,
        "modes": modes,
    }
    (folder / (race_code + ".json")).write_text(json.dumps(obj), encoding="utf-8")


class ReproductionTests(unittest.TestCase):
    def test_exact_saved_v2_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            report = audit(root)
            self.assertEqual(report["valid_v2_archives"], 1)
            self.assertEqual(report["exact_ticket_and_probability_matches"], 1)
            self.assertEqual(report["verified_reproductions_for_bias"], 1)
            self.assertEqual(sum(report["boat1_rate_rank_distribution"].values()), 1)
            self.assertGreater(report["boat1_mean_head_probability"], 0)
            self.assertEqual(sum(report["head_prior_1000_counts"]), 1000)
            self.assertEqual(report["mismatch_count"], 0)
            self.assertEqual(sum(report["hit_top3_signatures"].values()), 1)
            self.assertFalse(report["formal"])

    def test_detects_valid_but_nonreproducible_probability(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root, tamper=True)
            report = audit(root)
            self.assertEqual(report["valid_v2_archives"], 1)
            self.assertEqual(report["mismatch_count"], 1)
            self.assertEqual(report["mismatch_examples"], ["202611030101"])

    def test_rate_nonmax_and_exactly_reproduced_counts_as_model_bias_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lower_boat1 = [5.2, 6.1, 4.5, 5.4, 3.8, 4.9]
            fixture(root, rates=lower_boat1)
            report = audit(root)
            self.assertEqual(report["boat1_rate_not_max"], 1)
            self.assertEqual(report["boat1_rate_not_max_but_top1_head1"],
                             int(rank_modes(probabilities(lower_boat1))["hit"]["tickets"][0]["combo"][0] == "1"))

    def test_mismatch_is_excluded_from_structural_attribution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root, tamper=True)
            report = audit(root)
            self.assertEqual(report["valid_v2_archives"], 1)
            self.assertEqual(report["verified_reproductions_for_bias"], 0)
            self.assertEqual(report["boat1_rate_not_max"], 0)
            self.assertIsNone(report["boat1_mean_head_probability"])

    def test_same_first_place_conditional_ratios_independent_of_rates(self):
        # The 6 input rates can change the HEAD mass, not the relative
        # 2nd/3rd distribution conditional on a particular first-place boat.
        a = dict(probabilities([7, 6, 5, 4, 3, 2]))
        b = dict(probabilities([2, 3, 4, 5, 6, 7]))
        for first in range(1, 7):
            t1 = (first, (first % 6) + 1, ((first + 1) % 6) + 1)
            t2 = (first, ((first + 2) % 6) + 1, ((first + 3) % 6) + 1)
            self.assertAlmostEqual(a[t1] / a[t2], b[t1] / b[t2], places=12)

    def test_absent_archive_does_not_claim_reproduction(self):
        with tempfile.TemporaryDirectory() as td:
            report = audit(td)
            self.assertEqual(report["status"], "no_forecast_directory")
            self.assertEqual(report["exact_ticket_and_probability_matches"], 0)


if __name__ == "__main__":
    unittest.main()
