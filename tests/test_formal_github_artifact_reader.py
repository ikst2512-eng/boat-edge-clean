"""No-network tests for read-only GitHub artifact reader guardrails."""
import unittest
import json
from unittest.mock import patch
from formal_candidate_validator import InvalidCandidate
from formal_github_artifact_reader import audit, NoAuthCrossHostRedirect, _strict_metadata_json
from urllib.request import Request


class GitHubReaderTests(unittest.TestCase):
    def test_duplicate_github_json_key_rejected(self):
        with self.assertRaises(InvalidCandidate):
            _strict_metadata_json(b'{"id":123,"id":456}')

    def test_nonfinite_github_json_rejected(self):
        with self.assertRaises(InvalidCandidate):
            _strict_metadata_json(b'{"id":NaN}')

    def test_missing_token_fails(self):
        with self.assertRaises(InvalidCandidate):
            audit(123, 456, "202610280101", "a" * 64, "")

    def test_invalid_id_fails(self):
        with self.assertRaises(InvalidCandidate):
            audit(True, 456, "202610280101", "a" * 64, "fake")

    def test_downloaded_receipt_cannot_cross_run(self):
        class Opener:
            def open(self, req, timeout):
                class Response:
                    def __init__(self, data):
                        self.data = data
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return False
                    def read(self, n):
                        return self.data
                url = req.full_url
                if url.endswith("/actions/runs/123"):
                    data = {"id": 123, "run_attempt": 1, "status": "completed",
                            "conclusion": "success", "event": "repository_dispatch",
                            "path": ".github/workflows/fresh-prospective-capture.yml@refs/heads/main",
                            "head_branch": "main",
                            "head_repository": {"full_name": "ikst2512-eng/boat-edge-clean"}}
                elif "/artifacts?per_page=100" in url:
                    data = {"total_count": 1, "artifacts": [{"id": 456,
                            "workflow_run": {"id": 123}, "name": "prospective-v5-123",
                            "expired": False, "size_in_bytes": 200,
                            "created_at": "2026-10-28T09:02:00+09:00"}]}
                else:
                    return Response(b"fake zip")
                return Response(json.dumps(data).encode())
        mismatched = {"downloaded_bytes_consistent": True,
                      "workflow_run_id": 999, "workflow_attempt": 1,
                      "generated_at": "2026-10-28T09:00:00+09:00",
                      "deadline_at": "2026-10-28T09:15:00+09:00"}
        with patch("formal_github_artifact_reader.inspect_downloaded_artifact",
                   return_value=mismatched):
            with self.assertRaises(InvalidCandidate):
                audit(123, 456, "202610280101", "a" * 64, "fake", opener=Opener())

    def test_malformed_run_response_fails_closed(self):
        class BadOpener:
            def open(self, req, timeout):
                class Response:
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return False
                    def read(self, n):
                        return b"not-json"
                return Response()
        with self.assertRaises(InvalidCandidate):
            audit(123, 456, "202610280101", "a" * 64, "fake", opener=BadOpener())

    def test_connected_audit_synthetic_success_stays_unapproved(self):
        class Opener:
            def open(self, req, timeout):
                class Response:
                    def __init__(self, data):
                        self.data = data
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return False
                    def read(self, n):
                        return self.data
                url = req.full_url
                if url.endswith("/actions/runs/123"):
                    data = {"id": 123, "run_attempt": 1, "status": "completed",
                            "conclusion": "success", "event": "repository_dispatch",
                            "path": ".github/workflows/fresh-prospective-capture.yml",
                            "head_branch": "main",
                            "head_repository": {"full_name": "ikst2512-eng/boat-edge-clean"}}
                elif "/artifacts?per_page=100" in url:
                    data = {"total_count": 1, "artifacts": [{"id": 456,
                            "workflow_run": {"id": 123}, "name": "prospective-v5-123",
                            "expired": False, "size_in_bytes": 200,
                            "created_at": "2026-10-28T09:02:00+09:00"}]}
                else:
                    return Response(b"fake zip")
                return Response(json.dumps(data).encode())
        inspected = {"downloaded_bytes_consistent": True,
                     "workflow_run_id": 123, "workflow_attempt": 1,
                     "generated_at": "2026-10-28T09:00:00+09:00",
                     "deadline_at": "2026-10-28T09:15:00+09:00"}
        with patch("formal_github_artifact_reader.inspect_downloaded_artifact",
                   return_value=inspected):
            result = audit(123, 456, "202610280101", "a" * 64, "fake", opener=Opener())
        self.assertTrue(result["receipt_run_binding_verified"])
        self.assertFalse(result["formal_approved"])
        self.assertFalse(result["independent_upload_time_verified"])

    def test_wrong_capture_workflow_rejected(self):
        class WrongWorkflowOpener:
            def open(self, req, timeout):
                class Response:
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return False
                    def read(self, n):
                        return json.dumps({"id": 123, "run_attempt": 1,
                                           "path": ".github/workflows/other.yml",
                                           "head_repository": {"full_name": "ikst2512-eng/boat-edge-clean"}}).encode()
                return Response()
        with self.assertRaises(InvalidCandidate):
            audit(123, 456, "202610280101", "a" * 64, "fake", opener=WrongWorkflowOpener())

    def test_wrong_capture_branch_rejected(self):
        class WrongBranchOpener:
            def open(self, req, timeout):
                class Response:
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return False
                    def read(self, n):
                        return json.dumps({"id": 123, "run_attempt": 1,
                            "path": ".github/workflows/fresh-prospective-capture.yml",
                            "head_branch": "untrusted-research",
                            "head_repository": {"full_name": "ikst2512-eng/boat-edge-clean"}}).encode()
                return Response()
        with self.assertRaises(InvalidCandidate):
            audit(123, 456, "202610280101", "a" * 64, "fake", opener=WrongBranchOpener())

    def test_other_branch_suffix_cannot_spoof_main(self):
        class SpoofedOpener:
            def open(self, req, timeout):
                class Response:
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return False
                    def read(self, n):
                        return json.dumps({
                            "id": 123,
                            "path": ".github/workflows/fresh-prospective-capture.yml@refs/heads/untrusted",
                            "head_branch": "main",
                            "head_repository": {"full_name": "ikst2512-eng/boat-edge-clean"},
                        }).encode()
                return Response()
        with self.assertRaises(InvalidCandidate):
            audit(123, 456, "202610280101", "a" * 64, "fake", opener=SpoofedOpener())

    def test_invalid_digest_fails_before_network(self):
        with self.assertRaises(InvalidCandidate):
            audit(123, 456, "202610280101", "g" * 64, "fake")

    def test_real_zip_parsing_with_mocked_github_metadata(self):
        import io
        import zipfile
        import hashlib
        from itertools import permutations
        code = "202610280101"
        candidate = {"race_code": code,
                     "generated_at": "2026-10-28T09:00:00+09:00",
                     "deadline_at": "2026-10-28T09:15:00+09:00",
                     "source_snapshot_sha256": "a" * 64,
                     "probabilities": {"-".join(t): 1/120 for t in permutations("123456", 3)}}
        raw = json.dumps(candidate).encode()
        digest = hashlib.sha256(raw).hexdigest()
        receipt = {"candidate_sha256": digest, "race_code": code,
                   "schema": "fresh-prospective-receipt-v1",
                   "status": "candidate_only_not_formal_or_public",
                   "independent_github_arrival_verified": False,
                   "workflow_run_id": 123, "workflow_attempt": 1,
                   "deadline_at": candidate["deadline_at"],
                   "source_snapshot_sha256": candidate["source_snapshot_sha256"],
                   "runner_recorded_at": "2026-10-28T09:02:00+09:00"}
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zipped:
            zipped.writestr(f"prospective_candidates/{code}.json", raw)
            zipped.writestr("prospective_receipt.json", json.dumps(receipt).encode())
        archive = buf.getvalue()

        class FakeOpener:
            def open(self, req, timeout):
                class Response:
                    def __init__(self, data):
                        self.data = data
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return False
                    def read(self, n):
                        return self.data
                url = req.full_url
                if url.endswith("/actions/runs/123"):
                    return Response(json.dumps({
                        "id": 123, "run_attempt": 1, "status": "completed",
                        "conclusion": "success", "event": "repository_dispatch",
                        "head_branch": "main",
                        "path": ".github/workflows/fresh-prospective-capture.yml",
                        "head_repository": {"full_name": "ikst2512-eng/boat-edge-clean"},
                    }).encode())
                if "/artifacts?per_page=100" in url:
                    return Response(json.dumps({
                        "total_count": 1,
                        "artifacts": [{
                            "id": 456, "workflow_run": {"id": 123},
                            "name": "prospective-v5-123", "expired": False,
                            "size_in_bytes": len(archive),
                            "created_at": "2026-10-28T09:02:00+09:00",
                        }],
                    }).encode())
                return Response(archive)
        result = audit(123, 456, code, digest, "fake", opener=FakeOpener())
        self.assertTrue(result["artifact_zip_consistent"])
        self.assertTrue(result["receipt_run_binding_verified"])
        self.assertFalse(result["independent_upload_time_verified"])
        self.assertFalse(result["formal_approved"])

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
