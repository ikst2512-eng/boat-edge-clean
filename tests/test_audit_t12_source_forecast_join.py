"""Fail-closed read-only scheduled source pair + frozen model tests."""
import unittest
from copy import deepcopy

from scripts.audit_t12_source_forecast_join import inspect, run

RUN = 42769768447
ART = 13740574410
DIGEST = "cdfdeae53222a5b7852ba5cf5b6b44080247ec074c8d3dbaf53c4a32fe9706dd"
FORECAST = "c4d39245cbc96b6c680585a68c3b9adf6ddeb921"
DAY = "20261110"
CODES = ("202611101202", "202611102211")


def original():
    rows = []
    for code, complete, limit, last, count in [
        (CODES[0], True, "15:40:00", "15:38:04", 6),
        (CODES[1], False, "15:46:00", "15:38:23", 0),
    ]:
        rows.append({
            "race_code": code, "reported_status":
                "pair_complete" if complete else "pair_not_ready",
            "official_beforeinfo_original_replayed": True,
            "official_odds_original_replayed": True,
            "official_racelist_original_replayed": False,
            "two_originals_complete_by_t12": complete,
            "exhibition_time_observed_boats": count,
            "start_exhibition_six_valid_rows": complete,
            "official_odds_120_verified": True,
            "official_t12_cutoff_jst": f"2026-11-10T{limit}+09:00",
            "beforeinfo_received_jst": "2026-11-10T15:37:54+09:00",
            "last_source_received_jst": f"2026-11-10T{last}+09:00",
            "formal": False,
        })
    return {
        "schema": "T12_ACTUAL_SCHEDULED_SOURCE_PAIR_ZIP_REPLAY_V1",
        "run_id": RUN, "day_jst": DAY, "candidate_count": 2,
        "race_rows": rows, "two_original_complete_race_count": 1,
        "original_actions_artifact_sha256": DIGEST,
        "github_artifact_digest_metadata_matches": True,
        "extracted_original_source_bytes_replayed": True,
        "github_original_zip_digest_verified_by_local_hash": False,
        "official_racelist_originals_verified": 0,
        "full_t12_source_certified": False,
        "formal": False,
    }


def artifact():
    return {
        "id": ART, "name": f"independent-late-preview-{RUN}",
        "digest": "sha256:" + DIGEST, "expired": False,
        "workflow_run": {"id": RUN}, "size_in_bytes": 32936,
        "created_at": "2026-11-10T06:38:25Z",
        "updated_at": "2026-11-10T06:38:25Z",
    }


def workflow():
    return {
        "id": RUN, "path": ".github/workflows/research-live-preview-evidence.yml",
        "event": "schedule", "status": "completed", "conclusion": "success",
        "created_at": "2026-11-10T06:37:36Z",
        "updated_at": "2026-11-10T06:38:30Z",
    }


def frozen(path):
    code = path.split("/")[-1].removesuffix(".json")
    is_v2 = path.startswith("four_mode_forecasts/")
    generated = (
        "2026-11-10T01:39:35+09:00" if is_v2 else
        "2026-11-10T07:44:29+09:00")
    return ({
        "race_code": code, "generated_at_jst" if is_v2 else "generated_at": generated,
        "input_source_kind": "public_pre_race_csv",
        "beforeinfo": "optional_not_in_snapshot" if is_v2 else None,
    }, {
        "pinned_remote_commit": FORECAST,
        "remote_sha256": "a" * 64, "remote_git_blob_sha1": "b" * 40,
    })


def verify(s=None, a=None, w=None, get=frozen):
    return inspect(
        s or original(), a or artifact(), w or workflow(), get,
        run_id=RUN, artifact_id=ART, original_sha256=DIGEST,
        forecast_ref=FORECAST, expected_races=CODES)


class TimelySourceIsNotSourceConsumingForecast(unittest.TestCase):
    def test_real_nov10_shape_is_one_complete_pair_and_zero_formal(self):
        result = verify()
        self.assertEqual(result["complete_two_original_races"], 1)
        self.assertEqual(result["original_source_candidate_races"], 2)
        self.assertEqual(result["matched_immutable_forecasts"], 4)
        self.assertEqual(result["forecasts_generated_after_originals"], 0)
        self.assertEqual(result["same_race_complete_official_three_originals"], 0)
        self.assertEqual(result["verified_first_forecast_remote_acceptances"], 0)
        self.assertEqual(result["new_formal_certifications"], 0)
        self.assertIsNone(result["formal_accuracy_denominator"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["original_zip_directly_rehashed_inside_ci"])

    def test_positive_pair_has_independent_source_zip_publication_only(self):
        rows = {row["race_code"]: row for row in verify()["race_rows"]}
        self.assertTrue(rows[CODES[0]]["source_pair_complete_by_t12"])
        self.assertTrue(rows[CODES[0]]["independent_source_zip_published_by_t12"])
        self.assertFalse(rows[CODES[0]]["official_racelist_original_replayed"])
        self.assertFalse(rows[CODES[0]]["frozen_forecasts"]["clean"]["generated_after_pair_sources"])
        self.assertEqual(rows[CODES[0]]["source_pair_first_blocker"],
                         "official_racelist_original_missing")
        self.assertFalse(rows[CODES[1]]["source_pair_complete_by_t12"])
        self.assertEqual(rows[CODES[1]]["exhibition_time_observed_boats"], 0)

    def test_github_green_skipped_or_manual_not_equivalent_to_schedule_capture(self):
        for values in ({"event": "workflow_run"}, {"event": "workflow_dispatch"},
                       {"path": "other.yml"}, {"conclusion": "failure"},
                       {"status": "in_progress"}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                verify(w={**workflow(), **values})

    def test_wrong_artifact_identity_hash_expiration_or_parent_rejected(self):
        for values in ({"id": ART + 1}, {"digest": "sha256:" + "0"*64},
                       {"expired": True}, {"size_in_bytes": 0},
                       {"workflow_run": {"id": RUN - 1}}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                verify(a={**artifact(), **values})

    def test_cross_race_and_cross_day_artifact_not_joinable(self):
        for value in (("202611101202", "202611101202"),
                      ("202611101202", "202611111211")):
            with self.subTest(codes=value), self.assertRaises(ValueError):
                inspect(original(), artifact(), workflow(), frozen,
                        run_id=RUN, artifact_id=ART, original_sha256=DIGEST,
                        forecast_ref=FORECAST, expected_races=value)

    def test_source_report_forged_complete_or_zip_receipt_rejected(self):
        s = original()
        s["race_rows"][1]["two_originals_complete_by_t12"] = True
        with self.assertRaises(ValueError):
            verify(s=s)
        a = artifact()
        a["updated_at"] = "2026-11-10T06:37:00Z"
        with self.assertRaises(ValueError):
            verify(a=a)
        s = original()
        s["github_original_zip_digest_verified_by_local_hash"] = True
        with self.assertRaises(ValueError):
            verify(s=s)

    def test_synthetic_post_source_forecast_is_not_model_consumption_proof(self):
        def after(path):
            item, meta = frozen(path)
            item = dict(item)
            if path.startswith("prospective_predictions/"):
                item["generated_at"] = "2026-11-10T15:38:10+09:00"
            return item, meta
        report = verify(get=after)
        self.assertEqual(report["forecasts_generated_after_originals"], 2)
        self.assertEqual(report["verified_model_original_byte_consumption"], 0)
        self.assertEqual(report["new_formal_certifications"], 0)
        self.assertFalse(report["accuracy_scoring_allowed"])

    def test_forecast_identity_and_ambiguous_clocks_fail_closed(self):
        def bad_id(path):
            j, meta = frozen(path)
            return {**j, "race_code": "202611100401"}, meta
        with self.assertRaises(ValueError):
            verify(get=bad_id)
        def duplicate_clock(path):
            j, meta = frozen(path)
            return {**j, "generated_at": "2026-11-10T12:00:00+09:00"}, meta
        with self.assertRaises(ValueError):
            verify(get=duplicate_clock)

    def test_run_injects_only_authenticated_pinned_readers(self):
        calls = []
        def get_meta(*args):
            calls.append(("meta", args[-1]))
            return artifact()
        def audit(root, **kw):
            calls.append(("source", kw["run_id"]))
            return original()
        def get_run(*args):
            calls.append(("run", args[-1]))
            return workflow()
        def get_frozen(repo, token, ref, path):
            calls.append(("forecast", path))
            return frozen(path)
        report = run(
            "ikst2512-eng/boat-edge-clean", "testtoken", "/not/used",
            run_id=RUN, artifact_id=ART, digest=DIGEST, forecast_ref=FORECAST,
            expected_races=CODES, metadata_getter=get_meta,
            extracted_auditor=audit, get_run=get_run, frozen_getter=get_frozen)
        self.assertEqual(report["matched_immutable_forecasts"], 4)
        self.assertEqual(len([x for x in calls if x[0] == "forecast"]), 4)
        self.assertEqual(calls[:3], [("meta", ART), ("source", RUN), ("run", RUN)])


if __name__ == "__main__":
    unittest.main()
