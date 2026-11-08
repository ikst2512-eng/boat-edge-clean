"""Synthetic three-original fixtures: never a live official candidate or certificate."""
import unittest

from scripts.audit_t12_three_original_frozen import inspect, COMPONENTS

RACE = "202611080309"
CUT = "2026-11-08T14:18:00+09:00"
DEADLINE = "2026-11-08T14:30:00+09:00"
BEFORE = "2026-11-08T14:15:38.139739+09:00"
ODDS = "2026-11-08T14:15:48.378360+09:00"
RACELIST = "2026-11-08T14:15:44+09:00"
SHA = {"racelist": "a"*64, "beforeinfo": "b"*64, "odds": "c"*64}


def three(**overrides):
    return {
        "race_code": RACE,
        "cutoff_jst": CUT,
        "official_deadline_jst": DEADLINE,
        "racelist_received_jst": RACELIST,
        "beforeinfo_received_jst": BEFORE,
        "odds_received_jst": ODDS,
        "three_originals_hash_verified": True,
        "component_checks": {key: True for key in COMPONENTS},
        "all_research_components_observed_by_t12": True,
        "final_race_entry_verified": False,
        **overrides,
    }


def frozen(**overrides):
    return {
        "race_code": RACE,
        "generated_at": "2026-11-08T14:16:00+09:00",
        "input_source_kind": "official_three_originals",
        "official_original_sha256": SHA.copy(),
        **overrides,
    }


class ThreeOriginalFrozenTests(unittest.TestCase):
    def test_synthetic_research_ready_still_never_formal(self):
        result = inspect(three(), frozen(), SHA)
        self.assertTrue(result["research_only_three_source_forecast_chain_ready"])
        self.assertTrue(result["all_twelve_official_components_verified"])
        self.assertTrue(result["all_three_originals_received_by_t12"])
        self.assertTrue(result["frozen_forecast_original_hashes_match"])
        self.assertEqual(result["source_to_forecast_margin_seconds"], 11.622)
        self.assertFalse(result["full_t12_source_certified"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["t12_eligible"])
        self.assertFalse(result["forecast_usable"])
        self.assertFalse(result["accuracy_scoring_allowed"])
        self.assertIn("independent_first_git_remote_receipt_unverified",
                      result["missing_requirements"])
        self.assertIn("final_race_entry_not_independently_verified",
                      result["missing_requirements"])

    def test_original_receipt_equals_generation_not_proof(self):
        result = inspect(three(), frozen(generated_at=ODDS), SHA)
        self.assertFalse(result["forecast_generated_after_all_three_originals"])
        self.assertFalse(result["research_only_three_source_forecast_chain_ready"])

    def test_generation_late_even_with_sources_complete(self):
        result = inspect(three(),
                         frozen(generated_at="2026-11-08T14:18:01+09:00"), SHA)
        self.assertIn("frozen_forecast_after_t12", result["missing_requirements"])
        self.assertFalse(result["research_only_three_source_forecast_chain_ready"])

    def test_one_racelist_arrives_after_t12(self):
        report = inspect(three(racelist_received_jst="2026-11-08T14:18:01+09:00"),
                         frozen(), SHA)
        self.assertFalse(report["all_three_originals_received_by_t12"])
        self.assertIn("official_three_original_receipt_after_t12",
                      report["missing_requirements"])

    def test_each_component_must_be_literal_true(self):
        for key in COMPONENTS:
            with self.subTest(key=key):
                checks = {name: True for name in COMPONENTS}
                checks[key] = 1
                report = inspect(three(component_checks=checks), frozen(), SHA)
                self.assertFalse(report["all_twelve_official_components_verified"])
                self.assertFalse(report["research_only_three_source_forecast_chain_ready"])

    def test_missing_component_and_green_summary_do_not_count(self):
        report = inspect(three(component_checks={"odds_120": True}), frozen(), SHA)
        self.assertIn("official_three_original_component_evidence_incomplete",
                      report["missing_requirements"])
        self.assertFalse(report["research_only_three_source_forecast_chain_ready"])

    def test_unverified_archive_hash_rejects(self):
        report = inspect(three(three_originals_hash_verified=1), frozen(), SHA)
        self.assertFalse(report["all_three_original_hashes_verified"])
        self.assertFalse(report["research_only_three_source_forecast_chain_ready"])

    def test_research_readiness_flag_must_be_literal_true(self):
        report = inspect(three(all_research_components_observed_by_t12=1),
                         frozen(), SHA)
        self.assertFalse(report["research_only_three_source_forecast_chain_ready"])

    def test_csv_forecast_not_official_even_when_frozen_late(self):
        report = inspect(three(), frozen(input_source_kind="public_pre_race_csv"), SHA)
        self.assertFalse(report["frozen_forecast_original_hashes_match"])
        self.assertIn("frozen_forecast_not_sha_linked_to_three_official_originals",
                      report["missing_requirements"])

    def test_digest_mismatch_or_partial_lineage_rejects(self):
        for link in ({"racelist": "f"*64, "beforeinfo": "b"*64, "odds": "c"*64},
                     {"beforeinfo": "b"*64, "odds": "c"*64}, None):
            with self.subTest(link=link):
                report = inspect(three(), frozen(official_original_sha256=link), SHA)
                self.assertFalse(report["frozen_forecast_original_hashes_match"])
                self.assertFalse(report["research_only_three_source_forecast_chain_ready"])

    def test_bad_original_digest_map_rejected(self):
        for sha in ({}, {"racelist": "a"*64, "beforeinfo": "b"*64, "odds": "not-a-sha"},
                    None, {"racelist": "a"*64, "beforeinfo": "b"*64,
                           "odds": "c"*64, "extra": "d"*64}):
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                inspect(three(), frozen(), sha)

    def test_cross_race_identity_rejected(self):
        with self.assertRaisesRegex(ValueError, "race identity"):
            inspect(three(), frozen(race_code="202611081409"), SHA)
        with self.assertRaisesRegex(ValueError, "invalid audited"):
            inspect(three(race_code="202611089909"), frozen(), SHA)

    def test_forecast_generation_timestamp_must_be_unique(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            inspect(three(), frozen(generated_at_jst=CUT), SHA)
        f = frozen()
        del f["generated_at"]
        with self.assertRaisesRegex(ValueError, "exactly one"):
            inspect(three(), f, SHA)

    def test_timezone_cross_day_and_deadline_rejected(self):
        for stamp in ("2026-11-08T14:17:00", "2026-11-08T05:17:00+00:00",
                      "2026-11-09T00:01:00+09:00"):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                inspect(three(odds_received_jst=stamp), frozen(), SHA)
        with self.assertRaisesRegex(ValueError, "deadline"):
            inspect(three(official_deadline_jst="2026-11-08T14:31:00+09:00"),
                    frozen(), SHA)

    def test_self_reported_formal_claims_can_never_promote(self):
        report = inspect(three(final_race_entry_verified=True,
                               full_t12_source_certified=True,
                               formal=True),
                         frozen(formal=True, t12_eligible=True,
                                accuracy_scoring_allowed=True), SHA)
        self.assertFalse(report["formal"])
        self.assertFalse(report["accuracy_scoring_allowed"])
        self.assertFalse(report["independent_first_git_remote_receipt_verified"])
        self.assertFalse(report["final_race_entry_verified"])


if __name__ == "__main__":
    unittest.main()
