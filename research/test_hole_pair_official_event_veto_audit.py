"""Synthetic adversarial tests: official event *claims* never authorize dispatch."""
import copy
import unittest

from research.hole_pair_official_event_veto_audit import audit
from research.hole_pair_real_main_snapshot_gate import audit as source_audit
from research.test_hole_pair_real_main_snapshot_gate import (
    CODE, DAY, SOURCE, REFERENCE, fixture, sample,
)

CODE2 = "202611100402"
HASH = "a" * 64


def source_report(second=False):
    codes = [(CODE, sample())]
    if second:
        codes.append((CODE2, sample(CODE2)))
    tree, reader = fixture(codes)
    return source_audit(DAY, SOURCE, REFERENCE, tree, reader)


def claim(code=CODE, **overrides):
    d = {
        "race_code": code,
        "source_audit_report_sha256_claim": HASH,
        "source_last_original_received_jst_claim": "2026-11-10T10:45:00+09:00",
        "official_deadline_jst_claim": "2026-11-10T11:12:00+09:00",
        "racelist_original_sha256_claim": HASH,
        "beforeinfo_original_sha256_claim": HASH,
        "odds_original_sha256_claim": HASH,
        "exhibition_boats_claim": 6,
        "distinct_trifecta_odds_claim": 120,
        "github_source_archive_artifact_id_claim": 1337,
    }
    d.update(overrides)
    return d


class SourceEventVetoTests(unittest.TestCase):
    def test_no_source_handoff_on_real_source_shape_makes_zero_dispatches(self):
        report = audit(source_report())
        self.assertEqual(report["original_source_races_examined"], 1)
        self.assertEqual(report["official_handoff_claim_missing"], 1)
        self.assertEqual(report["source_forecast_missing_beforeinfo"], 1)
        self.assertEqual(report["declared_t12_window_open_at_reference"], 1)
        self.assertEqual(report["authorized_dispatch_events"], 0)
        self.assertEqual(report["independent_first_candidate_receipts_verified"], 0)
        self.assertEqual(report["prospective_pilot_formally_eligible"], 0)
        self.assertEqual(report["prospective_confirmation_formally_eligible"], 0)
        self.assertFalse(report["results_opened"])
        self.assertFalse(report["formal"])

    def test_complete_looking_all_originals_still_cannot_authorize_dispatch(self):
        report = audit(source_report(), {CODE: claim()})
        row = report["rows"][0]
        self.assertTrue(row["all_three_official_original_components_claimed_only"])
        self.assertEqual(report["claimed_three_original_components_unverified"], 1)
        self.assertEqual(report["existing_forecast_predates_claimed_source"], 1)
        self.assertIn("existing_forecast_generated_before_claimed_official_sources",
                      row["blocking_evidence_codes"])
        self.assertFalse(row["dispatch_authorized"])
        self.assertEqual(report["authorized_dispatch_events"], 0)
        self.assertFalse(report["formal"])

    def test_no_forecast_consumption_verified_even_if_source_claim_precedes_model(self):
        report = audit(source_report(), {CODE: claim(
            source_last_original_received_jst_claim="2026-11-10T10:35:00+09:00",
        )})
        row = report["rows"][0]
        self.assertEqual(row["source_chronology_claim_classification"],
                         "generation_after_source_claim_not_authenticated")
        self.assertFalse(row["actual_model_official_original_consumption_verified"])
        self.assertIn("current_forecast_has_no_beforeinfo_snapshot",
                      row["blocking_evidence_codes"])
        self.assertFalse(row["dispatch_authorized"])

    def test_missing_racelist_cannot_be_filled_by_six_boats_and_120_odds(self):
        report = audit(source_report(), {CODE: claim(
            racelist_original_sha256_claim=None,
        )})
        self.assertIn("same_race_official_racelist_original_missing",
                      report["rows"][0]["blocking_evidence_codes"])
        self.assertFalse(report["rows"][0]["all_three_official_original_components_claimed_only"])

    def test_partial_exhibition_and_odds_must_remain_missing(self):
        for change, blocker in (
            ({"exhibition_boats_claim": 5}, "same_race_six_boat_exhibition_missing"),
            ({"beforeinfo_original_sha256_claim": None}, "same_race_six_boat_exhibition_missing"),
            ({"distinct_trifecta_odds_claim": 119}, "same_race_distinct_120_way_odds_missing"),
            ({"odds_original_sha256_claim": None}, "same_race_distinct_120_way_odds_missing"),
        ):
            with self.subTest(change=change):
                report = audit(source_report(), {CODE: claim(**change)})
                self.assertIn(blocker, report["rows"][0]["blocking_evidence_codes"])
                self.assertFalse(report["rows"][0]["dispatch_authorized"])

    def test_wrong_official_deadline_quarantined_even_if_other_claims_complete(self):
        report = audit(source_report(), {CODE: claim(
            official_deadline_jst_claim="2026-11-10T11:13:00+09:00",
        )})
        self.assertEqual(report["claimed_official_deadline_mismatch"], 1)
        self.assertIn("claimed_official_deadline_mismatches_original_forecast",
                      report["rows"][0]["blocking_evidence_codes"])

    def test_official_event_at_or_after_t12_never_retroactive(self):
        for stamp in ("2026-11-10T11:00:00+09:00",
                      "2026-11-10T11:01:00+09:00"):
            with self.subTest(stamp=stamp):
                report = audit(source_report(), {CODE: claim(
                    source_last_original_received_jst_claim=stamp,
                )})
                self.assertIn("claimed_official_source_arrived_after_declared_t12",
                              report["rows"][0]["blocking_evidence_codes"])
                self.assertEqual(report["authorized_dispatch_events"], 0)

    def test_cross_race_handoff_or_orphan_report_is_rejected(self):
        report = source_report(second=True)
        for handoff in (
            {CODE: claim(code=CODE2)},
            {CODE: claim(), "202611100403": claim("202611100403")},
            {CODE: claim(), CODE2: claim(code=CODE)},
        ):
            with self.subTest(handoff=handoff), self.assertRaises(ValueError):
                audit(report, handoff)

    def test_same_race_rows_not_counted_twice_and_second_uncovered(self):
        report = audit(source_report(second=True), {CODE: claim()})
        self.assertEqual(report["original_source_races_examined"], 2)
        self.assertEqual(report["source_handoff_claims_supplied_unverified"], 1)
        self.assertEqual(report["official_handoff_claim_missing"], 1)
        self.assertEqual(len({r["race_code"] for r in report["rows"]}), 2)
        self.assertEqual(report["authorized_dispatch_events"], 0)

    def test_poisoned_digest_and_unknown_schema_fields_fail_closed(self):
        for modifications in (
            {"source_audit_report_sha256_claim": "bad"},
            {"source_audit_report_sha256_claim": None},
            {"odds_original_sha256_claim": "b" * 63},
            {"beforeinfo_original_sha256_claim": 1},
            {"independent_official_source_verified": True},
            {"formal": True},
        ):
            with self.subTest(modifications=modifications), self.assertRaises(ValueError):
                audit(source_report(), {CODE: claim(**modifications)})

    def test_strict_counts_and_remote_artifact_identifiers(self):
        for modifications in (
            {"exhibition_boats_claim": 7},
            {"exhibition_boats_claim": -1},
            {"exhibition_boats_claim": True},
            {"distinct_trifecta_odds_claim": 121},
            {"distinct_trifecta_odds_claim": True},
            {"github_source_archive_artifact_id_claim": False},
            {"github_source_archive_artifact_id_claim": -1},
            {"github_source_archive_artifact_id_claim": "123"},
        ):
            with self.subTest(modifications=modifications), self.assertRaises(ValueError):
                audit(source_report(), {CODE: claim(**modifications)})

    def test_other_day_non_jst_and_unparseable_sources_refused(self):
        for received in (
            "2026-11-09T10:45:00+09:00",
            "2026-11-10T01:45:00Z",
            "not-a-time",
            None,
        ):
            with self.subTest(received=received), self.assertRaises(ValueError):
                audit(source_report(), {CODE: claim(
                    source_last_original_received_jst_claim=received,
                )})

    def test_forecast_source_provenance_cannot_be_overridden_by_event_claim(self):
        original = source_report()
        for key, value in (
            ("formal", True),
            ("result_files_read", True),
            ("prospective_pilot_formally_eligible", 1),
            ("source_main_commit", "b" * 40),
        ):
            poisoned = copy.deepcopy(original)
            poisoned[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit(poisoned, {CODE: claim()})

    def test_empty_source_day_has_no_authorized_source_events(self):
        # Git ls-tree prints zero bytes, not a newline, for an empty tree.
        report = source_audit(DAY, SOURCE, REFERENCE, "", lambda blob: None)
        self.assertEqual(audit(report)["original_source_races_examined"], 0)
        self.assertEqual(audit(report)["authorized_dispatch_events"], 0)
        self.assertFalse(audit(report)["official_full_day_schedule_verified"])

    def test_claim_forged_first_receipt_bool_is_not_whitelisted(self):
        with self.assertRaisesRegex(ValueError, "untrusted_or_cross_race_source_event"):
            audit(source_report(), {CODE: claim(
                independent_first_candidate_receipt_verified=True,
            )})


if __name__ == "__main__":
    unittest.main()
