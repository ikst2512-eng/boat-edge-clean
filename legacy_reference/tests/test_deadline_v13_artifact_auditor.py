import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts/deadline_v9/audit_v13_artifact.py"
spec = importlib.util.spec_from_file_location("v13_auditor", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class V13ArtifactAuditorTest(unittest.TestCase):
    def check(self, files, run_id="123", git_sha="a" * 40):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "evidence.zip"
            with zipfile.ZipFile(path, "w") as archive:
                for name, obj in files.items():
                    archive.writestr(name, json.dumps(obj) if not isinstance(obj, bytes) else obj)
            return module.audit(path, run_id, git_sha)

    def fixture(self):
        import hashlib
        raw = b"<html>research evidence</html>"
        sha = hashlib.sha256(raw).hexdigest()
        return {
            "report.json": {"date_jst": "20261026", "captures": [{
                "venue_code": "01", "race_number_requested": 1,
                "sha256": sha, "bytes": len(raw)}], "errors": [],
                "formal_eligible": False, "results_seen": False},
            "integrity.json": {"status": "CAPTURE_INTEGRITY_PASS_RESEARCH_ONLY",
                               "verified_count": 1, "formal_eligible": False},
            "page_classification.json": {"schema": "V13_RESEARCH_ONLY",
                "capture_integrity": "CAPTURE_INTEGRITY_PASS_RESEARCH_ONLY",
                "classifications": [{"venue_code": "01", "race_number": 1,
                                     "status": "NO_RACE_DATA", "formal_eligible": False}],
                "counts": {"NO_RACE_DATA": 1}, "formal_eligible": False,
                "results_seen": False, "scoring": "NOT_RUN", "unlock": "LOCKED"},
            "run_provenance.json": {"schema": "V13_RESEARCH_RUN_PROVENANCE",
                "run_id": "123", "git_sha": "a" * 40, "formal_eligible": False,
                "results_seen": False, "scoring": "NOT_RUN", "unlock": "LOCKED"},
            f"snapshots/20261026/01/{sha}.html": raw,
        }

    def test_valid_research_only(self):
        self.assertEqual(self.check(self.fixture())["verdict"], "PASS_RESEARCH_ONLY")

    def test_missing_independent_run_identity_fails_closed(self):
        result = self.check(self.fixture(), run_id=None, git_sha=None)
        self.assertEqual(result["verdict"], "NOT_CERTIFIED")
        self.assertIn("MISSING_EXPECTED_RUN_ID", result["issues"])
        self.assertIn("MISSING_EXPECTED_GIT_SHA", result["issues"])

    def test_mismatched_independent_sha_fails_closed(self):
        result = self.check(self.fixture(), git_sha="b" * 40)
        self.assertIn("GIT_SHA_MISMATCH", result["issues"])

    def test_missing_provenance_fails_closed(self):
        data = self.fixture()
        del data["run_provenance.json"]
        self.assertEqual(self.check(data)["verdict"], "NOT_CERTIFIED")

    def test_changed_race_key_fails_even_if_count_unchanged(self):
        data = self.fixture()
        data["page_classification.json"]["classifications"][0]["race_number"] = 2
        self.assertIn("CLASSIFICATION_KEYS_MISMATCH", self.check(data)["issues"])

    def test_malformed_capture_is_not_certified(self):
        data = self.fixture()
        data["report.json"]["captures"][0] = None
        self.assertIn("INVALID_CAPTURE_RECORD", self.check(data)["issues"])

    def test_unhashable_status_is_not_certified(self):
        data = self.fixture()
        data["page_classification.json"]["classifications"][0]["status"] = []
        self.assertIn("INVALID_CLASSIFICATION_STATUS", self.check(data)["issues"])

    def test_duplicate_zip_member_fails_closed(self):
        import warnings
        files = self.fixture()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "duplicate.zip"
            with zipfile.ZipFile(path, "w") as archive:
                for name, obj in files.items():
                    archive.writestr(name, json.dumps(obj) if not isinstance(obj, bytes) else obj)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    archive.writestr("report.json", json.dumps(files["report.json"]))
            result = module.audit(path, "123", "a" * 40)
        self.assertIn("DUPLICATE_ZIP_MEMBER", result["issues"])

    def test_unhashable_race_key_fails_closed(self):
        files = self.fixture()
        files["report.json"]["captures"][0]["venue_code"] = []
        self.assertIn("INVALID_CAPTURE_RECORD", self.check(files)["issues"])

    def test_unsafe_unlock_fails(self):
        data = self.fixture()
        data["page_classification.json"]["unlock"] = "UNLOCKED"
        self.assertEqual(self.check(data)["verdict"], "NOT_CERTIFIED")


if __name__ == "__main__":
    unittest.main()
