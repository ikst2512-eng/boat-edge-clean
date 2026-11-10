"""No network; historical orchestration must reject substituted/green source claims."""
import unittest
from copy import deepcopy

from scripts.audit_t12_archived_pair_forecast_replay import (
    ARTIFACTS, FORECAST_REF, reconcile, run
)

POSITIVE = {
    "20261105": ("202611051111", "2026-11-05T14:54:00+09:00",
                 "2026-11-05T14:50:49.136632+09:00",
                 "2026-11-05T14:50:58.419703+09:00"),
    "20261106": ("202611061410", "2026-11-06T14:53:00+09:00",
                 "2026-11-06T14:47:38.371341+09:00",
                 "2026-11-06T14:47:48.721444+09:00"),
    "20261108": ("202611080309", "2026-11-08T14:18:00+09:00",
                 "2026-11-08T14:15:38.139739+09:00",
                 "2026-11-08T14:15:48.378360+09:00"),
}
EARLY = {
    "202611051111": ("2026-11-05T11:04:24.496897+09:00",
                     "2026-11-05T11:15:10.119704+09:00"),
    "202611061410": ("2026-11-06T10:15:39.642861+09:00",
                     "2026-11-06T10:15:36.394911+09:00"),
    "202611080309": ("2026-11-08T10:12:31.149675+09:00",
                     "2026-11-08T10:17:12.313648+09:00"),
}


def source_runs():
    rows = []
    for run_id, _, digest, day in ARTIFACTS:
        positive = POSITIVE.get(day)
        race_rows = []
        if positive:
            code, cutoff, before, odds = positive
            race_rows.append({
                "race_code": code,
                "formal": False,
                "two_originals_complete_by_t12": True,
                "official_odds_120_verified": True,
                "official_t12_cutoff_jst": cutoff,
                "beforeinfo_received_jst": before,
                "last_source_received_jst": odds,
            })
        race_rows.append({
            "race_code": {"20261105": "202611052210",
                          "20261106": "202611060810",
                          "20261107": "202611071409",
                          "20261108": "202611081409"}[day],
            "formal": False,
            "two_originals_complete_by_t12": False,
        })
        if day == "20261107":
            race_rows.append({
                "race_code": "202611071110", "formal": False,
                "two_originals_complete_by_t12": False,
            })
        rows.append({
            "run_id": run_id, "day_jst": day, "artifact_sha256": digest,
            "status": "source_pairs_independently_replayed_nonformal",
            "full_t12_source_certified": False,
            "formal": False,
            "official_racelist_originals_verified": 0,
            "candidate_count": len(race_rows),
            "two_original_complete_race_count": 1 if positive else 0,
            "race_rows": race_rows,
        })
    return rows


def fake_frozen(path):
    code = path.rsplit("/", 1)[-1].removesuffix(".json")
    generation = EARLY[code][0 if path.startswith("prospective_") else 1]
    if path.startswith("prospective_"):
        forecast = {"race_code": code, "generated_at": generation,
                    "input_source_kind": "public_pre_race_csv"}
    else:
        forecast = {"race_code": code, "generated_at_jst": generation,
                    "beforeinfo": "optional_not_in_snapshot"}
    return forecast, {
        "pinned_remote_commit": FORECAST_REF,
        "remote_sha256": "a"*64,
        "remote_git_blob_sha1": "b"*40,
    }


class ArchivedOriginalForecastReplayTests(unittest.TestCase):
    def test_three_two_original_pairs_do_not_match_frozen_generation(self):
        result = reconcile(source_runs(), get_frozen=fake_frozen)
        self.assertEqual(result["four_archived_source_runs_replayed"], 4)
        self.assertEqual(result["source_pair_races"], 8)
        self.assertEqual(result["official_two_original_complete_races"], 3)
        self.assertEqual(result["matched_immutable_forecasts"], 6)
        self.assertEqual(result["forecasts_generated_after_sources"], 0)
        self.assertEqual(result["official_three_original_races"], 0)
        self.assertFalse(result["formal"])
        self.assertFalse(result["t12_eligible"])
        self.assertFalse(result["accuracy_scoring_allowed"])
        self.assertIsNone(result["formal_accuracy_denominator"])

    def test_matched_early_forecasts_have_source_after_generation(self):
        report = reconcile(source_runs(), get_frozen=fake_frozen)
        successful = [x for x in report["race_rows"] if
                      x["original_pair_replayed_complete"]]
        self.assertEqual(len(successful), 3)
        for race in successful:
            self.assertEqual(set(race["forecasts"]), {"clean", "v2_four_mode"})
            for mode in race["forecasts"].values():
                self.assertGreater(
                    mode["source_receipt_minus_generation_seconds"], 12000)
                self.assertFalse(mode["generated_strictly_after_official_source"])
                self.assertFalse(mode["model_consumed_official_original_bytes_verified"])
                self.assertFalse(mode["independent_first_github_remote_receipt_verified"])

    def test_incomplete_sources_do_not_trigger_frozen_lookup(self):
        result = reconcile(source_runs(), get_frozen=fake_frozen)
        failed = [r for r in result["race_rows"] if
                  not r["original_pair_replayed_complete"]]
        self.assertEqual(len(failed), 5)
        self.assertTrue(all(not x["forecasts"] for x in failed))

    def test_missing_one_real_run_fails_not_zero(self):
        with self.assertRaises(ValueError):
            reconcile(source_runs()[:-1], get_frozen=fake_frozen)

    def test_substituted_artifact_sha_fails(self):
        entries = source_runs()
        entries[0]["artifact_sha256"] = "f"*64
        with self.assertRaisesRegex(ValueError, "substituted"):
            reconcile(entries, get_frozen=fake_frozen)

    def test_unverified_positive_pair_cannot_skip_odds(self):
        entries = source_runs()
        entries[0]["race_rows"][0]["official_odds_120_verified"] = False
        with self.assertRaisesRegex(ValueError, "120"):
            reconcile(entries, get_frozen=fake_frozen)

    def test_counter_mismatch_rejected(self):
        entries = source_runs()
        entries[1]["two_original_complete_race_count"] = 2
        with self.assertRaisesRegex(ValueError, "count"):
            reconcile(entries, get_frozen=fake_frozen)

    def test_originals_receipt_after_cutoff_cannot_be_complete(self):
        entries = source_runs()
        entries[0]["race_rows"][0]["last_source_received_jst"] = (
            "2026-11-05T14:55:00+09:00")
        with self.assertRaisesRegex(ValueError, "contradictory"):
            reconcile(entries, get_frozen=fake_frozen)

    def test_frozen_race_identity_mismatch_rejected(self):
        def foreign(path):
            frozen, sha = fake_frozen(path)
            frozen["race_code"] = "202611080909"
            return frozen, sha
        with self.assertRaisesRegex(ValueError, "race identity"):
            reconcile(source_runs(), get_frozen=foreign)

    def test_missing_pinned_git_blob_proof_fails(self):
        def fake(path):
            frozen, sha = fake_frozen(path)
            sha["pinned_remote_commit"] = "f"*40
            return frozen, sha
        with self.assertRaisesRegex(ValueError, "unverified immutable"):
            reconcile(source_runs(), get_frozen=fake)

    def test_late_forecast_is_diagnostic_not_formal(self):
        def later(path):
            forecast, evidence = fake_frozen(path)
            if path.endswith("202611080309.json"):
                stamp = "2026-11-08T14:16:00+09:00"
                if "generated_at" in forecast:
                    forecast["generated_at"] = stamp
                else:
                    forecast["generated_at_jst"] = stamp
            return forecast, evidence
        report = reconcile(source_runs(), get_frozen=later)
        self.assertEqual(report["forecasts_generated_after_sources"], 2)
        self.assertFalse(report["formal"])
        self.assertFalse(report["independent_model_input_consumption_verified"])

    def test_403_artifact_failure_cannot_be_swallowed(self):
        def missing_archive(*args):
            raise PermissionError("HTTP 403 from GitHub Actions artifact")
        with self.assertRaises(PermissionError):
            run("owner/repo", "t", zip_loader=missing_archive,
                zip_auditor=lambda *args: None, frozen_getter=lambda *x: None)

    def test_unusable_frozen_timestamp_fails(self):
        def missing_time(path):
            frozen, evidence = fake_frozen(path)
            frozen.pop("generated_at", None)
            frozen.pop("generated_at_jst", None)
            return frozen, evidence
        with self.assertRaisesRegex(ValueError, "timestamp ambiguous"):
            reconcile(source_runs(), get_frozen=missing_time)


if __name__ == "__main__":
    unittest.main()
