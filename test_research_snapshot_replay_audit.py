import json
import tempfile
import unittest
from pathlib import Path
from research_model import probabilities
from research_snapshot_replay_audit import audit_directory, audit_snapshot

class SnapshotReplayAuditTests(unittest.TestCase):
    def fixture(self):
        rates=[6.0]*6
        return {"race_code":"202610271201","status":"research","validated":False,
                "model_version":"national-beta0.4-exploratory-v1",
                "national_win_rates":rates,
                "predictions":["-".join(map(str,t)) for t,p in probabilities(rates)[:10]]}

    def test_replay_matches(self):
        r=audit_snapshot(self.fixture())
        self.assertTrue(r["replay_matches"])
        self.assertFalse(r["prospective_verified"])

    def test_replay_detects_modified_rank(self):
        row=self.fixture()
        row["predictions"][0],row["predictions"][1]=row["predictions"][1],row["predictions"][0]
        self.assertFalse(audit_snapshot(row)["replay_matches"])

    def test_unknown_version_not_replayed(self):
        row=self.fixture()
        row["model_version"]="unknown"
        self.assertFalse(audit_snapshot(row)["version_supported"])
        self.assertIsNone(audit_snapshot(row)["replay_matches"])

    def test_directory_summary(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"202610271201.json").write_text(json.dumps(self.fixture()),encoding="utf-8")
            result=audit_directory(d)
            self.assertEqual(result["replay_matches"],1)
            self.assertEqual(result["prospective_verified"],0)

    def test_filename_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"202610271202.json").write_text(json.dumps(self.fixture()),encoding="utf-8")
            self.assertEqual(audit_directory(d)["invalid"],1)

if __name__=="__main__":
    unittest.main()
