"""Fail-closed Nov9 GitHub-origin artifact publication time / original-pair tests."""
import unittest
from copy import deepcopy

from scripts.audit_t12_remote_artifact_publication import audit, inspect
from scripts.audit_t12_nov09_real_pair_forecast_replay import (
    ARTIFACT_ID, RUN_ID, ZIP_SHA256,
)


def source():
    items = []
    for code, cutoff, last in (
        ("202611091110", "2026-11-09T14:30:00+09:00",
         "2026-11-09T14:26:59.498535+09:00"),
        ("202611091710", "2026-11-09T14:28:00+09:00",
         "2026-11-09T14:26:41.921482+09:00"),
    ):
        mode = {
            "generated_strictly_after_official_pair": False,
            "first_git_remote_receipt_verified": False,
            "independent_actual_model_original_consumption_verified": False,
            "formal": False,
        }
        items.append({
            "race_code": code,
            "official_latest_original_received_jst": last,
            "official_t12_cutoff_jst": cutoff,
            "official_pair_originals_replayed_complete": True,
            "racelist_official_original_present": False,
            "formal": False,
            "accuracy_scoring_allowed": False,
            "forecasts": {"clean": dict(mode), "v2_four_mode": dict(mode)},
        })
    return {
        "schema": "T12_NOV09_REAL_OFFICIAL_PAIR_VS_FROZEN_FORECAST_V1",
        "source_run_id": RUN_ID,
        "source_artifact_id": ARTIFACT_ID,
        "github_original_artifact_digest_from_metadata": ZIP_SHA256,
        "extracted_official_source_originals_replayed": True,
        "github_original_zip_digest_locally_rehashed_by_ci": False,
        "two_original_complete_races": 2,
        "matched_pinned_forecasts": 4,
        "matched_forecasts_generated_after_sources": 0,
        "three_official_original_races": 0,
        "new_formal_certifications": 0,
        "formal_accuracy_denominator": None,
        "formal": False,
        "accuracy_scoring_allowed": False,
        "race_rows": items,
    }


def remote():
    return {
        "id": ARTIFACT_ID,
        "name": f"independent-late-preview-{RUN_ID}",
        "digest": f"sha256:{ZIP_SHA256}",
        "expired": False,
        "size_in_bytes": 28063,
        "created_at": "2026-11-09T05:27:00Z",
        "updated_at": "2026-11-09T05:27:00Z",
        "workflow_run": {
            "id": RUN_ID, "head_branch": "main",
            "head_sha": "d0176b671363bed275045a0d454732f7cabff1a8",
        },
    }


def workflow():
    return {
        "id": RUN_ID,
        "event": "schedule",
        "path": ".github/workflows/research-live-preview-evidence.yml",
        "head_branch": "main",
        "head_sha": "d0176b671363bed275045a0d454732f7cabff1a8",
        "status": "completed", "conclusion": "success",
        "created_at": "2026-11-09T05:26:15Z",
        "run_started_at": "2026-11-09T05:26:15Z",
        "updated_at": "2026-11-09T05:27:04Z",
    }


class GithubSourceArtifactRemotePublication(unittest.TestCase):
    def test_actual_nov9_two_original_artifacts_uploaded_before_t12(self):
        report = inspect(source(), remote(), workflow())
        self.assertEqual(report["server_timestamp_artifact_archive_before_t12_races"], 2)
        self.assertEqual(report["github_artifact_updated_at_utc"],
                         "2026-11-09T05:27:00+00:00")
        margins = {x["race_code"]: x["github_archive_to_cutoff_margin_seconds"]
                   for x in report["race_rows"]}
        self.assertEqual(margins, {"202611091110": 180.0, "202611091710": 60.0})
        self.assertFalse(report["formal"])
        self.assertFalse(report["t12_eligible"])
        self.assertFalse(report["accuracy_scoring_allowed"])
        self.assertEqual(report["new_formal_certifications"], 0)
        self.assertIsNone(report["formal_accuracy_denominator"])
        self.assertTrue(report["source_artifact_server_time_not_first_forecast_git_receipt"])

    def test_late_artifact_timestamps_are_not_remotely_timely(self):
        item = remote()
        item["created_at"] = "2026-11-09T05:28:30Z"
        item["updated_at"] = "2026-11-09T05:28:30Z"
        running = workflow()
        running["updated_at"] = "2026-11-09T05:29:30Z"
        report = inspect(source(), item, running)
        dates = {x["race_code"]: x["github_artifact_updated_before_t12_one_sec_margin"]
                 for x in report["race_rows"]}
        self.assertEqual(dates, {"202611091110": True, "202611091710": False})
        self.assertEqual(report["server_timestamp_artifact_archive_before_t12_races"], 1)
        self.assertFalse(report["formal"])

    def test_exact_cutoff_second_is_not_pass(self):
        a = remote()
        a["created_at"] = a["updated_at"] = "2026-11-09T05:28:00Z"
        r = workflow()
        r["updated_at"] = "2026-11-09T05:28:05Z"
        result = inspect(source(), a, r)
        by_race = {x["race_code"]: x for x in result["race_rows"]}
        self.assertFalse(
            by_race["202611091710"]["github_artifact_updated_before_t12_one_sec_margin"])

    def test_source_replay_absent_or_truthy_certification_rejected(self):
        for changes in (
            {"schema": "unknown"},
            {"two_original_complete_races": 1},
            {"matched_forecasts_generated_after_sources": 1},
            {"extracted_official_source_originals_replayed": False},
            {"extracted_official_source_originals_replayed": 1},
            {"github_original_artifact_digest_from_metadata": "0" * 64},
            {"three_official_original_races": 2},
            {"new_formal_certifications": 1},
            {"formal": True},
            {"accuracy_scoring_allowed": True},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                inspect({**source(), **changes}, remote(), workflow())

    def test_artifact_id_digest_expired_and_size_fail_closed(self):
        for changes in (
            {"id": ARTIFACT_ID + 1},
            {"id": True},
            {"name": "other-run-artifact"},
            {"digest": "sha256:" + "0" * 64},
            {"expired": True},
            {"size_in_bytes": 0},
            {"size_in_bytes": True},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                inspect(source(), {**remote(), **changes}, workflow())

    def test_parent_run_must_match_actual_schedule_job(self):
        for changes in (
            {"event": "workflow_dispatch"},
            {"path": ".github/workflows/clean-prospective.yml"},
            {"head_branch": "research"},
            {"head_sha": "f" * 40},
            {"conclusion": "failure"},
            {"status": "in_progress"},
            {"id": RUN_ID + 1},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                inspect(source(), remote(), {**workflow(), **changes})
        a = remote()
        a["workflow_run"] = {**a["workflow_run"], "id": RUN_ID + 1}
        with self.assertRaises(ValueError):
            inspect(source(), a, workflow())

    def test_unordered_or_false_timestamps_do_not_pass(self):
        for changes in (
            {"created_at": "2026-11-09T05:26:10Z"},
            {"created_at": "2026-11-09T05:27:10Z"},
            {"updated_at": "2026-11-09T05:26:30Z"},
            {"created_at": "2026-11-09T05:27:00+00:00"},
            {"updated_at": "2026-11-09T05:27:00.123Z"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                inspect(source(), {**remote(), **changes}, workflow())
        with self.assertRaises(ValueError):
            inspect(source(), remote(), {**workflow(), "updated_at":
                                         "2026-11-09T05:26:59Z"})

    def test_missing_race_or_second_original_not_accepted(self):
        for bad in (
            {"race_rows": source()["race_rows"][:1]},
            {"race_rows": [source()["race_rows"][0], source()["race_rows"][0]]},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                inspect({**source(), **bad}, remote(), workflow())
        for changes in (
            {"official_pair_originals_replayed_complete": False},
            {"racelist_official_original_present": True},
            {"formal": True},
            {"accuracy_scoring_allowed": True},
        ):
            s = source()
            s["race_rows"][0] = {**s["race_rows"][0], **changes}
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                inspect(s, remote(), workflow())

    def test_cutoff_and_source_receipt_chronology_enforced(self):
        for field, when in (
            ("official_latest_original_received_jst", "2026-11-09T14:31:00+09:00"),
            ("official_latest_original_received_jst", "2026-11-09T14:20:00+09:00"),
            ("official_latest_original_received_jst", "2026-11-10T14:26:59+09:00"),
            ("official_t12_cutoff_jst", "2026-11-09T14:25:00+09:00"),
        ):
            s = source()
            s["race_rows"][0][field] = when
            with self.subTest(field=field,when=when), self.assertRaises(ValueError):
                inspect(s, remote(), workflow())

    def test_model_forecast_gates_cannot_be_bypassed(self):
        s = source()
        s["race_rows"][0]["forecasts"]["clean"][
            "generated_strictly_after_official_pair"] = True
        with self.assertRaises(ValueError):
            inspect(s, remote(), workflow())
        s = source()
        s["race_rows"][0]["forecasts"]["v2_four_mode"]["first_git_remote_receipt_verified"] = True
        with self.assertRaises(ValueError):
            inspect(s, remote(), workflow())

    def test_read_only_api_delegation_injected_metadata(self):
        calls = []
        def artifact(repo, token, number):
            calls.append(("artifact", repo, number))
            return remote()
        def run(repo, token, number):
            calls.append(("run", repo, number))
            return workflow()
        result = audit("ikst2512-eng/boat-edge-clean", "token", source(),
                       get_artifact=artifact, get_run=run)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["server_timestamp_artifact_archive_before_t12_races"], 2)
        self.assertFalse(result["formal"])

    def test_invalid_repository_credentials_rejected(self):
        for repo, token in (
            ("ikst2512-eng/boat-edge-clean", None),
            ("bad", "token"),
            ("../bad", "token"),
            ("a/..", "token"),
        ):
            with self.subTest(repo=repo), self.assertRaises(ValueError):
                audit(repo, token, source(), get_artifact=lambda *x: remote(),
                      get_run=lambda *x: workflow())


if __name__ == "__main__":
    unittest.main()
