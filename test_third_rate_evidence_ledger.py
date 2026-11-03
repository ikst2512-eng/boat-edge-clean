import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from clean_four_modes import rank_modes
from research_model import probabilities
from four_mode_v2_third_rate_shadow import PROTOCOL, candidate
from third_rate_evidence_ledger import (prepare, publish, BRANCH,
    verify_first_add_git_provenance, verify_ledger_write_access,
    WRITE_PROBE_PATH, WRITE_PROBE_BYTES)

CODE = "202611040101"
SHA = "a" * 40
RATES = [5.2, 6.1, 4.6, 3.9, 4.8, 3.7]


class ThirdRateDurableLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        folder = self.root / "four_mode_forecasts"
        folder.mkdir()
        modes = rank_modes(probabilities(RATES))
        archive = {"race_code": CODE, "model_version":
                   "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
                   "deadline_jst": "2026-11-04T12:00:00+09:00",
                   "modes": modes}
        f = folder / (CODE + ".json")
        f.write_text(json.dumps(archive) + "\n", encoding="utf-8")
        baseline = [r["combo"] for r in modes["hit"]["tickets"]]
        after, _ = candidate(baseline, RATES, probabilities(RATES))
        self.data = {
            "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
            "protocol": PROTOCOL, "formal": False,
            "independent_remote_first_seen_verified": False,
            "production_forecast_changed": False,
            "status": "captured_local_after_push_not_remote_proven",
            "publication_commit_sha": SHA, "published_forecasts": 1,
            "frozen_before_t_minus_12": 1, "ineligible_count": 0,
            "validation_error_count": 0,
            "records": [{
                "race_code": CODE,
                "status": "frozen_in_same_job_before_t_minus_12",
                "source_commit_sha": SHA, "protocol": PROTOCOL,
                "baseline_top10": baseline, "candidate_top10": after,
                "frozen_at_utc": "2026-11-04T01:00:00+00:00",
                "t_minus_12_jst": "2026-11-04T11:48:00+09:00",
                "source_forecast_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            }],
        }
        self.storage = {}

    def original(self):
        return (json.dumps(self.data, sort_keys=True) + "\n").encode()

    def remote_read(self, path):
        return self.storage.get(path)

    def remote_create(self, path, original, run_id):
        self.assertNotIn(path, self.storage)
        self.storage[path] = original

    def test_first_publish_is_byte_exact_append_only_and_readback(self):
        raw = self.original()
        status = publish(raw, self.root, "412345", "1",
                         self.remote_read, self.remote_create)
        self.assertEqual(status["status"], "new_immutable_ledger_entry")
        self.assertTrue(status["stored"])
        self.assertEqual(status["branch"], BRANCH)
        self.assertEqual(status["path"],
                         "third_rate/20261104/run-412345-attempt-1.json")
        self.assertEqual(self.storage[status["path"]], raw)
        self.assertFalse(status["independent_remote_first_seen_verified"])
        self.assertFalse(status["formal"])

    def test_second_identical_write_idempotent_and_conflict_refused(self):
        raw = self.original()
        publish(raw, self.root, "412345", "1",
                self.remote_read, self.remote_create)
        seen = publish(raw, self.root, "412345", "1",
                       self.remote_read,
                       lambda *args: self.fail("attempted overwrite"))
        self.assertEqual(seen["status"], "already_preserved_identical")
        self.data["records"][0]["candidate_top10"].reverse()
        with self.assertRaisesRegex(ValueError, "immutable_ledger_collision"):
            publish(self.original(), self.root, "412345", "1",
                    self.remote_read, self.remote_create)

    def test_missing_remote_readback_rejected(self):
        with self.assertRaisesRegex(ValueError, "ledger_readback_mismatch"):
            publish(self.original(), self.root, "412345", "1",
                    lambda _: None, lambda *args: None)

    def test_no_frozen_predictions_not_preserved(self):
        self.data.update({"status": "no_confirmed_publication",
                          "published_forecasts": 0,
                          "frozen_before_t_minus_12": 0,
                          "ineligible_count": 0, "records": []})
        report = publish(self.original(), self.root, "412345", "1",
                         self.remote_read, self.remote_create)
        self.assertEqual(report["status"], "no_eligible_frozen_predictions")
        self.assertEqual(self.storage, {})

    def test_reject_double_counted_ineligible_error_before_preservation(self):
        self.data["published_forecasts"] = 2
        self.data["records"].append({
            "race_code": "202611040102", "status": "validation_error",
            "error_type": "ValueError"})
        self.data["validation_error_count"] = 1
        self.data["ineligible_count"] = 1  # Old bug: error counted twice.
        with self.assertRaisesRegex(ValueError, "ledger_record_partition_mismatch"):
            publish(self.original(), self.root, "412345", "1",
                    self.remote_read, self.remote_create)
        self.assertEqual(self.storage, {})

    def test_partial_error_is_preserved_with_disjoint_counts(self):
        self.data["published_forecasts"] = 2
        self.data["records"].append({
            "race_code": "202611040102", "status": "validation_error",
            "error_type": "ValueError"})
        self.data["validation_error_count"] = 1
        self.data["ineligible_count"] = 0
        result = publish(self.original(), self.root, "412345", "1",
                         self.remote_read, self.remote_create)
        self.assertTrue(result["stored"])

    def test_unknown_research_row_status_never_preserved(self):
        self.data["records"][0]["status"] = "unknown"
        with self.assertRaisesRegex(ValueError, "invalid_research_row_status"):
            publish(self.original(), self.root, "412345", "1",
                    self.remote_read, self.remote_create)
        self.assertEqual(self.storage, {})

    def test_reject_tampered_original_frozen_forecast(self):
        self.data["records"][0]["source_forecast_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "frozen_source_digest_mismatch"):
            prepare(self.original(), self.root, "412345", "1")

    def test_valid_digest_cannot_preserve_wrong_baseline_order(self):
        # The original archive is unchanged and its SHA matches the shadow.
        # Previously, a different but well-formed baseline could be saved
        # and only rejected by next-day read-only scoring.
        row = self.data["records"][0]
        row["baseline_top10"] = list(reversed(row["baseline_top10"]))
        with self.assertRaisesRegex(
                ValueError, "frozen_baseline_disagrees_with_original"):
            prepare(self.original(), self.root, "412345", "1")
        self.assertEqual(self.storage, {})

    def test_wrong_model_version_cannot_be_preserved(self):
        path = self.root / "four_mode_forecasts" / (CODE + ".json")
        archive = json.loads(path.read_text(encoding="utf-8"))
        archive["model_version"] = "OTHER_RESEARCH_MODEL"
        path.write_text(json.dumps(archive) + "\n", encoding="utf-8")
        self.data["records"][0]["source_forecast_sha256"] = hashlib.sha256(
            path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(
                ValueError, "frozen_baseline_disagrees_with_original"):
            prepare(self.original(), self.root, "412345", "1")
        self.assertEqual(self.storage, {})

    def test_forged_late_twelve_minute_cutoff_not_preserved(self):
        self.data["records"][0]["frozen_at_utc"] = "2026-11-04T02:00:00+00:00"
        self.data["records"][0]["t_minus_12_jst"] = "2026-11-04T13:48:00+09:00"
        with self.assertRaisesRegex(ValueError, "frozen_cutoff_disagrees_with_original"):
            prepare(self.original(), self.root, "412345", "1")
        self.assertEqual(self.storage, {})

    def test_reject_late_or_development_period_prediction(self):
        self.data["records"][0]["frozen_at_utc"] = "2026-11-04T02:48:00+00:00"
        with self.assertRaisesRegex(ValueError, "late_or_inconsistent"):
            prepare(self.original(), self.root, "412345", "1")
        self.data["records"][0]["frozen_at_utc"] = "2026-11-04T01:00:00+00:00"
        self.data["records"][0]["race_code"] = "202611030101"
        with self.assertRaisesRegex(ValueError, "development_or_wrong_protocol"):
            prepare(self.original(), self.root, "412345", "1")

    def test_duplicate_race_and_wrong_publication_sha_rejected(self):
        self.data["records"].append(dict(self.data["records"][0]))
        self.data["published_forecasts"] = 2
        self.data["frozen_before_t_minus_12"] = 2
        with self.assertRaisesRegex(ValueError, "duplicate_or_invalid_race"):
            prepare(self.original(), self.root, "412345", "1")
        self.data["records"] = [self.data["records"][0]]
        self.data["published_forecasts"] = 1
        self.data["frozen_before_t_minus_12"] = 1
        self.data["records"][0]["source_commit_sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "source_commit_mismatch"):
            prepare(self.original(), self.root, "412345", "1")

    def git_provenance(self, *args):
        if args[:2] == ("rev-parse", "HEAD"):
            return (SHA + "\n").encode()
        if args[:2] == ("merge-base", "--is-ancestor"):
            return b""
        if args[0] == "diff-tree":
            return ("four_mode_forecasts/" + CODE + ".json\n").encode()
        if args[0] == "show":
            return (self.root / "four_mode_forecasts" /
                    (CODE + ".json")).read_bytes()
        raise AssertionError(args)

    def test_source_commit_first_add_provenance_matches_original(self):
        self.assertEqual(
            verify_first_add_git_provenance(self.original(), self.root,
                                            self.git_provenance), 1)

    def test_source_commit_must_match_capture_checkout_head(self):
        def wrong(*args):
            if args[:2] == ("rev-parse", "HEAD"):
                return ("b" * 40 + "\n").encode()
            return self.git_provenance(*args)
        with self.assertRaisesRegex(ValueError, "ledger_publication_head_mismatch"):
            verify_first_add_git_provenance(self.original(), self.root, wrong)

    def test_source_must_be_first_added_not_just_present(self):
        def wrong(*args):
            if args[0] == "diff-tree":
                return b""
            return self.git_provenance(*args)
        with self.assertRaisesRegex(ValueError, "ledger_source_not_first_add_in_commit"):
            verify_first_add_git_provenance(self.original(), self.root, wrong)

    def test_first_add_git_blob_must_match_frozen_source_hash(self):
        def wrong(*args):
            if args[0] == "show":
                return b"modified history"
            return self.git_provenance(*args)
        with self.assertRaisesRegex(ValueError, "ledger_first_add_blob_mismatch"):
            verify_first_add_git_provenance(self.original(), self.root, wrong)

    def test_missing_remote_main_ancestry_is_fail_closed(self):
        import subprocess
        def wrong(*args):
            if args[0] == "merge-base":
                raise subprocess.CalledProcessError(1, list(args))
            return self.git_provenance(*args)
        with self.assertRaisesRegex(ValueError, "ledger_git_history_unavailable"):
            verify_first_add_git_provenance(self.original(), self.root, wrong)

    def test_first_run_write_probe_creates_exact_nonforecast_file(self):
        verdict = verify_ledger_write_access(self.remote_read, self.remote_create)
        self.assertEqual(verdict["status"], "new_write_permission_probe")
        self.assertFalse(verdict["forecast_record"])
        self.assertFalse(verdict["formal"])
        self.assertTrue(verdict["write_permission_tested_this_run"])
        self.assertEqual(self.storage[WRITE_PROBE_PATH], WRITE_PROBE_BYTES)
        self.assertNotIn(b"candidate_top10", WRITE_PROBE_BYTES)

    def test_write_probe_is_idempotent_and_does_not_overwrite(self):
        verify_ledger_write_access(self.remote_read, self.remote_create)
        verdict = verify_ledger_write_access(
            self.remote_read, lambda *a: self.fail("second write"))
        self.assertEqual(verdict["status"], "existing_write_probe_readback")
        self.assertFalse(verdict["write_permission_tested_this_run"])

    def test_write_probe_detects_conflicting_existing_content(self):
        self.storage[WRITE_PROBE_PATH] = b"tampered"
        with self.assertRaisesRegex(ValueError, "write_probe_collision"):
            verify_ledger_write_access(self.remote_read, self.remote_create)

    def test_write_probe_denied_write_does_not_claim_success(self):
        def deny(*args):
            raise ValueError("github_append_only_write_failed")
        with self.assertRaisesRegex(ValueError, "github_append_only_write_failed"):
            verify_ledger_write_access(self.remote_read, deny)
        self.assertNotIn(WRITE_PROBE_PATH, self.storage)

    def test_write_probe_requires_remote_readback(self):
        with self.assertRaisesRegex(ValueError, "write_probe_readback_mismatch"):
            verify_ledger_write_access(lambda _: None,
                                       lambda *args: None)

    def test_invalid_run_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_run_identity"):
            prepare(self.original(), self.root, "not-a-run", "1")
        with self.assertRaisesRegex(ValueError, "invalid_run_identity"):
            prepare(self.original(), self.root, "123", "0")


if __name__ == "__main__":
    unittest.main()
