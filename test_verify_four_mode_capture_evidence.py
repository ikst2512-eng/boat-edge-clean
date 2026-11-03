"""Regression checks for publication-dependent evidence gate."""
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from scripts.verify_four_mode_capture_evidence import verify, record_verdict


class EvidenceVerdictTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "four-mode-evidence").mkdir()
    def write(self, name, data):
        (self.root / "four-mode-evidence" / name).write_text(json.dumps(data), encoding="utf-8")
    def published(self):
        self.write("publication.json", {"outcome":"pushed_to_main", "added_forecasts":1, "commit_sha":"a"*40})
    def good(self):
        self.write("github-server-observation.json", {
            "status":"remote_observation_audited_nonformal",
            "publication_commit_sha":"a"*40,"publication_count":1,
            "records":[{"race_code":"202611040101",
                        "first_add_commit":"a"*40,
                        "status":"github_server_observed_before_t_minus_12",
                        "first_add_blob_matches_remote":True,
                        "github_api_server_date_utc":"2026-11-04T01:00:00+00:00",
                        "deadline_minus_12_jst":"2026-11-04T11:48:00+09:00"}],
            "unverified_count":0, "observed_after_t_minus_12":0,
            "observed_before_t_minus_12":1})
        source=(self.root/"four-mode-evidence"/"github-server-observation.json").read_bytes()
        self.write("github-server-observation-ledger.json", {
            "stored":True,"formal":False,"status":"new_append_only_observation",
            "sha256":hashlib.sha256(source).hexdigest(),
            "path":"github_server/20261104/run-1234-attempt-1.json"})
    def good_third(self):
        original = {
            "schema": "V2_THIRD_RATE_SAME_JOB_FROZEN_SHADOW_V1",
            "status": "captured_local_after_push_not_remote_proven",
            "formal": False,
            "publication_commit_sha": "a" * 40,
            "published_forecasts": 1,
            "frozen_before_t_minus_12": 1,
            "validation_error_count": 0,
            "records": [{
                "race_code": "202611040101",
                "status": "frozen_in_same_job_before_t_minus_12",
                "source_commit_sha": "a" * 40,
                "frozen_at_utc": "2026-11-04T01:00:00+00:00",
                "t_minus_12_jst": "2026-11-04T11:48:00+09:00",
            }],
        }
        self.write("third-rate-shadow.json", original)
        blob = (self.root / "four-mode-evidence" / "third-rate-shadow.json").read_bytes()
        self.write("third-rate-ledger.json", {
            "status": "new_immutable_ledger_entry",
            "stored": True, "formal": False,
            "branch": "v2-third-rate-evidence-ledger",
            "original_sha256": hashlib.sha256(blob).hexdigest(),
            "path": "third_rate/20261104/run-1234-attempt-1.json",
        })

    def test_future_publication_requires_durable_third_shadow(self):
        self.published(); self.good()
        with self.assertRaises(FileNotFoundError):
            verify(self.root)

    def test_future_rejects_third_shadow_without_long_term_bytes(self):
        self.published(); self.good(); self.good_third()
        (self.root / "four-mode-evidence" / "third-rate-ledger.json").unlink()
        with self.assertRaises(FileNotFoundError):
            verify(self.root)

    def test_future_rejects_third_shadow_with_wrong_digest(self):
        self.published(); self.good(); self.good_third()
        path = self.root / "four-mode-evidence" / "third-rate-ledger.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["original_sha256"] = "0" * 64
        self.write("third-rate-ledger.json", data)
        with self.assertRaisesRegex(ValueError, "future_third_rate_not_durable"):
            verify(self.root)

    def test_future_rejects_no_frozen_third_predictions(self):
        self.published(); self.good(); self.good_third()
        path = self.root / "four-mode-evidence" / "third-rate-shadow.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["frozen_before_t_minus_12"] = 0
        self.write("third-rate-shadow.json", data)
        with self.assertRaisesRegex(ValueError, "future_third_rate_shadow_missing_or_invalid"):
            verify(self.root)

    def test_two_published_but_one_third_rate_freeze_never_passes(self):
        self.published(); self.good(); self.good_third()
        evidence_dir = self.root / "four-mode-evidence"
        publication = json.loads((evidence_dir/"publication.json").read_text())
        publication["added_forecasts"] = 2
        self.write("publication.json", publication)
        observation = json.loads((evidence_dir/"github-server-observation.json").read_text())
        second = dict(observation["records"][0])
        second["race_code"] = "202611040102"
        observation["records"].append(second)
        observation["publication_count"] = 2
        observation["observed_before_t_minus_12"] = 2
        self.write("github-server-observation.json", observation)
        observed_bytes = (evidence_dir/"github-server-observation.json").read_bytes()
        first_ledger = json.loads((evidence_dir/"github-server-observation-ledger.json").read_text())
        first_ledger["sha256"] = hashlib.sha256(observed_bytes).hexdigest()
        self.write("github-server-observation-ledger.json", first_ledger)
        shadow = json.loads((evidence_dir/"third-rate-shadow.json").read_text())
        shadow["published_forecasts"] = 2
        shadow["records"].append({
            "race_code":"202611040102", "status":"ineligible",
            "reason":"calculation_crossed_t_minus_12"})
        shadow["ineligible_count"] = 1
        self.write("third-rate-shadow.json", shadow)
        shadow_bytes = (evidence_dir/"third-rate-shadow.json").read_bytes()
        second_ledger = json.loads((evidence_dir/"third-rate-ledger.json").read_text())
        second_ledger["original_sha256"] = hashlib.sha256(shadow_bytes).hexdigest()
        self.write("third-rate-ledger.json", second_ledger)
        with self.assertRaisesRegex(ValueError, "future_third_rate_partial_frozen_roster"):
            verify(self.root)
        self.assertEqual(record_verdict(self.root)["status"], "failed")

    def test_third_rate_cutoff_must_equal_remote_observed_same_race_cutoff(self):
        self.published(); self.good(); self.good_third()
        folder = self.root / "four-mode-evidence"
        # Shadow pretends the race deadline is an hour later than the
        # independently observed forecast's original race deadline.
        original = json.loads((folder/"third-rate-shadow.json").read_text())
        original["records"][0]["t_minus_12_jst"] = "2026-11-04T12:48:00+09:00"
        self.write("third-rate-shadow.json", original)
        ledger = json.loads((folder/"third-rate-ledger.json").read_text())
        ledger["original_sha256"] = hashlib.sha256(
            (folder/"third-rate-shadow.json").read_bytes()).hexdigest()
        self.write("third-rate-ledger.json", ledger)
        with self.assertRaisesRegex(ValueError,
                                    "future_third_rate_remote_cutoff_mismatch"):
            verify(self.root)
        self.assertEqual(record_verdict(self.root)["status"], "failed")

    def test_cross_run_receipt_substitution_is_not_same_job_proof(self):
        self.published(); self.good(); self.good_third()
        ledger = self.root / "four-mode-evidence" / "third-rate-ledger.json"
        data = json.loads(ledger.read_text(encoding="utf-8"))
        data["path"] = "third_rate/20261104/run-9999-attempt-1.json"
        self.write("third-rate-ledger.json", data)
        with self.assertRaisesRegex(ValueError,
                                    "future_evidence_ledger_run_identity_mismatch"):
            verify(self.root)
        self.assertEqual(record_verdict(self.root)["status"], "failed")

    def test_cross_attempt_receipt_substitution_is_not_same_job_proof(self):
        self.published(); self.good(); self.good_third()
        ledger = self.root / "four-mode-evidence" / "third-rate-ledger.json"
        data = json.loads(ledger.read_text(encoding="utf-8"))
        data["path"] = "third_rate/20261104/run-1234-attempt-2.json"
        self.write("third-rate-ledger.json", data)
        with self.assertRaisesRegex(ValueError,
                                    "future_evidence_ledger_run_identity_mismatch"):
            verify(self.root)

    def test_valid_future_shadow_and_ledger_are_required_for_publication_pass(self):
        self.published(); self.good(); self.good_third()
        self.assertEqual(verify(self.root)["status"],
                         "published_with_durable_early_observation")

    def test_hash_mismatch_does_not_claim_durable_same_evidence(self):
        self.published();self.good()
        path=self.root/"four-mode-evidence"/"github-server-observation-ledger.json"
        saved=json.loads(path.read_text())
        saved["sha256"]="0"*64
        path.write_text(json.dumps(saved))
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_forged_early_aggregate_with_unverified_row_is_rejected(self):
        self.published();self.good()
        self.write("github-server-observation.json", {
            "status":"remote_observation_audited_nonformal",
            "publication_commit_sha":"a"*40,"publication_count":1,
            "records":[{"race_code":"202611040101",
                        "first_add_commit":"a"*40,
                        "status":"remote_observation_unverified"}],
            "unverified_count":0,"observed_after_t_minus_12":0,
            "observed_before_t_minus_12":1})
        source=(self.root/"four-mode-evidence"/"github-server-observation.json").read_bytes()
        ledger=self.root/"four-mode-evidence"/"github-server-observation-ledger.json"
        saved=json.loads(ledger.read_text())
        saved["sha256"]=hashlib.sha256(source).hexdigest()
        ledger.write_text(json.dumps(saved))
        with self.assertRaisesRegex(ValueError,"invalid_observation_row"):
            verify(self.root)

    def test_late_timestamp_with_fake_early_label_is_rejected(self):
        self.published();self.good()
        observation=self.root/"four-mode-evidence"/"github-server-observation.json"
        data=json.loads(observation.read_text())
        data["records"][0]["github_api_server_date_utc"]="2026-11-04T03:00:00+00:00"
        observation.write_text(json.dumps(data))
        ledger=self.root/"four-mode-evidence"/"github-server-observation-ledger.json"
        saved=json.loads(ledger.read_text())
        saved["sha256"]=hashlib.sha256(observation.read_bytes()).hexdigest()
        ledger.write_text(json.dumps(saved))
        with self.assertRaisesRegex(ValueError,"observation_not_before_t_minus_12"):
            verify(self.root)

    def test_final_verdict_artifact_preserves_success_and_failure(self):
        self.write("publication.json", {"outcome": "no_eligible_candidates"})
        success = record_verdict(self.root)
        self.assertEqual(success["status"], "passed")
        self.assertFalse(success["detail"]["evidence_required"])
        self.assertEqual(json.loads((self.root / "four-mode-evidence" /
                                     "final-evidence-verdict.json").read_text()),
                         success)
        self.published()
        failure = record_verdict(self.root)
        self.assertEqual(failure["status"], "failed")
        self.assertEqual(failure["error_type"], "FileNotFoundError")
        self.assertEqual(json.loads((self.root / "four-mode-evidence" /
                                     "final-evidence-verdict.json").read_text()),
                         failure)

    def test_empty_capture_is_not_error(self):
        self.write("publication.json", {"outcome":"no_eligible_candidates"})
        self.assertFalse(verify(self.root)["evidence_required"])
    def test_published_valid_evidence_passes(self):
        self.published(); self.good(); self.good_third()
        self.assertEqual(verify(self.root)["published"], 1)
    def test_published_without_ledger_fails(self):
        self.published()
        with self.assertRaises(OSError):
            verify(self.root)
    def test_unverified_observation_fails(self):
        self.published(); self.good()
        self.write("github-server-observation.json", {
            "status":"remote_observation_audited_nonformal","publication_commit_sha":"a"*40,
            "publication_count":1,"records":[{}],"unverified_count":1,
            "observed_before_t_minus_12":0})
        with self.assertRaises(ValueError): verify(self.root)
    def test_late_observation_fails(self):
        self.published(); self.good()
        self.write("github-server-observation.json", {
            "status":"remote_observation_audited_nonformal","publication_commit_sha":"a"*40,
            "publication_count":1,"records":[{}],"unverified_count":0,
            "observed_before_t_minus_12":0})
        with self.assertRaises(ValueError): verify(self.root)
    def test_not_confirmed_fails(self):
        self.write("publication.json", {"outcome":"failed"})
        with self.assertRaises(ValueError): verify(self.root)


if __name__ == "__main__":
    unittest.main()
