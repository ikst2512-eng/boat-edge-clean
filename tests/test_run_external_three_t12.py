import base64
import hashlib
import json
import tempfile
import unittest
from urllib.error import HTTPError
from pathlib import Path
from unittest.mock import Mock

from scripts.run_external_three_t12 import collected_files, publish_originals, run, archival_exit_code

RACE = "202611030104"
OBS = "externaltest1"

def report(status="research_components_incomplete"):
    return {"race_code": RACE, "status": status, "forecast_usable": False,
            "full_t12_source_certified": False}

class ExternalT12EvidenceTests(unittest.TestCase):
    def populate(self, root):
        for part, names in {
            "card": ("racelist.html", "manifest.json"),
            "before": ("beforeinfo.json", "manifest.json"),
            "odds": ("original.html", "manifest.json"),
        }.items():
            for name in names:
                path = Path(root) / "observations" / (part + OBS) / "20261103" / RACE / name
                path.parent.mkdir(parents=True, exist_ok=True)
                if name == "manifest.json":
                    original = ("original:" + part + ":" + names[0]).encode()
                    path.write_text(json.dumps({"race_code": RACE,
                        "sha256": hashlib.sha256(original).hexdigest(),
                        "bytes": len(original)}))
                else:
                    path.write_bytes(("original:" + part + ":" + name).encode())

    def test_seven_atomic_evidence_files_from_six_originals(self):
        with tempfile.TemporaryDirectory() as root:
            self.populate(root)
            files = collected_files(root, RACE, OBS, report())
            self.assertEqual(len(files), 7)
            self.assertTrue(all(k.startswith("external_three_t12/20261103/" + RACE + "/" + OBS)
                                for k in files))
            self.assertEqual(sum(k.endswith("manifest.json") for k in files), 3)

    def test_incomplete_original_pair_is_not_published_as_complete_fetch(self):
        with tempfile.TemporaryDirectory() as root:
            self.populate(root)
            path = Path(root) / "observations" / ("odds" + OBS) / "20261103" / RACE / "original.html"
            path.unlink()
            with self.assertRaisesRegex(ValueError, "all three original pairs"):
                collected_files(root, RACE, OBS, report())

    def test_no_forecast_certificate_allowed(self):
        with tempfile.TemporaryDirectory() as root:
            for field in ("forecast_usable", "full_t12_source_certified"):
                candidate = report()
                candidate[field] = True
                with self.assertRaisesRegex(ValueError, "fail-closed"):
                    collected_files(root, RACE, OBS, candidate)

    def test_tampered_original_is_refused_before_any_git_publication(self):
        with tempfile.TemporaryDirectory() as root:
            self.populate(root)
            path = Path(root) / "observations" / ("card" + OBS) / "20261103" / RACE / "racelist.html"
            path.write_bytes(b"tampered original")
            with self.assertRaisesRegex(ValueError, "bytes and manifest disagree"):
                collected_files(root, RACE, OBS, report())

    def test_other_development_branches_cannot_receive_originals(self):
        for forbidden in ("main", "production", "audit/test", "research-evidence"):
            with self.assertRaisesRegex(ValueError, "invalid dedicated evidence branch"):
                publish_originals("owner/repo", forbidden, "stub-token",
                    {"external_three_t12/x": b"research"}, api=Mock())

    def test_atomic_non_force_git_commit_and_exact_blob_sha(self):
        events = []
        ref_reads = [0]
        def api(repo, token, method, endpoint, data=None):
            events.append((method, endpoint, data))
            if method == "GET" and endpoint.startswith("git/ref/"):
                ref_reads[0] += 1
                return {"object": {"sha": "parent" if ref_reads[0] == 1 else "new-commit"}}
            if method == "GET" and endpoint.startswith("git/commits"):
                return {"tree": {"sha": "base-tree"}}
            if endpoint == "git/blobs":
                original = base64.b64decode(data["content"])
                return {"sha": hashlib.sha1(f"blob {len(original)}\0".encode() + original).hexdigest()}
            if endpoint == "git/trees":
                self.assertEqual(data["base_tree"], "base-tree")
                return {"sha": "new-tree"}
            if endpoint == "git/commits":
                self.assertEqual(data["parents"], ["parent"])
                self.assertEqual(data["tree"], "new-tree")
                return {"sha": "new-commit"}
            if method == "PATCH":
                self.assertEqual(data, {"sha": "new-commit", "force": False})
                return {"object": {"sha": "new-commit"}}
            raise AssertionError(endpoint)
        files = {"external_three_t12/20261103/" + RACE + "/obs/report.json": b"research"}
        sha = publish_originals("owner/repo", "research-t12-external-evidence",
                                "stub-token", files, api=api)
        self.assertEqual(sha, "new-commit")
        self.assertEqual(len([event for event in events if event[0] == "PATCH"]), 1)

    def test_nonforce_branch_conflict_rebases_and_preserves_other_receipts(self):
        calls = []
        refs = iter(["parent-A", "parent-B", "new-commit-from-parent-B"])
        def api(repo, token, method, endpoint, data=None):
            calls.append((method, endpoint, data))
            if method == "GET" and endpoint.startswith("git/ref/"):
                return {"object": {"sha": next(refs)}}
            if method == "GET" and endpoint.startswith("git/commits/"):
                return {"tree": {"sha": "tree-" + endpoint.split("/")[-1]}}
            if endpoint == "git/blobs":
                raw = base64.b64decode(data["content"])
                return {"sha": hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()}
            if endpoint == "git/trees":
                return {"sha": "new-tree-based-" + data["base_tree"]}
            if endpoint == "git/commits":
                return {"sha": "new-commit-from-" + data["parents"][0]}
            if method == "PATCH":
                self.assertFalse(data["force"])
                if data["sha"].endswith("parent-A"):
                    raise HTTPError("https://api.github.com", 422, "non fast forward", {}, None)
                return {"object": {"sha": data["sha"]}}
            raise AssertionError(endpoint)
        files = {"external_three_t12/20261103/" + RACE + "/obs/report.json": b"evidence"}
        result = publish_originals("owner/repo", "research-t12-external-evidence",
                                   "stub-token", files, api=api)
        self.assertEqual(result, "new-commit-from-parent-B")
        self.assertEqual(len([x for x in calls if x[1] == "git/blobs"]), 1)
        self.assertEqual(len([x for x in calls if x[1] == "git/trees"]), 2)
        self.assertEqual(len([x for x in calls if x[0] == "PATCH"]), 2)

    def test_reject_detached_saved_commit_after_ref_update(self):
        reads = [0]
        def api(repo, token, method, endpoint, data=None):
            if method == "GET" and endpoint.startswith("git/ref/"):
                reads[0] += 1
                return {"object": {"sha": "initial" if reads[0] == 1 else "unrelated-head"}}
            if method == "GET" and endpoint.startswith("git/commits/"):
                return {"tree": {"sha": "base"}}
            if endpoint == "git/blobs":
                data_bytes = base64.b64decode(data["content"])
                return {"sha": hashlib.sha1(f"blob {len(data_bytes)}\0".encode() + data_bytes).hexdigest()}
            if endpoint == "git/trees":
                return {"sha": "new-tree"}
            if endpoint == "git/commits":
                return {"sha": "new-commit"}
            if method == "PATCH":
                return {"object": {"sha": "new-commit"}}
            if method == "GET" and endpoint.startswith("compare/"):
                return {"status": "diverged",
                        "merge_base_commit": {"sha": "other-commit"}}
            raise AssertionError(endpoint)
        with self.assertRaisesRegex(ValueError, "not reachable"):
            publish_originals("owner/repo", "research-t12-external-evidence",
                "stub-token", {"external_three_t12/x": b"evidence"}, api=api)

    def test_accept_saved_commit_followed_by_another_valid_archive(self):
        reads = [0]
        def api(repo, token, method, endpoint, data=None):
            if method == "GET" and endpoint.startswith("git/ref/"):
                reads[0] += 1
                return {"object": {"sha": "initial" if reads[0] == 1 else "descendant-commit"}}
            if method == "GET" and endpoint.startswith("git/commits/"):
                return {"tree": {"sha": "base"}}
            if endpoint == "git/blobs":
                data_bytes = base64.b64decode(data["content"])
                return {"sha": hashlib.sha1(f"blob {len(data_bytes)}\0".encode() + data_bytes).hexdigest()}
            if endpoint == "git/trees":
                return {"sha": "new-tree"}
            if endpoint == "git/commits":
                return {"sha": "new-commit"}
            if method == "PATCH":
                return {"object": {"sha": "new-commit"}}
            if method == "GET" and endpoint.startswith("compare/"):
                self.assertEqual(endpoint, "compare/new-commit...descendant-commit")
                return {"status": "ahead",
                        "merge_base_commit": {"sha": "new-commit"}}
            raise AssertionError(endpoint)
        sha = publish_originals("owner/repo", "research-t12-external-evidence",
                "stub-token", {"external_three_t12/x": b"evidence"}, api=api)
        self.assertEqual(sha, "new-commit")

    def test_permission_denial_never_retried(self):
        requests = []
        def api(repo, token, method, endpoint, data=None):
            requests.append((method, endpoint))
            if method == "GET" and endpoint.startswith("git/ref/"):
                return {"object": {"sha": "parent"}}
            if method == "GET" and endpoint.startswith("git/commits"):
                return {"tree": {"sha": "base"}}
            if endpoint == "git/blobs":
                raw = base64.b64decode(data["content"])
                return {"sha": hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()}
            if endpoint == "git/trees":
                return {"sha": "tree"}
            if endpoint == "git/commits":
                return {"sha": "commit"}
            if method == "PATCH":
                raise HTTPError("https://api.github.com", 403, "forbidden", {}, None)
            raise AssertionError(endpoint)
        with self.assertRaises(HTTPError):
            publish_originals("owner/repo", "research-t12-external-evidence",
                "stub-token", {"external_three_t12/x": b"evidence"}, api=api)
        self.assertEqual(len([x for x in requests if x[0] == "PATCH"]), 1)

    def test_exhausted_nonforce_conflicts_fail_without_force(self):
        attempts = []
        def api(repo, token, method, endpoint, data=None):
            attempts.append((method, endpoint, data))
            if method == "GET" and endpoint.startswith("git/ref/"):
                return {"object": {"sha": "parent"}}
            if method == "GET" and endpoint.startswith("git/commits"):
                return {"tree": {"sha": "tree"}}
            if endpoint == "git/blobs":
                raw = base64.b64decode(data["content"])
                return {"sha": hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()}
            if endpoint == "git/trees":
                return {"sha": "tree"}
            if endpoint == "git/commits":
                return {"sha": "commit"}
            if method == "PATCH":
                self.assertIs(data["force"], False)
                raise HTTPError("https://api.github.com", 409, "conflict", {}, None)
            raise AssertionError(endpoint)
        with self.assertRaises(HTTPError):
            publish_originals("owner/repo", "research-t12-external-evidence",
                "stub-token", {"external_three_t12/x": b"evidence"}, api=api)
        self.assertEqual(len([x for x in attempts if x[0] == "PATCH"]), 3)

    def test_remote_reinspection_failure_prevents_success_result(self):
        with tempfile.TemporaryDirectory() as root:
            self.populate(root)
            publisher = Mock(return_value="fake-commit")
            verifier = Mock(side_effect=ValueError("remote originals disagreed"))
            with self.assertRaisesRegex(ValueError, "remote originals disagreed"):
                run(RACE, root, OBS, "owner/repo",
                    "research-t12-external-evidence", "token",
                    observer=lambda *a: report(), publisher=publisher,
                    verifier=verifier)
            publisher.assert_called_once()
            verifier.assert_called_once()

    def test_local_complete_claim_needs_explicit_audit_completion(self):
        with tempfile.TemporaryDirectory() as root:
            self.populate(root)
            local = report("research_components_complete_by_t12")
            remote = {
                "status": "independent_originals_reaudited",
                "declared_status": local["status"],
                "research_complete": False, "original_files_found": 6,
                "full_t12_source_certified": False, "forecast_usable": False,
            }
            with self.assertRaisesRegex(ValueError, "lacks source audit proof"):
                run(RACE, root, OBS, "owner/repo", "research-t12-external-evidence",
                    "token", observer=lambda *args: local,
                    publisher=lambda *args: "saved-commit",
                    verifier=lambda *args: remote)

    def test_remote_file_count_mismatch_blocks_success(self):
        with tempfile.TemporaryDirectory() as root:
            self.populate(root)
            remote = {
                "status": "independent_originals_reaudited",
                "declared_status": "research_components_incomplete",
                "research_complete": False, "original_files_found": 5,
                "full_t12_source_certified": False, "forecast_usable": False,
            }
            with self.assertRaisesRegex(ValueError, "does not agree"):
                run(RACE, root, OBS, "owner/repo", "research-t12-external-evidence",
                    "token", observer=lambda *args: report(),
                    publisher=lambda *args: "saved-commit",
                    verifier=lambda *args: remote)

    def test_remote_false_completeness_blocks_local_complete_claim(self):
        with tempfile.TemporaryDirectory() as root:
            self.populate(root)
            local = report("research_components_complete_by_t12")
            local["audit"] = {"all_research_components_observed_by_t12": True}
            remote = {
                "status": "independent_originals_reaudited",
                "declared_status": local["status"],
                "research_complete": False, "original_files_found": 6,
                "full_t12_source_certified": False, "forecast_usable": False,
            }
            with self.assertRaisesRegex(ValueError, "does not agree"):
                run(RACE, root, OBS, "owner/repo", "research-t12-external-evidence",
                    "token", observer=lambda *args: local,
                    publisher=lambda *args: "saved-commit",
                    verifier=lambda *args: remote)

    def test_remote_unready_status_blocks_complete_fetch_claim(self):
        with tempfile.TemporaryDirectory() as root:
            self.populate(root)
            remote = {
                "status": "observation_not_ready",
                "declared_status": "research_components_incomplete",
                "research_complete": False, "original_files_found": 6,
                "full_t12_source_certified": False, "forecast_usable": False,
            }
            with self.assertRaisesRegex(ValueError, "does not agree"):
                run(RACE, root, OBS, "owner/repo", "research-t12-external-evidence",
                    "token", observer=lambda *args: report(),
                    publisher=lambda *args: "saved-commit",
                    verifier=lambda *args: remote)

    def test_diagnostic_only_archive_exits_nonzero_even_if_git_write_succeeds(self):
        result = {
            "race_code": RACE, "status": "t12_preflight_expired",
            "remote_originals_reaudited": False, "archived_original_count": 0,
            "research_complete": False, "full_t12_source_certified": False,
            "forecast_usable": False,
        }
        self.assertEqual(archival_exit_code(result), 1)

    def test_valid_originals_archived_with_incomplete_exhibition_exits_zero(self):
        result = {
            "race_code": RACE, "status": "research_components_incomplete",
            "remote_originals_reaudited": True, "archived_original_count": 6,
            "research_complete": False, "full_t12_source_certified": False,
            "forecast_usable": False,
        }
        self.assertEqual(archival_exit_code(result), 0)

    def test_claimed_original_count_or_forecast_permission_never_passes(self):
        result = {
            "remote_originals_reaudited": True, "archived_original_count": 6,
            "full_t12_source_certified": False, "forecast_usable": False,
        }
        for broken in ({"archived_original_count": 5},
                       {"remote_originals_reaudited": False},
                       {"full_t12_source_certified": True},
                       {"forecast_usable": True}):
            self.assertEqual(archival_exit_code({**result, **broken}), 1)

    def test_main_branch_cannot_be_written(self):
        with self.assertRaisesRegex(ValueError, "invalid dedicated evidence branch"):
            publish_originals("owner/repo", "main", "stub-token",
                              {"external_three_t12/x": b"evidence"}, api=Mock())

    def test_runner_only_reports_success_after_publication(self):
        with tempfile.TemporaryDirectory() as root:
            self.populate(root)
            publisher = Mock(return_value="verified-commit")
            verifier = Mock(return_value={
                "status": "independent_originals_reaudited",
                "declared_status": "research_components_incomplete",
                "research_complete": False,
                "original_files_found": 6,
                "full_t12_source_certified": False,
                "forecast_usable": False,
            })
            outcome = run(RACE, root, OBS, "owner/repo", "research-t12-external-evidence",
                          "token", observer=lambda *a: report(), publisher=publisher,
                          verifier=verifier)
            self.assertEqual(outcome["archived_original_count"], 6)
            self.assertFalse(outcome["forecast_usable"])
            publisher.assert_called_once()
            publisher.reset_mock(side_effect=True)
            publisher.side_effect = OSError("GitHub refused evidence commit")
            with self.assertRaises(OSError):
                run(RACE, root, OBS, "owner/repo", "research-t12-external-evidence",
                    "token", observer=lambda *a: report(), publisher=publisher,
                    verifier=verifier)

if __name__ == "__main__":
    unittest.main()
