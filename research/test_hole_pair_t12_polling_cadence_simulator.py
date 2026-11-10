"""No live polling; all expected first-acceptance/source flags remain false."""
import copy
import unittest

from research import hole_pair_t12_polling_cadence_simulator as planner
from research import hole_pair_real_main_snapshot_gate as originals
from research.test_hole_pair_real_main_snapshot_gate import (
    DAY, SOURCE, REFERENCE, CODE, sample, fixture
)

HINT = "2026-11-10T10:50:00+09:00"


def original_report():
    tree, read = fixture([
        (CODE, sample()),
        ("202611100402", sample("202611100402",
                               deadline_jst="2026-11-10T11:18:00+09:00")),
    ])
    return originals.audit(DAY, SOURCE, REFERENCE, tree, read)


def plan(data=None, **changes):
    return planner.simulate(
        original_report() if data is None else data,
        first_git_source_sighting_hint_jst=HINT,
        **changes,
    )


class T12CounterfactualTests(unittest.TestCase):
    def test_faster_cadence_has_more_clock_only_slots_not_formal_candidates(self):
        r = plan(cadence_minutes=(1, 3, 5, 10, 15))
        counts = {x["hypothetical_poll_period_minutes"]:
                  x["clock_only_races_with_at_least_one_hypothetical_slot"]
                  for x in r["scenarios"]}
        self.assertEqual(counts, {1: 2, 3: 2, 5: 1, 10: 0, 15: 0})
        self.assertFalse(r["actual_workflow_or_candidates_dispatched"])
        self.assertFalse(r["official_source_arrival_authenticated"])
        self.assertFalse(r["first_independent_receipt_verified"])
        self.assertFalse(r["formal"])
        self.assertEqual(r["prospective_pilot_formally_eligible"], 0)
        self.assertEqual(r["prospective_confirmation_formally_eligible"], 0)
        self.assertFalse(r["results_opened"])

    def test_single_race_valid_window_computes_one_or_zero_without_writes(self):
        r = plan()
        for item in r["scenarios"]:
            self.assertEqual(
                item["clock_only_races_without_slot"] +
                item["clock_only_races_with_at_least_one_hypothetical_slot"], 2)
            self.assertEqual(item["formally_eligible"], 0)
            self.assertFalse(item["official_input_actual_arrival_verified"])

    def test_later_sighting_hint_can_close_all_theoretical_windows(self):
        r = planner.simulate(
            original_report(),
            first_git_source_sighting_hint_jst="2026-11-10T11:10:00+09:00",
            cadence_minutes=(1, 5))
        self.assertEqual([x["clock_only_races_with_at_least_one_hypothetical_slot"]
                          for x in r["scenarios"]], [0, 0])

    def test_hypothetical_official_lead_too_short_never_authenticates_input(self):
        r = plan(assumed_source_ready_lead_seconds=40,
                 assumed_processing_reserve_seconds=30)
        self.assertEqual(r["assumed_official_input_ready_seconds_before_declared_t12_NOT_OBSERVED"], 40)
        self.assertFalse(r["official_source_arrival_authenticated"])

    def test_duplicate_or_reversed_source_roster_is_rejected(self):
        r = original_report()
        for rows in (
            r["rows"][::-1],
            [r["rows"][0], r["rows"][0]],
            r["rows"][:1],
        ):
            bad = copy.deepcopy(r)
            bad["rows"] = rows
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                plan(bad)

    def test_changed_original_sha1_sha256_or_clock_fields_fail_closed(self):
        r = original_report()
        mutations = (
            ("source_git_blob_sha1", "not-a-sha"),
            ("source_sha256_from_verified_git_bytes", "0"*40),
            ("local_declared_t_minus_12_jst", "2026-11-10T10:59:00+09:00"),
            ("declared_t12_open_at_reference", False),
            ("generated_before_local_declared_t12", False),
            ("local_generated_jst_claim", "2026-11-09T10:40:00+09:00"),
            ("local_declared_deadline_jst", "not-a-time"),
            ("race_code", "202611100412"),
            ("beforeinfo_snapshot_status", "official_verified_6boats"),
            ("official_complete_six_boat_beforeinfo_verified", True),
            ("official_complete_120_way_odds_verified", True),
            ("independent_first_candidate_receipt_verified", True),
            ("formal_candidate", True),
        )
        for field, changed in mutations:
            bad = copy.deepcopy(r)
            bad["rows"][0][field] = changed
            with self.subTest(field=field), self.assertRaises(ValueError):
                plan(bad)

    def test_aggregate_hiding_missing_forecast_or_falsifying_counts_is_rejected(self):
        for key in (
            "original_main_forecast_ids_examined",
            "original_git_blob_sha1_verified_count",
            "original_source_sha256_computed_count",
            "optional_beforeinfo_absent_from_forecast",
            "locally_generated_before_declared_t12",
            "declared_t12_still_future_at_reference",
        ):
            r = original_report()
            r[key] += 1
            with self.subTest(key=key), self.assertRaises(ValueError):
                plan(r)

    def test_forged_formal_claim_unknown_fields_and_wrong_schema_are_rejected(self):
        for key, value in (
            ("formal", True),
            ("production_promotion_allowed", True),
            ("prospective_pilot_formally_eligible", 1),
            ("prospective_confirmation_formally_eligible", 1),
            ("same_race_official_t12_origins_authenticated", 1),
            ("first_independent_signed_candidate_receipts_authenticated", 1),
            ("result_files_read", True),
            ("whole_day_official_schedule_verified", True),
            ("schema", "UNREVIEWED_RETROACTIVE_PROOF"),
            ("confirmed_winner", "1-2-3"),
        ):
            bad = original_report()
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                plan(bad)

    def test_invalid_hypothetical_time_parameters_rejected(self):
        for lead, reserve in ((0, 30), (20, 30), (30, 30), (3601, 5),
                              (True, 10), (180, -1), (180, "30")):
            with self.subTest(lead=lead, reserve=reserve), self.assertRaises(ValueError):
                plan(assumed_source_ready_lead_seconds=lead,
                     assumed_processing_reserve_seconds=reserve)

    def test_untrusted_or_cherry_picked_cadences_rejected(self):
        for cadences in ((), (1, 1), (5, 1), (0,), (121,), (True,), "1",
                         tuple(range(1, 26))):
            with self.subTest(cadences=cadences), self.assertRaises(ValueError):
                plan(cadence_minutes=cadences)

    def test_missing_or_wrong_day_initial_sighting_hint_is_rejected(self):
        data = original_report()
        for hint in (None, "2026-11-09T10:50:00+09:00",
                     "2026-11-10T01:50:00Z", "not-a-date", ""):
            with self.subTest(hint=hint), self.assertRaises(ValueError):
                planner.simulate(data, first_git_source_sighting_hint_jst=hint)

    def test_empty_verified_snapshot_is_not_formal_day_universe(self):
        report = originals.audit(DAY, SOURCE, REFERENCE, "", lambda blob: None)
        r = plan(report, cadence_minutes=(1,))
        self.assertEqual(r["original_races_from_verified_git_snapshot"], 0)
        self.assertEqual(r["scenarios"][0]["clock_only_races_with_at_least_one_hypothetical_slot"], 0)
        self.assertFalse(r["schedule_day_universe_verified"])
        self.assertFalse(r["production_promotion_allowed"])


    def test_one_minute_phase_can_miss_one_minute_pre_cutoff_source_release(self):
        # Two deadlines at exact minute boundaries; arrivals hypothesized only
        # 60s before cutoff, processing reserve 30s. Aligned minute polls fit,
        # but a 45-second phase offset misses both. Do not infer 1m guarantee.
        aligned = plan(assumed_source_ready_lead_seconds=60,
                       assumed_processing_reserve_seconds=30,
                       cadence_minutes=(1,))
        jittered = plan(assumed_source_ready_lead_seconds=60,
                        assumed_processing_reserve_seconds=30,
                        cadence_minutes=(1,), poll_phase_offset_seconds=45)
        self.assertEqual(
            aligned["scenarios"][0]["clock_only_races_with_at_least_one_hypothetical_slot"], 2)
        self.assertEqual(
            jittered["scenarios"][0]["clock_only_races_with_at_least_one_hypothetical_slot"], 0)
        self.assertEqual(jittered["hypothetical_poll_phase_offset_seconds"], 45)
        self.assertFalse(jittered["first_independent_receipt_verified"])
        self.assertFalse(jittered["formal"])

    def test_polling_phase_range_rejects_malformed_and_synthetic_promotion(self):
        for phase in (-1, 60, True, "30", 1.5, None):
            with self.subTest(phase=phase), self.assertRaisesRegex(
                    ValueError, "invalid_untrusted_synthetic_poll_phase"):
                plan(poll_phase_offset_seconds=phase)


if __name__ == "__main__":
    unittest.main()
