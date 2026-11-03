import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.run_external_three_t12 import collected_files, publish_originals, run

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
        def api(repo, token, method, endpoint, data=None):
            events.append((method, endpoint, data))
            if method == "GET" and endpoint.startswith("git/ref/"):
                return {"object": {"sha": "parent"}}
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

    def test_main_branch_cannot_be_written(self):
        with self.assertRaisesRegex(ValueError, "invalid dedicated evidence branch"):
            publish_originals("owner/repo", "main", "stub-token",
                              {"external_three_t12/x": b"evidence"}, api=Mock())

    def test_runner_only_reports_success_after_publication(self):
        with tempfile.TemporaryDirectory() as root:
            self.populate(root)
            publisher = Mock(return_value="verified-commit")
            outcome = run(RACE, root, OBS, "owner/repo", "research-t12-external-evidence",
                          "token", observer=lambda *a: report(), publisher=publisher)
            self.assertEqual(outcome["archived_original_count"], 6)
            self.assertFalse(outcome["forecast_usable"])
            publisher.assert_called_once()
            publisher.reset_mock(side_effect=True)
            publisher.side_effect = OSError("GitHub refused evidence commit")
            with self.assertRaises(OSError):
                run(RACE, root, OBS, "owner/repo", "research-t12-external-evidence",
                    "token", observer=lambda *a: report(), publisher=publisher)

if __name__ == "__main__":
    unittest.main()
