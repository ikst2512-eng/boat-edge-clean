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
        "exhibition_complete": True,
        "odds_120_complete": True,
        "component_checks": {
            "six_unique_boats": True,
            "exhibition_time_six": True,
            "tilt_six": True,
            "start_exhibition_six": True,
            "beforeinfo_received_by_t12": True,
            "official_odds_120": True,
            "odds_received_by_t12": True,
        },
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

    def test_nov05_biwako11_replayed_pair_still_predates_frozen_clean(self):
        # Receipt times correspond to original ZIP artifact 13391673467;
        # this test is a chronology fixture, not a raw-byte replay.
        source = pair(
            race_code="202611051111",
            cutoff_jst="2026-11-05T14:54:00+09:00",
            before_received_jst="2026-11-05T14:50:49.136632+09:00",
            odds_received_jst="2026-11-05T14:50:58.419703+09:00",
        )
        pred = clean(
            race_code="202611051111",
            generated_at="2026-11-05T11:04:24.496897+09:00",
            input_source_kind="public_pre_race_csv",
        )
        checked = inspect(source, pred)
        self.assertTrue(checked["two_source_complete_before_t12"])
        self.assertFalse(checked["forecast_generated_after_official_pair"])
        self.assertAlmostEqual(checked["last_source_minus_generation_seconds"],
                               13593.923, places=3)
        self.assertIn("frozen_input_public_csv_not_official_originals",
                      checked["missing_requirements"])
        self.assertFalse(checked["accuracy_scoring_allowed"])

    def test_nov06_naruto10_replayed_pair_still_predates_frozen_clean(self):
        # Receipt times correspond to original ZIP artifact 13480945699.
        source = pair(
            race_code="202611061410",
            cutoff_jst="2026-11-06T14:53:00+09:00",
            before_received_jst="2026-11-06T14:47:38.371341+09:00",
            odds_received_jst="2026-11-06T14:47:48.721444+09:00",
        )
        pred = clean(
            race_code="202611061410",
            generated_at="2026-11-06T10:15:39.642861+09:00",
            input_source_kind="public_pre_race_csv",
        )
        checked = inspect(source, pred)
        self.assertTrue(checked["two_source_complete_before_t12"])
        self.assertFalse(checked["forecast_generated_after_official_pair"])
        self.assertAlmostEqual(checked["last_source_minus_generation_seconds"],
                               16329.079, places=3)
        self.assertIn("official_original_received_after_frozen_forecast",
                      checked["missing_requirements"])
        self.assertFalse(checked["full_t12_source_certified"])

    def test_nov05_nov06_nov08_frozen_v2_missing_official_beforeinfo(self):
        historical = (
            ("202611051111", "2026-11-05T14:54:00+09:00",
             "2026-11-05T14:50:49.136632+09:00",
             "2026-11-05T14:50:58.419703+09:00",
             "2026-11-05T11:15:10.119704+09:00"),
            ("202611061410", "2026-11-06T14:53:00+09:00",
             "2026-11-06T14:47:38.371341+09:00",
             "2026-11-06T14:47:48.721444+09:00",
             "2026-11-06T10:15:36.394911+09:00"),
            (RACE, CUTOFF, BEFORE, ODDS,
             "2026-11-08T10:17:12.313648+09:00"),
        )
        for race, cutoff, before, odds, generation in historical:
            with self.subTest(race=race):
                source = pair(race_code=race, cutoff_jst=cutoff,
                              before_received_jst=before,
                              odds_received_jst=odds)
                frozen_v2 = {
                    "race_code": race, "generated_at_jst": generation,
                    "beforeinfo": "optional_not_in_snapshot",
                }
                checked = inspect(source, frozen_v2)
                self.assertTrue(checked["two_source_complete_before_t12"])
                self.assertFalse(checked["forecast_generated_after_official_pair"])
                self.assertIn("official_beforeinfo_absent_from_frozen_snapshot",
                              checked["missing_requirements"])
                self.assertFalse(checked["formal"])
                self.assertFalse(checked["forecast_usable"])

    def test_real_clean_public_csv_not_mistaken_for_official_originals(self):
        frozen = clean(input_source_kind="public_pre_race_csv")
        result = inspect(pair(), frozen)
        self.assertEqual(result["frozen_input_source_kind"], "public_pre_race_csv")
        self.assertIn("frozen_input_public_csv_not_official_originals",
                      result["missing_requirements"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["accuracy_scoring_allowed"])

    def test_missing_input_kind_does_not_gain_official_certification(self):
        result = inspect(pair(), clean())
        self.assertIsNone(result["frozen_input_source_kind"])
        self.assertIn("official_originals_not_linked_to_frozen_model_inputs",
                      result["missing_requirements"])
        self.assertFalse(result["full_t12_source_certified"])

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

    def test_aggregate_pair_flag_cannot_mask_missing_6_boat_components(self):
        values = pair()
        components = {**values["component_checks"],
                      "start_exhibition_six": False}
        report = inspect(pair(component_checks=components), clean())
        self.assertFalse(report["official_component_checks_verified"])
        self.assertFalse(report["two_source_complete_before_t12"])
        self.assertIn("official_pair_component_checks_missing_or_false",
                      report["missing_requirements"])
        self.assertFalse(report["formal"])

    def test_aggregate_flag_cannot_mask_exhibition_or_odds_failure(self):
        for problem, blocked in (
            ({"exhibition_complete": False},
             "official_exhibition_six_incomplete_or_unverified"),
            ({"odds_120_complete": False},
             "official_120_odds_incomplete_or_unverified"),
        ):
            with self.subTest(problem=problem):
                report = inspect(pair(**problem), clean())
                self.assertFalse(report["two_source_complete_before_t12"])
                self.assertIn(blocked, report["missing_requirements"])
                self.assertFalse(report["accuracy_scoring_allowed"])

    def test_missing_or_truthy_component_flags_are_not_evidence(self):
        with self.subTest("missing dictionary"):
            report = inspect(pair(component_checks=None), clean())
            self.assertFalse(report["two_source_complete_before_t12"])
        with self.subTest("missing key"):
            report = inspect(pair(component_checks={"six_unique_boats": True}), clean())
            self.assertFalse(report["two_source_complete_before_t12"])
        with self.subTest("truthy number"):
            flags = {**pair()["component_checks"], "official_odds_120": 1}
            report = inspect(pair(component_checks=flags), clean())
            self.assertFalse(report["two_source_complete_before_t12"])
        for value in (1, "true", None):
            with self.subTest(aggregate=value):
                report = inspect(pair(both_complete_before_t12=value), clean())
                self.assertFalse(report["two_source_complete_before_t12"])
                self.assertFalse(report["t12_eligible"])

    def test_official_component_diagnostics_are_recorded_on_positive_pair(self):
        report = inspect(pair(), clean())
        self.assertTrue(report["official_component_checks_verified"])
        self.assertTrue(report["official_exhibition_six_complete"])
        self.assertTrue(report["official_odds_120_complete"])
        self.assertTrue(report["two_source_complete_before_t12"])
        self.assertFalse(report["formal"])

    def test_unhashed_or_late_originals_never_pass(self):
        report = inspect(pair(originals_hash_verified=False,
                              odds_received_jst="2026-11-08T14:19:01+09:00"), clean())
        self.assertIn("two_originals_not_hash_verified", report["missing_requirements"])
        self.assertIn("official_original_received_after_t12", report["missing_requirements"])
        self.assertFalse(report["two_source_complete_before_t12"])
        self.assertFalse(report["formal"])

    def test_aggregate_true_with_late_source_does_not_report_complete(self):
        report = inspect(pair(odds_received_jst="2026-11-08T14:19:01+09:00"),
                         clean())
        self.assertTrue(report["official_component_checks_verified"])
        self.assertFalse(report["source_receipts_before_t12"])
        self.assertFalse(report["two_source_complete_before_t12"])
        self.assertFalse(report["accuracy_scoring_allowed"])

    def test_hash_failure_cannot_report_complete_two_originals(self):
        report = inspect(pair(originals_hash_verified=False), clean())
        self.assertFalse(report["source_pair_sha_verified"])
        self.assertFalse(report["two_source_complete_before_t12"])
        self.assertFalse(report["t12_eligible"])

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
