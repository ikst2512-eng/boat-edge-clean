"""T−12 same-race proof-chain regression fixtures; real originals in Actions CI."""
import unittest
from copy import deepcopy

from scripts.audit_t12_same_race_proof_chain import compose, NOV03, NOV09


def nonformal():
    return dict(formal=False, t12_eligible=False,
                accuracy_scoring_allowed=False,
                new_formal_certifications=0,
                formal_accuracy_denominator=None)


def triple():
    return dict(
        **nonformal(),
        schema="T12_PINNED_GITHUB_THREE_ORIGINAL_REPLAY_V1",
        race_code=NOV03,
        source_git_commit_sha="d0ed89f146dff117021c2bc042b20259d6715515",
        source_git_blob_and_manifest_hashes_reaudited=True,
        three_official_original_files_present=True,
        source_received_by_t12=True,
        six_registration_and_exhibition_components_complete=False,
        source_research_components_complete=False,
        qualified_three_source_candidates=0,
        missing_source_components=[
            "exhibition_six_courses", "exhibition_times_six",
            "tilt_six", "start_exhibition_six",
        ],
        model_original_bytes_consumption_independently_verified=False,
        independent_first_forecast_git_remote_acceptance_verified=False,
        final_entry_independently_verified=False,
        last_original_received_jst="2026-11-03T17:00:59.946462+09:00",
        source_cutoff_jst="2026-11-03T20:19:00+09:00",
    )


def paired():
    rows = []
    for code, cutoff, last in (
        (NOV09[0], "2026-11-09T14:30:00+09:00",
         "2026-11-09T14:26:59.498535+09:00"),
        (NOV09[1], "2026-11-09T14:28:00+09:00",
         "2026-11-09T14:26:41.921482+09:00"),
    ):
        mode = dict(generated_strictly_after_official_pair=False,
                    independent_actual_model_original_consumption_verified=False,
                    first_git_remote_receipt_verified=False, formal=False)
        rows.append(dict(race_code=code, official_t12_cutoff_jst=cutoff,
                         official_latest_original_received_jst=last,
                         official_pair_originals_replayed_complete=True,
                         racelist_official_original_present=False,
                         formal=False, accuracy_scoring_allowed=False,
                         forecasts={"clean": dict(mode), "v2_four_mode": dict(mode)}))
    return dict(
        **nonformal(),
        schema="T12_NOV09_REAL_OFFICIAL_PAIR_VS_FROZEN_FORECAST_V1",
        extracted_official_source_originals_replayed=True,
        source_run_id=42567310743,
        source_artifact_id=13652131213,
        github_original_artifact_digest_from_metadata=
            "99f02ff306307dd945f27c225e18ff8341be2832232b7dd0f2751e1d8935f451",
        two_original_complete_races=2, matched_pinned_forecasts=4,
        matched_forecasts_generated_after_sources=0,
        three_official_original_races=0,
        independent_model_input_consumption_verified=False,
        independent_first_remote_receipt_verified=False,
        final_race_entry_verified=False,
        race_rows=rows,
    )


def artifact():
    rows = []
    for code, cutoff, last in (
        (NOV09[0], "2026-11-09T14:30:00+09:00",
         "2026-11-09T14:26:59.498535+09:00"),
        (NOV09[1], "2026-11-09T14:28:00+09:00",
         "2026-11-09T14:26:41.921482+09:00"),
    ):
        rows.append(dict(
            race_code=code, official_t12_cutoff_jst=cutoff,
            last_official_original_receipt_self_recorded_jst=last,
            two_official_original_bytes_replayed=True,
            third_official_racelist_original_replayed=False,
            github_artifact_updated_before_t12_one_sec_margin=True,
            forecast_generated_after_all_official_sources=False,
            independent_first_forecast_git_remote_receipt_proven=False,
            formal=False,
        ))
    return dict(
        **nonformal(),
        schema="T12_SOURCE_ARCHIVE_SERVER_TIME_AUDIT_V1",
        source_run_id=42567310743, source_artifact_id=13652131213,
        artifact_original_zip_sha256_from_github_metadata=
            "99f02ff306307dd945f27c225e18ff8341be2832232b7dd0f2751e1d8935f451",
        individual_official_original_bytes_replayed_by_upstream_audit=True,
        server_timestamp_artifact_archive_before_t12_races=2,
        source_artifact_server_time_not_first_forecast_git_receipt=True,
        official_three_originals_replayed=0,
        post_official_source_frozen_forecasts=0,
        race_rows=rows,
    )


class NoCrossRaceOrAcrossDayStitching(unittest.TestCase):
    def test_real_races_have_disjoint_missing_gates_and_zero_formal(self):
        audit = compose(triple(), paired(), artifact())
        self.assertEqual(audit["races_compared"], 3)
        self.assertEqual(audit["fully_qualified_same_race_three_original_t12_sources"], 0)
        self.assertEqual(audit["two_original_sets_with_complete_exhibition_and_120_odds"], 2)
        self.assertEqual(audit["source_archive_server_published_before_t12_races"], 2)
        self.assertEqual(audit["new_formal_certifications"], 0)
        self.assertFalse(audit["cross_race_original_combination_allowed"])
        self.assertIsNone(audit["formal_accuracy_denominator"])
        old = audit["races"][0]
        self.assertEqual(old["race_code"], NOV03)
        self.assertTrue(old["official_racelist_original"])
        self.assertFalse(old["six_boat_exhibition_complete"])
        for race in audit["races"][1:]:
            self.assertIn(race["race_code"], NOV09)
            self.assertFalse(race["official_racelist_original"])
            self.assertTrue(race["six_boat_exhibition_complete"])
            self.assertTrue(race["independent_source_archive_server_publication_by_t12"])
            self.assertFalse(race["same_race_three_source_readiness"])

    def test_five_gate_same_race_counts_preserve_missing_evidence(self):
        result = compose(triple(), paired(), artifact())
        self.assertEqual(result["historical_five_gate_counts"], {
            "official_beforeinfo_six_exhibition": 2,
            "official_odds_120": 3,
            "official_deadline_source_cutoff": 3,
            "forecast_after_official_sources_before_t12": 0,
            "independent_first_forecast_git_acceptance": 0,
        })
        self.assertEqual(result["historical_extra_gate_counts"], {
            "official_racelist_original": 1,
            "actual_model_original_consumption": 0,
            "final_entry_verified": 0,
        })
        self.assertEqual(result["historical_all_five_gates_verified"], 0)
        self.assertEqual(len(result["historical_five_gate_by_race"]), 3)
        self.assertFalse(result["formal"])
        self.assertIsNone(result["formal_accuracy_denominator"])

    def test_gate_counts_cannot_borrow_official_racelist_from_other_race(self):
        rows = compose(triple(), paired(), artifact())["historical_five_gate_by_race"]
        by_code = {row["race_code"]: row for row in rows}
        self.assertEqual(set(by_code), {NOV03, *NOV09})
        self.assertFalse(by_code[NOV03]["gates"]["official_beforeinfo_six_exhibition"])
        self.assertTrue(by_code[NOV03]["extra_official_racelist_original"])
        for code in NOV09:
            self.assertTrue(by_code[code]["gates"]["official_beforeinfo_six_exhibition"])
            self.assertTrue(by_code[code]["gates"]["official_odds_120"])
            self.assertFalse(by_code[code]["extra_official_racelist_original"])
            self.assertFalse(by_code[code]["gates"]["forecast_after_official_sources_before_t12"])
            self.assertFalse(by_code[code]["gates"]["independent_first_forecast_git_acceptance"])
            self.assertFalse(by_code[code]["all_five_verified"])

    def test_all_five_required_cannot_erase_independent_consumption_gate(self):
        result = compose(triple(), paired(), artifact())
        for row in result["historical_five_gate_by_race"]:
            self.assertFalse(row["extra_model_original_consumption"])
            self.assertFalse(row["extra_final_entry"])
            self.assertFalse(row["formal"])
        self.assertFalse(result["t12_eligible"])
        self.assertFalse(result["accuracy_scoring_allowed"])
        self.assertEqual(result["new_formal_certifications"], 0)

    def test_collector_timestamp_not_equal_independent_source_zip(self):
        report = compose(triple(), paired(), artifact())
        self.assertEqual(report["historical_source_time_provenance"], {
            "collector_source_receipt_self_reported_before_t12": 3,
            "independent_source_zip_published_before_t12": 2,
            "first_forecast_git_remote_receipt_verified": 0,
        })
        old = report["historical_five_gate_by_race"][0]
        self.assertTrue(old["collector_source_receipt_self_reported_before_t12"])
        self.assertFalse(old["independent_source_zip_published_before_t12"])
        self.assertFalse(old["source_zip_publication_is_first_forecast_git_receipt"])

    def test_earliest_blocker_is_per_race_and_no_cross_race_stitch(self):
        report = compose(triple(), paired(), artifact())
        self.assertEqual(report["historical_first_blocker_counts"], {
            "complete_six_boat_exhibition_missing": 1,
            "same_race_official_racelist_missing": 2,
        })
        by_code = {r["race_code"]: r for r in report["historical_five_gate_by_race"]}
        self.assertEqual(by_code[NOV03]["next_source_or_forecast_blocker"],
                         "complete_six_boat_exhibition_missing")
        for code in NOV09:
            self.assertEqual(by_code[code]["next_source_or_forecast_blocker"],
                             "same_race_official_racelist_missing")
            self.assertTrue(by_code[code]["independent_source_zip_published_before_t12"])
            self.assertFalse(by_code[code]["source_zip_publication_is_first_forecast_git_receipt"])
        self.assertEqual(report["new_formal_certifications"], 0)

    def test_synthetically_removed_independent_publication_cannot_certify(self):
        x = artifact()
        x["race_rows"][0]["github_artifact_updated_before_t12_one_sec_margin"] = False
        with self.assertRaises(ValueError):
            compose(triple(), paired(), x)
        report = compose(triple(), paired(), artifact())
        self.assertEqual(report["historical_all_five_gates_verified"], 0)
        self.assertFalse(report["accuracy_scoring_allowed"])
        self.assertIsNone(report["formal_accuracy_denominator"])

    def test_three_files_without_exhibition_does_not_pass(self):
        x = triple()
        x["six_registration_and_exhibition_components_complete"] = True
        with self.assertRaises(ValueError):
            compose(x, paired(), artifact())

    def test_three_source_missing_list_cannot_be_fabricated(self):
        for fields in ([], ["tilt_six"], ["start_exhibition_six"] * 4,
                       ["exhibition_times_six", "tilt_six",
                        "start_exhibition_six", "unknown"]):
            x = triple()
            x["missing_source_components"] = fields
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                compose(x, paired(), artifact())

    def test_historical_git_sha_and_race_must_match(self):
        for update in ({"race_code": NOV09[0]},
                       {"source_git_commit_sha": "f" * 40},
                       {"source_git_blob_and_manifest_hashes_reaudited": False}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                compose({**triple(), **update}, paired(), artifact())

    def test_stale_or_mixed_racing_day_is_rejected(self):
        x = triple()
        x["last_original_received_jst"] = "2026-11-04T17:00:59+09:00"
        with self.assertRaises(ValueError):
            compose(x, paired(), artifact())
        x = paired()
        x["race_rows"][0]["official_t12_cutoff_jst"] = (
            "2026-11-08T14:30:00+09:00")
        with self.assertRaises(ValueError):
            compose(triple(), x, artifact())

    def test_raw_pair_only_success_is_not_formal(self):
        x = paired()
        x["three_official_original_races"] = 1
        with self.assertRaises(ValueError):
            compose(triple(), x, artifact())

    def test_no_overclaim_from_artifact_server_time(self):
        for altered in (
            {"server_timestamp_artifact_archive_before_t12_races": 0},
            {"individual_official_original_bytes_replayed_by_upstream_audit": False},
            {"source_artifact_server_time_not_first_forecast_git_receipt": False},
            {"post_official_source_frozen_forecasts": 1},
            {"official_three_originals_replayed": 2},
        ):
            with self.subTest(altered=altered), self.assertRaises(ValueError):
                compose(triple(), paired(), {**artifact(), **altered})

    def test_remote_time_for_another_race_may_not_be_transferred(self):
        x = artifact()
        x["race_rows"][0]["race_code"] = NOV03
        with self.assertRaises(ValueError):
            compose(triple(), paired(), x)
        x = artifact()
        x["race_rows"][0]["last_official_original_receipt_self_recorded_jst"] = (
            "2026-11-09T14:25:15+09:00")
        with self.assertRaises(ValueError):
            compose(triple(), paired(), x)

    def test_duplicated_source_race_does_not_count_twice(self):
        x = paired()
        x["race_rows"][0] = deepcopy(x["race_rows"][1])
        with self.assertRaises(ValueError):
            compose(triple(), x, artifact())

    def test_missing_actual_model_consumption_cannot_be_promoted(self):
        x = paired()
        x["race_rows"][0]["forecasts"]["clean"][
            "independent_actual_model_original_consumption_verified"] = True
        with self.assertRaises(ValueError):
            compose(triple(), x, artifact())

    def test_false_remote_first_commit_flag_does_not_pass(self):
        x = paired()
        x["race_rows"][1]["forecasts"]["v2_four_mode"][
            "first_git_remote_receipt_verified"] = True
        with self.assertRaises(ValueError):
            compose(triple(), x, artifact())

    def test_upstream_formal_truthy_flags_cannot_poison_history(self):
        for key, value in (
            ("formal", True),
            ("t12_eligible", True),
            ("accuracy_scoring_allowed", 1),
            ("new_formal_certifications", 1),
            ("formal_accuracy_denominator", 3),
        ):
            x = paired()
            x[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                compose(triple(), x, artifact())

    def test_archive_deadline_or_pair_timeliness_mismatch_rejected(self):
        x = artifact()
        x["race_rows"][1]["github_artifact_updated_before_t12_one_sec_margin"] = False
        with self.assertRaises(ValueError):
            compose(triple(), paired(), x)
        x = artifact()
        x["race_rows"][1]["official_t12_cutoff_jst"] = (
            "2026-11-09T14:29:00+09:00")
        with self.assertRaises(ValueError):
            compose(triple(), paired(), x)


if __name__ == "__main__":
    unittest.main()
