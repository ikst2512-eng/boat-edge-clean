"""Synthetic adversarial tests for original Git-byte census; never scores races."""
import hashlib
import json
import unittest

from research import hole_pair_real_main_snapshot_gate as g

DAY = "20261110"
SOURCE = "a" * 40
REFERENCE = "2026-11-10T10:52:00+09:00"
CODE = "202611100401"
MODEL = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"


def sample(code=CODE, **changes):
    obj = {
        "race_code": code,
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "model_version": MODEL,
        "status": "provisional",
        "modes": {"hole": {"tickets": [{"combo": "1-2-3"}]}},
        "generated_at_jst": "2026-11-10T10:40:00+09:00",
        "deadline_jst": "2026-11-10T11:12:00+09:00",
        "beforeinfo": "optional_not_in_snapshot",
    }
    obj.update(changes)
    return json.dumps(obj, sort_keys=True).encode()


def fixture(records):
    blobs, lines = {}, []
    for code, raw in records:
        sha1 = hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\x00" + raw
        ).hexdigest()
        blobs[sha1] = raw
        lines.append(f"100644 blob {sha1}\tfour_mode_forecasts/{code}.json")
    return "\n".join(lines) + "\n", lambda sha: blobs[sha]


class RealMainSourceSnapshotTests(unittest.TestCase):
    def test_valid_original_blob_checks_sha1_and_sha256_without_formal_admission(self):
        original = sample()
        tree, fetch = fixture([(CODE, original)])
        result = g.audit(DAY, SOURCE, REFERENCE, tree, fetch)
        self.assertEqual(result["original_git_blob_sha1_verified_count"], 1)
        self.assertEqual(result["original_main_forecast_ids_examined"], 1)
        self.assertEqual(result["optional_beforeinfo_absent_from_forecast"], 1)
        self.assertEqual(result["locally_generated_before_declared_t12"], 1)
        self.assertEqual(result["declared_t12_still_future_at_reference"], 1)
        self.assertEqual(
            result["rows"][0]["source_sha256_from_verified_git_bytes"],
            hashlib.sha256(original).hexdigest())
        self.assertEqual(result["prospective_pilot_formally_eligible"], 0)
        self.assertEqual(result["prospective_confirmation_formally_eligible"], 0)
        self.assertFalse(result["formal"])
        self.assertFalse(result["result_files_read"])

    def test_future_and_expired_declared_t12_are_not_equivalent_to_formal(self):
        a = sample()
        b = sample("202611100402", deadline_jst="2026-11-10T10:49:00+09:00")
        tree, fetch = fixture([(CODE, a), ("202611100402", b)])
        result = g.audit(DAY, SOURCE, REFERENCE, tree, fetch)
        self.assertEqual(result["declared_t12_still_future_at_reference"], 1)
        self.assertEqual(result["declared_t12_elapsed_at_reference"], 1)
        self.assertEqual(result["not_generated_before_declared_t12"], 1)
        self.assertEqual(result["original_main_forecast_ids_examined"], 2)
        self.assertFalse(result["whole_day_official_schedule_verified"])

    def test_populated_beforeinfo_field_still_never_promotes_to_official(self):
        tree, fetch = fixture([(CODE, sample(beforeinfo={"boats": [1, 2, 3, 4, 5, 6]}))])
        result = g.audit(DAY, SOURCE, REFERENCE, tree, fetch)
        self.assertEqual(result["beforeinfo_field_not_officially_verified"], 1)
        self.assertEqual(result["same_race_official_t12_origins_authenticated"], 0)
        self.assertFalse(result["rows"][0]["official_complete_six_boat_beforeinfo_verified"])
        self.assertFalse(result["rows"][0]["official_complete_120_way_odds_verified"])

    def test_sha1_mismatch_fails_closed_before_metadata(self):
        tree, _ = fixture([(CODE, sample())])
        with self.assertRaisesRegex(ValueError, "original_git_blob_sha1_mismatch"):
            g.audit(DAY, SOURCE, REFERENCE, tree,
                    lambda sha: sample(generated_at_jst="2026-11-10T10:41:00+09:00"))

    def test_unsupported_model_schema_and_postresult_field_rejected(self):
        for field, value in (
            ("model_version", "UNAPPROVED_MODEL"),
            ("schema", "RESULT_BASED_RANKING"),
            ("status", "confirmed_result"),
            ("race_code", "202611100402"),
            ("modes", []),
        ):
            tree, fetch = fixture([(CODE, sample(**{field: value}))])
            with self.subTest(field=field), self.assertRaisesRegex(
                    ValueError, "unexpected_original_model_or_identity"):
                g.audit(DAY, SOURCE, REFERENCE, tree, fetch)

    def test_snapshot_file_not_necessarily_official_day_or_race_census(self):
        r = g.audit(DAY, SOURCE, REFERENCE, "", lambda sha: None)
        self.assertEqual(r["original_main_forecast_ids_examined"], 0)
        self.assertFalse(r["whole_day_official_schedule_verified"])
        self.assertEqual(r["prospective_pilot_formally_eligible"], 0)

    def test_invalid_dates_timezones_or_generation_clock_rejected(self):
        for field, value in (
            ("generated_at_jst", "2026-11-10T10:40:00Z"),
            ("generated_at_jst", "2026-11-09T10:40:00+09:00"),
            ("deadline_jst", "not-a-clock"),
            ("deadline_jst", None),
        ):
            tree, fetch = fixture([(CODE, sample(**{field: value}))])
            with self.subTest(field=field), self.assertRaises(ValueError):
                g.audit(DAY, SOURCE, REFERENCE, tree, fetch)

    def test_symlink_and_unexpected_git_paths_are_rejected(self):
        tree, fetch = fixture([(CODE, sample())])
        with self.assertRaises(ValueError):
            g.audit(DAY, SOURCE, REFERENCE,
                    tree.replace("100644 blob", "120000 blob"), fetch)
        with self.assertRaises(ValueError):
            g.audit(DAY, SOURCE, REFERENCE,
                    tree.replace("four_mode_forecasts/", "confirmed_results/"), fetch)

    def test_canonical_id_day_and_commit_required(self):
        tree, fetch = fixture([(CODE, sample())])
        for day, sha, stamp in (
            ("20261108", SOURCE, REFERENCE),
            ("20261110", "short", REFERENCE),
            (DAY, SOURCE, "2026-11-10T10:52:00Z"),
            (DAY, SOURCE, "2026-11-11T10:52:00+09:00"),
        ):
            with self.subTest(day=day, sha=sha, stamp=stamp), self.assertRaises(ValueError):
                g.audit(day, sha, stamp, tree, fetch)

    def test_wrong_bytes_or_large_blob_rejected(self):
        tree, _ = fixture([(CODE, sample())])
        with self.assertRaises(ValueError):
            g.audit(DAY, SOURCE, REFERENCE, tree, lambda sha: b"X" * 30001)
        with self.assertRaises(ValueError):
            g.audit(DAY, SOURCE, REFERENCE, tree, lambda sha: "not bytes")

    def test_refuses_duplicate_original_paths(self):
        tree, fetch = fixture([(CODE, sample())])
        with self.assertRaisesRegex(ValueError, "duplicated_git_tree_forecast"):
            g.audit(DAY, SOURCE, REFERENCE, tree + tree, fetch)


if __name__ == "__main__":
    unittest.main()
