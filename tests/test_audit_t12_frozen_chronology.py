import unittest

from scripts.audit_t12_frozen_chronology import inspect

RACE = "202611080309"
CUTOFF = "2026-11-08T14:18:00+09:00"
BEFORE = "2026-11-08T14:15:38.139739+09:00"
ODDS = "2026-11-08T14:15:48.378360+09:00"


def pair(**overrides):
    return {
        "race_code": RACE,
        "cutoff_jst": CUTOFF,
        "before_received_jst": BEFORE,
        "odds_received_jst": ODDS,
        "originals_hash_verified": True,
        "both_complete_before_t12": True,
        **overrides,
    }


def clean(**overrides):
    return {"race_code": RACE,
            "generated_at": "2026-11-08T10:12:31.149675+09:00",
            "formal": False, **overrides}


class FrozenChronologyAuditTests(unittest.TestCase):
    def test_real_edogawa_frozen_clean_predates_official_originals(self):
        result = inspect(pair(), clean())
        self.assertTrue(result["source_pair_sha_verified"])
        self.assertTrue(result["two_source_complete_before_t12"])
        self.assertTrue(result["source_receipts_before_t12"])
        self.assertFalse(result["forecast_generated_after_official_pair"])
        self.assertGreater(result["last_source_minus_generation_seconds"], 14000)
        self.assertIn("official_original_received_after_frozen_forecast",
                      result["missing_requirements"])
        self.assertFalse(result["accuracy_scoring_allowed"])
        self.assertFalse(result["formal"])

    def test_real_v2_beforeinfo_is_not_in_10_17_frozen_snapshot(self):
        v2 = {"race_code": RACE,
              "generated_at_jst": "2026-11-08T10:17:12.313648+09:00",
              "beforeinfo": "optional_not_in_snapshot"}
        report = inspect(pair(), v2)
        self.assertIn("official_beforeinfo_absent_from_frozen_snapshot",
                      report["missing_requirements"])
        self.assertFalse(report["forecast_usable"])

    def test_exact_same_receipt_and_generation_time_is_not_proof_of_order(self):
        equal = clean(generated_at=ODDS)
        result = inspect(pair(), equal)
        self.assertFalse(result["forecast_generated_after_official_pair"])
        self.assertIn("official_original_received_after_frozen_forecast",
                      result["missing_requirements"])
        self.assertFalse(result["accuracy_scoring_allowed"])

    def test_later_prospective_forecast_still_lacks_third_original_and_linkage(self):
        later = clean(generated_at="2026-11-08T14:16:01+09:00")
        report = inspect(pair(), later)
        self.assertTrue(report["forecast_generated_after_official_pair"])
        self.assertTrue(report["forecast_generated_before_t12"])
        self.assertIn("official_racelist_original_not_in_two_source_archive",
                      report["missing_requirements"])
        self.assertIn("official_originals_not_linked_to_frozen_model_inputs",
                      report["missing_requirements"])
        self.assertFalse(report["full_t12_source_certified"])

    def test_incomplete_naruto_pair_not_eligible(self):
        report = inspect(pair(both_complete_before_t12=False), clean())
        self.assertIn("two_originals_incomplete", report["missing_requirements"])
        self.assertFalse(report["t12_eligible"])

    def test_unhashed_or_late_originals_never_pass(self):
        report = inspect(pair(originals_hash_verified=False,
                              odds_received_jst="2026-11-08T14:19:01+09:00"), clean())
        self.assertIn("two_originals_not_hash_verified", report["missing_requirements"])
        self.assertIn("official_original_received_after_t12", report["missing_requirements"])

    def test_after_cutoff_forecast_never_passes(self):
        report = inspect(pair(), clean(generated_at="2026-11-08T14:19:01+09:00"))
        self.assertIn("frozen_forecast_generated_after_t12",
                      report["missing_requirements"])
        self.assertFalse(report["accuracy_scoring_allowed"])

    def test_mismatched_race_never_pairs(self):
        with self.assertRaisesRegex(ValueError, "race identity mismatch"):
            inspect(pair(), clean(race_code="202611081409"))
        with self.assertRaisesRegex(ValueError, "invalid audited source race"):
            inspect(pair(race_code="bad"), clean())

    def test_naive_or_utc_or_missing_timestamp_rejected(self):
        for bad in ("2026-11-08T14:15:38", "2026-11-08T05:15:38+00:00",
                    None, "not-a-timestamp"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                inspect(pair(before_received_jst=bad), clean())

    def test_ambiguous_generation_field_and_missing_generation_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            inspect(pair(), {**clean(), "generated_at_jst": "2026-11-08T10:12:31+09:00"})
        with self.assertRaisesRegex(ValueError, "exactly one"):
            inspect(pair(), {"race_code": RACE})

    def test_cross_day_source_or_forecast_rejected(self):
        with self.assertRaisesRegex(ValueError, "cross-day"):
            inspect(pair(odds_received_jst="2026-11-09T00:01:01+09:00"), clean())
        with self.assertRaisesRegex(ValueError, "cross-day"):
            inspect(pair(), clean(generated_at="2026-11-07T15:00:00+09:00"))

    def test_nonobjects_rejected(self):
        with self.assertRaisesRegex(ValueError, "must be objects"):
            inspect([], clean())
        with self.assertRaisesRegex(ValueError, "must be objects"):
            inspect(pair(), None)


if __name__ == "__main__":
    unittest.main()
