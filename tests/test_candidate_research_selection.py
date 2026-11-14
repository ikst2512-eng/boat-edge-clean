"""Read-only research shortlist regression: preserve all immutable race records."""
import json
import tempfile
import unittest
from pathlib import Path

from candidate_history import daily_candidate_history
from research_model import probabilities
from selection_dual import MINIMUM_CONFIDENCE


DAY = "20261108"
VERSION = "clean-prospective-national-beta0.4-v1"


def save(root, race, rates, *, version=VERSION, generated="2026-11-08T08:00:00+09:00"):
    code = DAY + "01" + f"{race:02d}"
    record = {
        "race_code": code,
        "status": "prospective_candidate",
        "formal": False, "validated": False, "scoring": False,
        "model_version": version,
        "predictions": ["1-2-3"],
        "generated_at": generated,
        "source_deadline_jst": "2026-11-08T15:00:00+09:00",
        "cutoff_jst": "2026-11-08T14:48:00+09:00",
        "source_title_received_jst": "2026-11-08T07:54:00+09:00",
        "source_cards_received_jst": "2026-11-08T07:55:00+09:00",
        "national_win_rates": rates,
    }
    (root / "prospective_predictions" / (code + ".json")).write_text(
        json.dumps(record), encoding="utf-8"
    )
    return code


class CandidateResearchSelectionTests(unittest.TestCase):
    def test_70_rule_only_filters_read_only_view_not_immutable_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "prospective_predictions").mkdir()
            high = [6.34, 3.02, 3.93, 3.08, 4.53, 5.43]
            low = [3.45, 5.88, 5.87, 5.62, 3.89, 6.28]
            pass_code = save(root, 1, high)
            below_code = save(root, 2, low)
            unknown_code = save(root, 3, high, version="unrecognized-model")
            invalid_code = save(
                root, 4, high, generated="2026-11-08T14:50:00+09:00"
            )
            status, manifest = daily_candidate_history(DAY, root)
            self.assertEqual(status, 200)
            self.assertEqual(manifest["selection_rule"], "top2_head_mass_ge_70_research_only_v1")
            self.assertEqual(manifest["candidate_count"], 4)
            self.assertEqual(manifest["research_70_pass_count"], 1)
            self.assertEqual(manifest["research_70_below_count"], 1)
            self.assertEqual(manifest["research_unassessed_count"], 2)
            self.assertEqual(manifest["payout_verified_count"], 0)
            by_code = {row["race_code"]: row for row in manifest["races"]}
            self.assertEqual(
                (by_code[pass_code]["selection_status"], by_code[below_code]["selection_status"]),
                ("research_70_pass", "research_70_below"),
            )
            self.assertEqual(by_code[unknown_code]["selection_status"], "unassessed")
            self.assertIsNone(by_code[unknown_code]["head_top2_model_pct"])
            self.assertEqual(by_code[invalid_code]["forecast_status"], "unverified")
            self.assertEqual(by_code[invalid_code]["selection_status"], "unassessed")
            self.assertEqual(set(by_code), {pass_code, below_code, unknown_code, invalid_code})
            heads = {
                boat: sum(p for ticket, p in probabilities(high) if ticket[0] == boat)
                for boat in range(1, 7)
            }
            expected = round(100 * sum(sorted(heads.values(), reverse=True)[:2]), 2)
            self.assertGreaterEqual(expected, MINIMUM_CONFIDENCE * 100)
            self.assertEqual(by_code[pass_code]["head_top2_model_pct"], expected)
            # A second read must not mutate frozen inputs or change classification.
            again_status, again = daily_candidate_history(DAY, root)
            self.assertEqual(again_status, 200)
            self.assertEqual(again, manifest)


if __name__ == "__main__":
    unittest.main()
