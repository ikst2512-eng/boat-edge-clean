"""Proof-of-retrievability tests: no self-reported clock/byte substitution."""
import base64
import json
import unittest
from forward_hole_rank3_protocol import PROTOCOL, _git_blob_sha1
from forward_protocol_github_observation import verify_remote_protocol, REMOTE_PATH

REPO = "ikst2512-eng/boat-edge-clean"
HEAD = "c" * 40
RAW = PROTOCOL.read_bytes()

def response(date="Wed, 04 Nov 2026 20:00:00 GMT", *, content=RAW,
             path=REMOTE_PATH, sha=None, age=None):
    return {
        "server_date": date, "cache_age": age,
        "body": json.dumps({
            "path": path, "type": "file", "encoding": "base64",
            "content": base64.b64encode(content).decode("ascii"),
            "sha": sha or _git_blob_sha1(RAW),
        }).encode("utf-8"),
    }


class GitHubProtocolObservationTests(unittest.TestCase):
    def check(self, data):
        return verify_remote_protocol(REPO, HEAD, request=lambda: data)

    def test_original_remote_bytes_observed_before_slot(self):
        result = self.check(response())
        self.assertEqual(result["status"], "research_protocol_on_github_before_study_cutoff")
        self.assertFalse(result["formal"])
        self.assertFalse(result["remote_forecasts_verified"])
        self.assertFalse(result["eligible_races_proven"])
        self.assertTrue(result["server_response_not_first_receipt_proof"])
        self.assertEqual(result["protocol_commit_sha"], HEAD)

    def test_cutoff_is_exclusive_and_utc(self):
        with self.assertRaisesRegex(ValueError, "protocol_remote_observation_after_cutoff"):
            self.check(response(date="Wed, 04 Nov 2026 22:00:00 GMT"))
        with self.assertRaisesRegex(ValueError, "protocol_remote_observation_after_cutoff"):
            self.check(response(date="Thu, 05 Nov 2026 01:00:00 GMT"))

    def test_wrong_remote_bytes_not_attested(self):
        with self.assertRaisesRegex(ValueError, "remote_protocol_bytes_mismatch"):
            self.check(response(content=RAW + b"\n"))

    def test_wrong_blob_identity_refused(self):
        with self.assertRaisesRegex(ValueError, "remote_protocol_json_or_base64_invalid"):
            self.check(response(sha="f" * 40))

    def test_cached_response_refused_even_if_early(self):
        with self.assertRaisesRegex(ValueError, "untrusted_or_cached"):
            self.check(response(age="10"))

    def test_wrong_remote_path_refused(self):
        with self.assertRaisesRegex(ValueError, "remote_protocol_json_or_base64_invalid"):
            self.check(response(path="research/forged.json"))

    def test_no_authentic_server_date_refused(self):
        with self.assertRaisesRegex(ValueError, "missing_github_server_date"):
            self.check(response(date=None))

    def test_non_gmt_clock_refused(self):
        with self.assertRaisesRegex(ValueError, "non_utc_github_server_date"):
            self.check(response(date="Thu, 05 Nov 2026 09:00:00 +0900"))

    def test_bad_commit_ref_refused(self):
        with self.assertRaisesRegex(ValueError, "invalid_repository_or_commit"):
            verify_remote_protocol(REPO, "main", request=lambda: response())


if __name__ == "__main__":
    unittest.main()
