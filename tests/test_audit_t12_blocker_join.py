"""Synthetic metadata snapshots only; never a source-complete T12 fixture."""
import unittest
from copy import deepcopy

from scripts.audit_t12_blocker_join import join


def schedule(**overrides):
    row = {
        "schema": "OFFICIAL_PAIR_SCHEDULE_CONTINUITY_AUDIT_V1",
        "utc_day": "20261108",
        "as_of_utc": "2026-11-08T11:45:30+00:00",
        "workflow_path": ".github/workflows/research-live-preview-evidence.yml",
        "expected_cron_assumption": "*/5 0-12 * * *",
        "elapsed_nominal_slots_at_snapshot": 142,
        "observed_official_pair_schedule_runs": 1,
        "observed_within_declared_cron_hours": 1,
        "observed_outside_declared_cron_hours": 0,
        "expected_slots_full_day": 156,
        "schedule_slot_identity_verified": False,
        "raw_official_source_receipts_verified": False,
        "full_t12_source_certified": False,
        "runs": [{"run_id": 42450048245}],
    }
    row.update(overrides)
    return row


def archive(**overrides):
    row = {
        "schema": "T12_EXTERNAL_ARCHIVE_DAY_PRESENCE_AUDIT_V1",
        "day_jst": "20261108",
        "evidence_branch": "research-t12-external-evidence",
        "evidence_branch_commit_sha": "d0ed89f146dff117021c2bc042b20259d6715515",
        "existing_day_directories": ["20261103"],
        "day_directory_present": False,
        "race_directory_count": 0,
        "race_directories": [],
        "status": "no_persisted_three_original_day_directory",
        "originals_replayed": False,
        "github_initial_remote_receipt_verified": False,
        "full_t12_source_certified": False,
        "formal": False,
    }
    row.update(overrides)
    return row


class SameDayT12BlockedResearchAudit(unittest.TestCase):
    def test_actual_shape_missing_day_is_not_formal(self):
        report = join(schedule(), archive())
        self.assertEqual(report["day_jst"], "20261108")
        self.assertEqual(report["official_pair_collector_schedule_runs_observed"], 1)
        self.assertEqual(report["durable_three_original_race_directories"], 0)
        self.assertEqual(report["candidate_status"], "no_durable_three_originals")
        self.assertIn("no_durable_official_three_original_race_directories",
                      report["missing_requirements"])
        self.assertEqual(report["new_formal_certifications"], 0)
        self.assertIsNone(report["formal_accuracy_denominator"])
        self.assertFalse(report["formal"])
        self.assertFalse(report["accuracy_scoring_allowed"])
        self.assertFalse(report["per_slot_http_failures_inferred"])

    def test_future_archive_directory_not_auto_certified(self):
        a = archive(existing_day_directories=["20261103", "20261108"],
                    day_directory_present=True,
                    race_directory_count=1,
                    race_directories=["202611080309"],
                    status="persisted_race_directories_unverified")
        report = join(schedule(), a)
        self.assertEqual(report["candidate_status"],
                         "durable_directories_exist_but_not_verified")
        self.assertIn("persisted_official_three_original_bytes_not_reaudited",
                      report["missing_requirements"])
        self.assertEqual(report["new_formal_certifications"], 0)
        self.assertFalse(report["t12_eligible"])

    def test_prior_utc_cohort_mismatch_must_fail(self):
        with self.assertRaisesRegex(ValueError, "mismatched UTC"):
            join(schedule(utc_day="20261107"), archive())

    def test_wrong_schema_or_unverified_report_rejected(self):
        for input_record, bad in (
                ("schedule", {"schema": "NONE"}),
                ("schedule", {"full_t12_source_certified": True}),
                ("schedule", {"raw_official_source_receipts_verified": True}),
                ("schedule", {"schedule_slot_identity_verified": True}),
                ("archive", {"schema": "NOT_AN_ARCHIVE"}),
                ("archive", {"originals_replayed": True}),
                ("archive", {"formal": True}),
                ("archive", {"github_initial_remote_receipt_verified": True}),
        ):
            with self.subTest(record=input_record, bad=bad):
                s, a = schedule(), archive()
                (s if input_record == "schedule" else a).update(bad)
                with self.assertRaises(ValueError):
                    join(s, a)

    def test_unreconciled_schedule_counts_rejected(self):
        bad = (
            {"observed_official_pair_schedule_runs": 2},
            {"observed_within_declared_cron_hours": 0},
            {"elapsed_nominal_slots_at_snapshot": -1},
            {"elapsed_nominal_slots_at_snapshot": 157},
            {"elapsed_nominal_slots_at_snapshot": True},
            {"expected_slots_full_day": 150},
            {"runs": [{"run_id": 1}, {"run_id": 2}]},
            {"observed_outside_declared_cron_hours": 1},
        )
        for obj in bad:
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                join(schedule(**obj), archive())

    def test_missing_day_and_saved_counts_cannot_disagree(self):
        for item in (
            {"race_directory_count": 1, "race_directories": ["202611080309"]},
            {"day_directory_present": True},
            {"status": "persisted_race_directories_unverified"},
        ):
            with self.subTest(item=item), self.assertRaises(ValueError):
                join(schedule(), archive(**item))

    def test_race_directory_requires_same_day_and_valid_bijective_identity(self):
        a = archive(existing_day_directories=["20261108"], day_directory_present=True,
                    status="persisted_race_directories_unverified")
        for races in (["202611090309"], ["202611082501"],
                      ["202611080313"], ["202611080309", "202611080309"],
                      ["202611080309", "not-a-code"]):
            with self.subTest(races=races), self.assertRaises(ValueError):
                join(schedule(), {**a, "race_directories": races,
                                  "race_directory_count": len(races)})

    def test_historical_utc_snapshot_allowed_only_after_all_slots(self):
        valid = schedule(
            as_of_utc="2026-11-09T11:00:00+00:00",
            elapsed_nominal_slots_at_snapshot=156,
        )
        report = join(valid, archive())
        self.assertEqual(report["nominal_elapsed_five_minute_slots"], 156)
        with self.assertRaises(ValueError):
            join({**valid, "elapsed_nominal_slots_at_snapshot": 155}, archive())
        with self.assertRaises(ValueError):
            join(schedule(as_of_utc="2026-11-07T21:00:00+00:00"), archive())

    def test_first_utc_slot_is_one_not_zero_even_if_none_observed(self):
        report = join(schedule(
            as_of_utc="2026-11-08T00:00:00+00:00",
            elapsed_nominal_slots_at_snapshot=1,
            observed_official_pair_schedule_runs=0,
            observed_within_declared_cron_hours=0,
            runs=[]
        ), archive())
        self.assertEqual(report["invocation_count_deficit_in_cron_hours"], 1)
        self.assertEqual(report["invocation_count_coverage_pct"], 0.0)
        with self.assertRaises(ValueError):
            join(schedule(
                as_of_utc="2026-11-08T00:00:00+00:00",
                elapsed_nominal_slots_at_snapshot=0,
                observed_official_pair_schedule_runs=0,
                observed_within_declared_cron_hours=0,
                runs=[]
            ), archive())

    def test_same_day_branch_version_stays_read_only(self):
        report = join(schedule(), archive())
        self.assertEqual(report["evidence_branch_commit_sha"],
                         "d0ed89f146dff117021c2bc042b20259d6715515")
        self.assertFalse(report["archived_original_bytes_verified_by_this_join"])
        self.assertFalse(report["schedule_missing_trigger_cause_known"])
        self.assertEqual(report["priority_owner"], "source_collector_owner_1")


if __name__ == "__main__":
    unittest.main()
