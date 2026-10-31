import json
import tempfile
import unittest
from pathlib import Path

from scripts.research_prerace_feature_audit import analyze


class PreRaceFeatureAuditTests(unittest.TestCase):
    def test_valid_holdout_and_invalid_evidence_are_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "research_snapshots").mkdir()
            (root / "confirmed_results").mkdir()
            forecast = {
                "race_code": "202610300101", "status": "research", "validated": False,
                "generated_at": "2026-10-30T09:03:00+09:00",
                "cutoff_jst": "2026-10-30T09:10:00+09:00",
                "source_deadline_jst": "2026-10-30T09:22:00+09:00",
                "source_title_received_jst": "2026-10-30T09:01:00+09:00",
                "source_cards_received_jst": "2026-10-30T09:02:00+09:00",
                "national_win_rates": [8, 6, 6, 6, 6, 6],
                "predictions": ["1-2-3","1-2-4","1-2-5","1-2-6","1-3-2","1-3-4","1-3-5","1-3-6","1-4-2","1-4-3"]
            }
            result = {"race_code": "202610300101", "status": "confirmed", "confirmed_at_jst": "2026-10-30T09:50:00+09:00", "finish_order": [1, 2, 3]}
            fp = root / "research_snapshots" / "202610300101.json"
            rp = root / "confirmed_results" / "202610300101.json"
            rp.write_text(json.dumps(result))
            fp.write_text(json.dumps(forecast))
            good = analyze(root)
            self.assertEqual(good["cohorts"]["holdout"]["all"]["n"], 1)
            self.assertEqual(good["saved_advanced_feature_presence"]["holdout"]["records"], 1)
            self.assertTrue(all(v==0 for v in good["saved_advanced_feature_presence"]["holdout"]["direct_fields"].values()))
            self.assertEqual(good["cohorts"]["holdout"]["lane1_strongest"]["selection_pct"], 100.0)
            self.assertEqual(good["cohorts"]["holdout"]["lane1_strongest"]["lift_pp"], 0.0)
            self.assertFalse(good["cohorts"]["holdout"]["lane1_strongest"]["sample_sufficient_30"])
            self.assertIsNone(good["cohorts"]["holdout"]["lane1_not_strongest"]["lift_pp"])
            self.assertEqual(good["cohorts"]["holdout"]["lane1_lead_2plus"]["top10"], 1)
            self.assertEqual(good["cohorts"]["holdout"]["lane1_strongest"]["head1_actual"], 1)
            self.assertEqual(good["cohorts"]["holdout"]["lane1_strongest"]["head1_top10_hit"], 1)
            self.assertEqual(good["cohorts"]["holdout"]["lane1_strongest"]["head1_top10_miss"], 0)
            self.assertEqual(good["cohorts"]["holdout"]["lane1_strongest"]["top3"], 1)
            fp.write_text(json.dumps({**forecast, "predictions": forecast["predictions"][1:] + ["2-1-3"]}))
            missed = analyze(root)["cohorts"]["holdout"]["lane1_strongest"]
            self.assertEqual(missed["head1_actual"], 1)
            self.assertEqual(missed["head1_top10_miss"], 1)
            details = analyze(root)["strongest_lane1_head1_top10_misses"]["holdout"]
            self.assertEqual(len(details), 1)
            self.assertEqual(details[0]["race_code"], "202610300101")
            self.assertEqual(details[0]["winning_ticket"], "1-2-3")
            self.assertEqual((details[0]["second_boat"], details[0]["third_boat"]), (2, 3))
            self.assertEqual(details[0]["top10_head1_tickets"], 9)
            self.assertEqual(missed["head1_top10_hit"], 0)
            fp.write_text(json.dumps(forecast))
            self.assertEqual(good["cohorts"]["holdout"]["lane1_unique_strongest"]["n"], 1)
            self.assertEqual(good["cohorts"]["holdout"]["lane1_tied_strongest"]["n"], 0)
            fp.write_text(json.dumps({**forecast, "national_win_rates": [8, 8, 6, 6, 6, 6]}))
            tied = analyze(root)
            self.assertEqual(tied["cohorts"]["holdout"]["lane1_strongest"]["n"], 1)
            self.assertEqual(tied["cohorts"]["holdout"]["lane1_unique_strongest"]["n"], 0)
            self.assertEqual(tied["cohorts"]["holdout"]["lane1_tied_strongest"]["n"], 1)
            classes = ("lane1_unique_strongest", "lane1_tied_strongest", "lane1_not_strongest")
            self.assertEqual(sum(tied["cohorts"]["holdout"][name]["n"] for name in classes),
                             tied["cohorts"]["holdout"]["all"]["n"])
            self.assertEqual(sum(tied["cohorts"]["holdout"][name]["top10"] for name in classes),
                             tied["cohorts"]["holdout"]["all"]["top10"])
            rp.write_text(json.dumps({**result, "confirmed_at_jst": "2026-10-30T09:21:00+09:00"}))
            self.assertEqual(analyze(root)["rejected"], 1)
            rp.write_text(json.dumps(result))
            fp.write_text(json.dumps(forecast))
            fp.write_text(json.dumps({**forecast, "model_version":"national-beta0.4-exploratory-v1"}))
            self.assertEqual(analyze(root)["rejected"], 1)
            fp.write_text(json.dumps(forecast))
            self.assertEqual(good["cohorts"]["discovery"]["all"]["n"], 0)
            for change in (
                {"national_win_rates": "bad"},
                {"national_win_rates": [True, 6, 6, 6, 6, 6]},
                {"generated_at": "2026-10-30T09:00:00"},
                {"generated_at": "2026-10-30T09:30:00+09:00"},
                {"source_cards_received_jst": "2026-10-30T09:11:00+09:00"},
                {"source_deadline_jst": "2026-10-30T09:23:00+09:00"},
                {"validated": True},
                {"model_version": "other-model-v2"},
                {"generated_at": "2026-10-30T08:59:00+09:00"},
                {"source_deadline_jst": "2026-10-31T09:22:00+09:00", "cutoff_jst": "2026-10-31T09:10:00+09:00"},
            ):
                fp.write_text(json.dumps({**forecast, **change}))
                audited = analyze(root)
                self.assertEqual(audited["cohorts"]["holdout"]["all"]["n"], 0)
                self.assertEqual(audited["rejected"], 1)


if __name__ == "__main__":
    unittest.main()
