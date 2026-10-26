"""No-network tests for read-only GitHub artifact reader guardrails."""
import unittest
from formal_candidate_validator import InvalidCandidate
from formal_github_artifact_reader import audit, NoAuthCrossHostRedirect
from urllib.request import Request


class GitHubReaderTests(unittest.TestCase):
    def test_missing_token_fails(self):
        with self.assertRaises(InvalidCandidate):
            audit(123, 456, "202610280101", "a" * 64, "")

    def test_invalid_id_fails(self):
        with self.assertRaises(InvalidCandidate):
            audit(True, 456, "202610280101", "a" * 64, "fake")

    def test_bad_redirect_host_rejected(self):
        handler = NoAuthCrossHostRedirect()
        original = Request("https://api.github.com/example",
                           headers={"Authorization": "Bearer fake"})
        with self.assertRaises(InvalidCandidate):
            handler.redirect_request(original, None, 302, "Found", {},
                                     "https://not-github.invalid/collect")

    def test_redirect_drops_authorization(self):
        handler = NoAuthCrossHostRedirect()
        original = Request("https://api.github.com/example",
                           headers={"Authorization": "Bearer fake"})
        redirected = handler.redirect_request(
            original, None, 302, "Found", {},
            "https://objects.githubusercontent.com/signed")
        self.assertIsNone(redirected.get_header("Authorization"))


if __name__ == "__main__":
    unittest.main()
