"""No-result, synthetic, adversarial coverage tests for future snapshots."""
import copy
import unittest

from research import hole_pair_universe_coverage as c
from test_hole_pair_remote_receipt_evidence import candidate

MAIN = "a" * 40
DAY = "20261109"
CODES = ["202611090101", "202611090102", "202611090103", "202611090104"]


def frozen(code):
    r = candidate()
    r["race_code"] = code
    r["source_git_blob_sha1"] = "b" * 40
    r["model_version"] = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"
    r["locked_selector_git_blobs"] = {
        "hole_third_choice_research.py": "579edc1ae846489d447307fbf03b35fc7d4c09b9",
        "hole_pair_diversification_research.py": "56f06c10f6d07e03b2e37624ecf57dc6de7d8748",
        "hole_top5_safe_bundle_research.py": "a43f53d898ac73829e7f2b24f81624d69d26d74a",
        "hole_pair_third_bundle_research.py": "88c4ed506588a24bb593d104b5d0f59c7502d73a",
    }
    return r


class ExactRosterCoverageTests(unittest.TestCase):
    def full(self):
        return c.reconcile(
            DAY, MAIN, CODES, [frozen(CODES[0]), frozen(CODES[2])],
            {"after_t_minus_12": [CODES[1]],
             "archive_unavailable_or_invalid": [CODES[3]]},
        )

    def test_all_main_snapshot_race_ids_accounted_exactly_once(self):
        out = self.full()
        self.assertEqual(out["snapshot_forecasts_examined"], 4)
        self.assertEqual(out["frozen_locally_unverified"], 2)
        self.assertEqual(out["excluded_by_reason"],
                         {"after_t_minus_12": 1,
                          "archive_unavailable_or_invalid": 1})
        self.assertEqual(out["frozen_codes_by_candidate_cutoff_order"],
                         [CODES[0], CODES[2]])
        self.assertTrue(out["source_snapshot_race_coverage_complete"])
        self.assertFalse(out["entire_day_or_official_schedule_complete_verified"])
        self.assertFalse(out["official_t12_complete_verified"])
        self.assertEqual(out["pilot_formally_eligible"], 0)
        self.assertEqual(out["confirmation_formally_eligible"], 0)
        self.assertFalse(out["formal"])

    def test_missing_exclusion_fails_even_if_all_frozen_are_valid(self):
        with self.assertRaisesRegex(ValueError, "coverage_mismatch_missing_1_orphan_0"):
            c.reconcile(DAY, MAIN, CODES, [frozen(CODES[0]), frozen(CODES[2])],
                        {"after_t_minus_12": [CODES[1]]})

    def test_count_matching_cannot_hide_wrong_race_id(self):
        with self.assertRaisesRegex(ValueError, "coverage_mismatch_missing_1_orphan_1"):
            c.reconcile(DAY, MAIN, CODES[:3],
                        [frozen(CODES[0]), frozen(CODES[3])],
                        {"after_t_minus_12": [CODES[1]]})

    def test_duplicate_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_source_inventory"):
            c.reconcile(DAY, MAIN, CODES + [CODES[0]], [], {})

    def test_duplicate_frozen_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_frozen_or_excluded"):
            c.reconcile(DAY, MAIN, [CODES[0]],
                        [frozen(CODES[0]), frozen(CODES[0])], {})

    def test_frozen_and_excluded_collision_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_frozen_or_excluded"):
            c.reconcile(DAY, MAIN, [CODES[0]], [frozen(CODES[0])],
                        {"after_t_minus_12": [CODES[0]]})

    def test_excluded_in_two_reasons_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_frozen_or_excluded"):
            c.reconcile(DAY, MAIN, [CODES[0]], [],
                        {"after_t_minus_12": [CODES[0]],
                         "invalid_deadline": [CODES[0]]})

    def test_outside_day_and_unreal_race_rejected(self):
        with self.assertRaisesRegex(ValueError, "race_outside_snapshot_day"):
            c.reconcile(DAY, MAIN, ["202611100101"], [], {})
        with self.assertRaisesRegex(ValueError, "invalid_venue_or_race_number"):
            c.reconcile(DAY, MAIN, ["202611092501"], [], {})
        with self.assertRaisesRegex(ValueError, "invalid_race_calendar_date"):
            c.reconcile("20261131", MAIN, ["202611310101"], [], {})

    def test_backfill_before_november_9_rejected(self):
        with self.assertRaisesRegex(ValueError, "capture_day_outside_future_protocol"):
            c.reconcile("20261108", MAIN, ["202611080101"], [], {})

    def test_new_unrecognized_reasons_rejected(self):
        with self.assertRaisesRegex(ValueError, "unrecognized_exclusion_reason"):
            c.reconcile(DAY, MAIN, [CODES[0]], [],
                        {"winner_is_known": [CODES[0]]})

    def test_noncanonical_source_and_exclusion_orders_rejected(self):
        with self.assertRaisesRegex(ValueError, "source_inventory_not_canonical_sorted"):
            c.reconcile(DAY, MAIN, CODES[::-1], [], {})
        with self.assertRaisesRegex(ValueError, "noncanonical_exclusion_roster"):
            c.reconcile(DAY, MAIN, CODES[:2], [],
                        {"after_t_minus_12": CODES[:2][::-1]})

    def test_mutated_candidate_fails_before_coverage_credit(self):
        record = frozen(CODES[0])
        record["method_source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "untrusted_candidate_claim_or_method"):
            c.reconcile(DAY, MAIN, [CODES[0]], [record], {})

    def test_missing_source_git_blob_refused(self):
        record = frozen(CODES[0])
        record.pop("source_git_blob_sha1")
        with self.assertRaisesRegex(ValueError, "unexpected_frozen_record_fields"):
            c.reconcile(DAY, MAIN, [CODES[0]], [record], {})

    def test_result_or_posthoc_metadata_cannot_enter_freeze_roster(self):
        for key, value in (
            ("winning_ticket", "1-2-3"),
            ("confirmed_result", {"first": 1, "second": 2, "third": 3}),
            ("result_checked_at", "2026-11-09T11:55:00+09:00"),
            ("post_result_label", "hit"),
        ):
            r = frozen(CODES[0])
            r[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(
                    ValueError, "unexpected_frozen_record_fields"):
                c.reconcile(DAY, MAIN, [CODES[0]], [r], {})

    def test_unknown_metadata_or_modified_warning_refused(self):
        r = frozen(CODES[0])
        r["unreviewed_metadata"] = "external_signal"
        with self.assertRaisesRegex(ValueError, "unexpected_frozen_record_fields"):
            c.reconcile(DAY, MAIN, [CODES[0]], [r], {})
        r = frozen(CODES[0])
        r["warning"] = {"winner": "1-2-3"}
        with self.assertRaisesRegex(ValueError, "untrusted_frozen_record_metadata"):
            c.reconcile(DAY, MAIN, [CODES[0]], [r], {})

    def test_altered_selector_blob_and_result_warning_never_pass(self):
        altered = frozen(CODES[0])
        altered["locked_selector_git_blobs"]["hole_third_choice_research.py"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "untrusted_frozen_record_metadata"):
            c.reconcile(DAY, MAIN, [CODES[0]], [altered], {})
        altered = frozen(CODES[0])
        altered["warning"] = "Known winning trifecta: 1-2-3"
        with self.assertRaisesRegex(ValueError, "untrusted_frozen_record_metadata"):
            c.reconcile(DAY, MAIN, [CODES[0]], [altered], {})

    def test_exact_source_freeze_warning_remains_compatible(self):
        r = frozen(CODES[0])
        r["warning"] = (
            "Candidate frozen by a local clock only. No independently "
            "verified first receipt; cannot report formal accuracy."
        )
        report = c.reconcile(DAY, MAIN, [CODES[0]], [r], {})
        self.assertEqual(report["frozen_locally_unverified"], 1)

    def test_empty_inventory_is_not_whole_day_proof(self):
        r = c.reconcile(DAY, MAIN, [], [], {})
        self.assertTrue(r["source_snapshot_race_coverage_complete"])
        self.assertFalse(r["entire_day_or_official_schedule_complete_verified"])
        self.assertFalse(r["formal"])

    def test_non_candidate_entries_never_enter_pilot_or_confirmation(self):
        r = c.reconcile(DAY, MAIN, [CODES[0]], [],
                        {"after_t_minus_12": [CODES[0]]})
        self.assertEqual(r["pilot_formally_eligible"], 0)
        self.assertEqual(r["confirmation_formally_eligible"], 0)
        self.assertEqual(r["frozen_locally_unverified"], 0)


if __name__ == "__main__":
    unittest.main()
