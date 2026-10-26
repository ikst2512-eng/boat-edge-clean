"""Synthetic GitHub artifact audit tests; no network or result access."""
import unittest
from formal_candidate_validator import InvalidCandidate
from formal_actions_artifact_audit import inspect_actions_artifact


class ArtifactAuditTests(unittest.TestCase):
    def fixture(self):
        c = {"deadline_at": "2026-10-28T09:15:00+09:00",
             "generated_at": "2026-10-28T09:00:00+09:00"}
        r = {"workflow_run_id": 123, "workflow_attempt": 1}
        run = {"id": 123, "run_attempt": 1, "status": "completed",
               "conclusion": "success", "event": "repository_dispatch"}
        artifact = {"workflow_run": {"id": 123}, "name": "prospective-v5-123",
                    "expired": False, "size_in_bytes": 300,
                    "created_at": "2026-10-28T09:02:00+09:00"}
        return c, r, run, artifact

    def test_metadata_never_approves(self):
        result = inspect_actions_artifact(*self.fixture())
        self.assertTrue(result["github_artifact_metadata_consistent"])
        self.assertFalse(result["downloaded_bytes_verified"])
        self.assertFalse(result["formal_approved"])

    def test_late_artifact(self):
        c, r, run, art = self.fixture()
        art["created_at"] = "2026-10-28T09:04:00+09:00"
        with self.assertRaises(InvalidCandidate):
            inspect_actions_artifact(c, r, run, art)

    def test_wrong_run(self):
        c, r, run, art = self.fixture()
        art["workflow_run"]["id"] = 999
        with self.assertRaises(InvalidCandidate):
            inspect_actions_artifact(c, r, run, art)

    def test_missing_workflow_association(self):
        c, r, run, art = self.fixture()
        art["workflow_run"] = None
        with self.assertRaises(InvalidCandidate):
            inspect_actions_artifact(c, r, run, art)

    def test_invalid_workflow_association_type(self):
        c, r, run, art = self.fixture()
        art["workflow_run"]["id"] = True
        with self.assertRaises(InvalidCandidate):
            inspect_actions_artifact(c, r, run, art)

    def test_invalid_run_identity_type(self):
        c, r, run, art = self.fixture()
        run["id"] = True
        with self.assertRaises(InvalidCandidate):
            inspect_actions_artifact(c, r, run, art)

    def test_expired_artifact(self):
        c, r, run, art = self.fixture()
        art["expired"] = True
        with self.assertRaises(InvalidCandidate):
            inspect_actions_artifact(c, r, run, art)

    def test_failed_run(self):
        c, r, run, art = self.fixture()
        run["conclusion"] = "failure"
        with self.assertRaises(InvalidCandidate):
            inspect_actions_artifact(c, r, run, art)


if __name__ == "__main__":
    unittest.main()
