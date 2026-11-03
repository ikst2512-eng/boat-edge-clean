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
        self.published(); self.good()
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
