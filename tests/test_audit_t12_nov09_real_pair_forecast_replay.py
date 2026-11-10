"""Strict Nov9 original+forecast join tests; real ZIP is independently replayed in CI."""
import unittest
from copy import deepcopy

from scripts.audit_t12_nov09_real_pair_forecast_replay import (
    ARTIFACT_ID, FORECAST_REF, RUN_ID, ZIP_SHA256, reconcile, run
)

RACES = ["202611091110", "202611091710"]
SOURCE_LAST = {
    "202611091110": ("2026-11-09T14:30:00+09:00",
                     "2026-11-09T14:26:50.194266+09:00",
                     "2026-11-09T14:26:59.498535+09:00"),
    "202611091710": ("2026-11-09T14:28:00+09:00",
                     "2026-11-09T14:26:32.711772+09:00",
                     "2026-11-09T14:26:41.921482+09:00"),
}
EARLY = {
    "202611091110": ("2026-11-09T10:31:48.770953+09:00",
                     "2026-11-09T10:38:07.795737+09:00"),
    "202611091710": ("2026-11-09T10:31:48.770953+09:00",
                     "2026-11-09T10:38:08.070980+09:00"),
}


def source():
    rows = []
    for code in RACES:
        cutoff, before, last = SOURCE_LAST[code]
        rows.append({
            "race_code": code, "formal": False,
            "two_originals_complete_by_t12": True,
            "official_odds_120_verified": True,
            "exhibition_time_observed_boats": 6,
            "start_exhibition_six_valid_rows": True,
            "official_racelist_original_replayed": False,
            "official_t12_cutoff_jst": cutoff,
            "beforeinfo_received_jst": before,
            "last_source_received_jst": last,
        })
    return {
        "run_id": RUN_ID, "day_jst": "20261109",
        "original_actions_artifact_sha256": ZIP_SHA256,
        "github_artifact_digest_metadata_matches": True,
        "extracted_original_source_bytes_replayed": True,
        "github_original_zip_digest_verified_by_local_hash": False,
        "official_racelist_originals_verified": 0,
        "full_t12_source_certified": False, "formal": False,
        "status": "source_pairs_independently_replayed_nonformal",
        "candidate_count": 2, "two_original_complete_race_count": 2,
        "race_rows": rows,
    }


def frozen(path, *, overrides=None):
    code = path.rsplit("/", 1)[-1].removesuffix(".json")
    is_clean = path.startswith("prospective_predictions/")
    generated = EARLY[code][0 if is_clean else 1]
    row = {"race_code": code,
           "generated_at" if is_clean else "generated_at_jst": generated}
    if is_clean:
        row["input_source_kind"] = "public_pre_race_csv"
    else:
        row["beforeinfo"] = "optional_not_in_snapshot"
    if overrides:
        row.update(overrides)
    return row, {
        "pinned_remote_commit": FORECAST_REF,
        "remote_sha256": "a"*64,
        "remote_git_blob_sha1": "b"*40,
    }


class Nov09ActualPairsAndEarlyForecasts(unittest.TestCase):
    def test_two_real_source_pairs_and_four_frozen_forecasts_remain_nonformal(self):
        result = reconcile(source(), get_frozen=frozen)
        self.assertEqual(result["two_original_complete_races"], 2)
        self.assertEqual(result["matched_pinned_forecasts"], 4)
        self.assertEqual(result["matched_forecasts_generated_after_sources"], 0)
        self.assertEqual(result["three_official_original_races"], 0)
        self.assertEqual(result["new_formal_certifications"], 0)
        self.assertIsNone(result["formal_accuracy_denominator"])
        self.assertFalse(result["formal"])
        for item in result["race_rows"]:
            self.assertTrue(item["official_pair_originals_replayed_complete"])
            self.assertFalse(item["racelist_official_original_present"])
            for mode in item["forecasts"].values():
                self.assertGreater(mode["last_official_source_minus_generation_seconds"], 13000)
                self.assertFalse(mode["generated_strictly_after_official_pair"])
                self.assertTrue(mode["generated_by_official_t12"])
                self.assertFalse(mode["formal"])
                self.assertFalse(mode["independent_actual_model_original_consumption_verified"])

    def test_missing_race_originals_cannot_become_zero(self):
        x = source()
        x["race_rows"] = x["race_rows"][:1]
        with self.assertRaisesRegex(ValueError, "roster"):
            reconcile(x, get_frozen=frozen)

    def test_green_aggregate_without_replayed_source_rejected(self):
        for changed in (
            {"extracted_original_source_bytes_replayed": False},
            {"github_artifact_digest_metadata_matches": False},
            {"two_original_complete_race_count": 1},
            {"status": "complete_pairs_observed"},
            {"original_actions_artifact_sha256": "f"*64},
            {"formal": True},
            {"official_racelist_originals_verified": 1},
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    reconcile({**source(), **changed}, get_frozen=frozen)

    def test_false_aggregate_pair_cannot_hide_incomplete_components(self):
        for field, value in (
            ("two_originals_complete_by_t12", 1),
            ("official_odds_120_verified", 1),
            ("exhibition_time_observed_boats", 5),
            ("start_exhibition_six_valid_rows", False),
            ("official_racelist_original_replayed", True),
            ("formal", True),
        ):
            x = source()
            x["race_rows"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                reconcile(x, get_frozen=frozen)

    def test_late_or_reversed_receipt_rejected(self):
        for field, value in (
            ("last_source_received_jst", "2026-11-09T14:31:00+09:00"),
            ("beforeinfo_received_jst", "2026-11-09T14:29:00+09:00"),
            ("official_t12_cutoff_jst", "2026-11-10T14:28:00+09:00"),
        ):
            x = source()
            x["race_rows"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                reconcile(x, get_frozen=frozen)

    def test_frozen_ref_and_identity_required(self):
        for changes in (
            {"pinned_remote_commit": "f"*40},
            {"remote_sha256": "not-sha"},
            {"remote_git_blob_sha1": "not-git-sha"},
        ):
            def bad(path):
                row, p = frozen(path)
                return row, {**p, **changes}
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                reconcile(source(), get_frozen=bad)
        with self.assertRaisesRegex(ValueError, "identity"):
            reconcile(source(), get_frozen=lambda path: frozen(path, overrides={
                "race_code": "202611090309"}))

    def test_same_second_generation_never_proves_input_or_first_remote(self):
        def second(path):
            code = path.rsplit("/", 1)[-1].removesuffix(".json")
            row, ref = frozen(path)
            key = "generated_at" if "generated_at" in row else "generated_at_jst"
            row[key] = SOURCE_LAST[code][2]
            row["input_source_kind"] = "official_three_originals"
            row["official_original_sha256"] = {
                "racelist": "a"*64, "beforeinfo": "b"*64, "odds": "c"*64,
            }
            return row, ref
        result = reconcile(source(), get_frozen=second)
        self.assertEqual(result["matched_forecasts_generated_after_sources"], 0)
        self.assertFalse(result["formal"])
        self.assertFalse(result["independent_model_input_consumption_verified"])

    def test_later_self_declared_official_inputs_remain_unverified(self):
        def later(path):
            row, ref = frozen(path)
            key = "generated_at" if "generated_at" in row else "generated_at_jst"
            row[key] = "2026-11-09T14:27:01+09:00"
            row["input_source_kind"] = "official_three_originals"
            return row, ref
        report = reconcile(source(), get_frozen=later)
        self.assertEqual(report["matched_forecasts_generated_after_sources"], 4)
        self.assertFalse(report["formal"])
        self.assertFalse(report["accuracy_scoring_allowed"])

    def test_authenticated_run_delegates_to_bounded_original_replay(self):
        recorded = {}
        def metadata(repo, token, id):
            recorded["metadata"] = id
            return {"id": id}
        def replay(root, **kwargs):
            recorded["root"] = str(root)
            recorded["replay_kwargs"] = kwargs
            return source()
        def getter(repo, token, ref, path):
            self.assertEqual(ref, FORECAST_REF)
            recorded.setdefault("paths", []).append(path)
            return frozen(path)
        result = run("ikst2512-eng/boat-edge-clean", "token", "/tmp/fake",
                     fetch_metadata=metadata,
                     replay_source=replay, get_forecast=getter)
        self.assertEqual(recorded["metadata"], ARTIFACT_ID)
        self.assertEqual(recorded["replay_kwargs"]["run_id"], RUN_ID)
        self.assertEqual(recorded["replay_kwargs"]["digest"], ZIP_SHA256)
        self.assertEqual(len(recorded["paths"]), 4)
        self.assertFalse(result["formal"])

    def test_missing_read_token_and_invalid_repository_fail_closed(self):
        for repo, token in (
            ("ikst2512-eng/boat-edge-clean", None),
            ("bad", "token"),
            ("bad/repo/extra", "token"),
        ):
            with self.subTest(repo=repo), self.assertRaises(ValueError):
                run(repo, token, "/tmp/fake")


if __name__ == "__main__":
    unittest.main()
