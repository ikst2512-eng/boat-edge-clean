"""Synthetic only: never equate another race's evidence to a candidate."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from position_sensitive_cross_pr_t12_bridge import (
    assess_cross_pr_blockers, COMPONENTS, SCHEMA, _read_json_file,
)


def source(code, racelist, exhibition, post_source, source_remote):
    fields = {k: False for k in COMPONENTS}
    fields.update({
        "official_racelist_original": racelist,
        "official_beforeinfo_original": True,
        "official_odds_original": True,
        "six_boat_exhibition_complete": exhibition,
        "official_t12_source_cutoff_met": True,
        "independent_source_archive_server_publication_by_t12": source_remote,
        "frozen_forecast_generated_after_all_originals": post_source,
    })
    return {
        "race_code": code,
        "day_jst": code[:8],
        **fields,
        "same_race_three_source_readiness": racelist and exhibition,
        "formal": False,
        "missing_requirements": ["synthetic_missing_provenance"],
    }


def report():
    rows = [
        source("202611030112", True, False, False, False),
        source("202611091110", False, True, False, True),
        source("202611091710", False, True, False, True),
    ]
    return {
        "schema": "T12_SAME_RACE_INDEPENDENT_PROOF_CHAIN_V1",
        "cross_race_original_combination_allowed": False,
        "formal": False, "t12_eligible": False,
        "accuracy_scoring_allowed": False,
        "new_formal_certifications": 0,
        "formal_accuracy_denominator": None,
        "races_compared": len(rows),
        "fully_qualified_same_race_three_original_t12_sources": 0,
        "forecasts_generated_after_all_originals": 0,
        "races": rows,
    }


class CrossPrSourceBridgeTests(unittest.TestCase):
    def test_same_race_three_historical_gaps_no_stitching(self):
        codes = ["202611030112", "202611091110", "202611091710"]
        d = assess_cross_pr_blockers(report(), codes)
        self.assertEqual(d["schema"], SCHEMA)
        self.assertEqual(d["matched_upstream_race_codes"], 3)
        self.assertEqual(d["new_formal_pilot_slots"], 0)
        self.assertEqual(d["new_formal_confirmation_slots"], 0)
        self.assertEqual(d["by_race"][0]["blockers"].count("six_boat_exhibition_complete"), 1)
        for row in d["by_race"][1:]:
            self.assertIn("official_racelist_original", row["blockers"])
        for k in ("formal", "model_improvement_proven", "promotion_allowed",
                  "production_changed", "outcomes_read",
                  "historical_upstream_report_self_authenticated",
                  "candidate_remote_first_receipt_independently_verified"):
            self.assertFalse(d[k], k)

    def test_no_source_does_not_borrow_other_race(self):
        d = assess_cross_pr_blockers(report(), ["202611090101"])
        self.assertEqual(d["matched_upstream_race_codes"], 0)
        self.assertEqual(d["unmatched_candidate_codes"], 1)
        self.assertEqual(d["by_race"][0]["blockers"],
                         ["no_same_race_upstream_source_report"])

    def test_empty_candidate_roster_not_formal(self):
        d = assess_cross_pr_blockers(report(), [])
        self.assertEqual(d["input_candidate_codes"], 0)
        self.assertFalse(d["formal"])

    def test_duplicate_candidate_not_reused_to_fill_denominator(self):
        with self.assertRaisesRegex(ValueError, "candidate_roster_duplicate"):
            assess_cross_pr_blockers(report(), ["202611091110"] * 2)

    def test_duplicate_source_race_cannot_be_combined(self):
        r = report()
        r["races"][0]["race_code"] = "202611091110"
        r["races"][0]["day_jst"] = "20261109"
        with self.assertRaisesRegex(ValueError, "duplicate_or_cross_day_source_row"):
            assess_cross_pr_blockers(r, ["202611091110"])

    def test_mismatched_race_day_rejected(self):
        r = report()
        r["races"][0]["day_jst"] = "20261109"
        with self.assertRaisesRegex(ValueError, "duplicate_or_cross_day_source_row"):
            assess_cross_pr_blockers(r, [])

    def test_false_full_triad_upgrade_rejected(self):
        r = report()
        r["races"][0]["same_race_three_source_readiness"] = True
        with self.assertRaisesRegex(ValueError, "triad_completeness_disagrees"):
            assess_cross_pr_blockers(r, [])

    def test_false_aggregate_upgrade_rejected(self):
        r = report()
        r["fully_qualified_same_race_three_original_t12_sources"] = 1
        with self.assertRaisesRegex(ValueError, "aggregate_component_disagreement"):
            assess_cross_pr_blockers(r, [])

    def test_forged_formal_and_accuracy_counter_rejected(self):
        for field, value in (("formal", True),
                             ("new_formal_certifications", 3),
                             ("formal_accuracy_denominator", 3),
                             ("accuracy_scoring_allowed", True)):
            r = report()
            r[field] = value
            with self.assertRaisesRegex(ValueError, "upstream_report_overclaims"):
                assess_cross_pr_blockers(r, [])

    def test_missing_blocker_or_unsupported_bool_rejected(self):
        r = report()
        r["races"][1]["missing_requirements"] = []
        with self.assertRaisesRegex(ValueError, "missing_source_blocker"):
            assess_cross_pr_blockers(r, [])
        r = report()
        r["races"][1]["official_odds_original"] = 1
        with self.assertRaisesRegex(ValueError, "missing_untyped_source_component"):
            assess_cross_pr_blockers(r, [])

    def test_matching_complete_self_claim_never_promotes(self):
        r = report()
        x = r["races"][0]
        for key in COMPONENTS:
            x[key] = True
        x["same_race_three_source_readiness"] = True
        r["fully_qualified_same_race_three_original_t12_sources"] = 1
        r["forecasts_generated_after_all_originals"] = 1
        d = assess_cross_pr_blockers(r, [x["race_code"]])
        self.assertIn("upstream_authenticity_and_candidate_receipts_not_verified_here",
                      d["by_race"][0]["blockers"])
        self.assertFalse(d["by_race"][0]["eligible_for_300_plus_300"])
        self.assertFalse(d["formal"])

    def test_unrecognized_source_format_fails(self):
        r = report()
        r["schema"] = "SOME_OTHER_REPORT"
        with self.assertRaisesRegex(ValueError, "upstream_report_overclaims"):
            assess_cross_pr_blockers(r, ["202611091110"])


    def test_readonly_json_inputs_and_reject_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source.json"
            roster = Path(td) / "candidate.json"
            source.write_text(json.dumps(report()), encoding="utf-8")
            roster.write_text(json.dumps(["202611091110"]), encoding="utf-8")
            d = assess_cross_pr_blockers(_read_json_file(source, 250000),
                                         _read_json_file(roster, 30000))
            self.assertEqual(d["matched_upstream_race_codes"], 1)
            self.assertFalse(d["formal"])
            source.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate_json_key"):
                _read_json_file(source, 250000)

    def test_readonly_json_refuses_symlink_and_oversize(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "oversize.json"
            p.write_text(json.dumps(report()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe_json_report_path"):
                _read_json_file(p, 5)
            link = Path(td) / "link.json"
            link.symlink_to(p)
            with self.assertRaisesRegex(ValueError, "unsafe_json_report_path"):
                _read_json_file(link, 250000)


if __name__ == "__main__":
    unittest.main()
