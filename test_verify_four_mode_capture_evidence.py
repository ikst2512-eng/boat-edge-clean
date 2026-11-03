"""Regression checks for publication-dependent evidence gate."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.verify_four_mode_capture_evidence import verify


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
            "records":[{"race_code":"202611040101"}],"unverified_count":0,
            "observed_before_t_minus_12":1})
        self.write("github-server-observation-ledger.json", {
            "stored":True,"formal":False,"status":"new_append_only_observation"})
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
