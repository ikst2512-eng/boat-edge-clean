"""Test auth/artifact metadata and honest scope of extracted original replay."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.audit_t12_extracted_artifact_replay import replay_extracted

RUN = 42450048245
ARTIFACT = 13604969020
DIGEST = "2bda1f350f18d7516ae685fd6a10094915fa00ae6cd8f3f3151b4bef651d2a5c"


def metadata(**overrides):
    data = {
        "id": ARTIFACT,
        "name": f"independent-late-preview-{RUN}",
        "expired": False,
        "digest": "sha256:" + DIGEST,
        "workflow_run": {"id": RUN},
        "size_in_bytes": 28283,
    }
    data.update(overrides)
    return data


def auditor(raw, run, repacked_sha):
    assert run == RUN
    assert hashlib.sha256(raw).hexdigest() == repacked_sha
    return {
        "run_id": run, "artifact_sha256": repacked_sha,
        "full_t12_source_certified": False, "formal": False,
        "official_racelist_originals_verified": 0,
    }


class ExtractedOriginalArtifactAuditTests(unittest.TestCase):
    def make_tree(self, root):
        dest = Path(root) / "official_joint_evidence" / "observations" / "example"
        dest.mkdir(parents=True)
        (dest / "beforeinfo.json").write_text('{"maindata":{}}', encoding="utf-8")
        (dest / "manifest.json").write_text('{"sha256":"example"}', encoding="utf-8")

    def test_valid_metadata_extracted_source_not_original_zip_hash(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_tree(root)
            report = replay_extracted(root, run_id=RUN, artifact_id=ARTIFACT,
                                      digest=DIGEST, metadata=metadata(),
                                      auditor=auditor)
            self.assertTrue(report["extracted_original_source_bytes_replayed"])
            self.assertTrue(report["github_artifact_digest_metadata_matches"])
            self.assertFalse(report["github_original_zip_digest_verified_by_local_hash"])
            self.assertEqual(report["original_actions_artifact_sha256"], DIGEST)
            self.assertNotEqual(report["repacked_zip_sha256_for_internal_replay"],
                                DIGEST)
            self.assertFalse(report["formal"])

    def test_mismatching_digest_or_metadata_cannot_be_success(self):
        for override in ({"digest": "sha256:" + "a"*64},
                         {"id": ARTIFACT + 1},
                         {"expired": True},
                         {"name": "unrelated"},
                         {"workflow_run": {"id": RUN+1}},
                         {"size_in_bytes": 0}):
            with self.subTest(override=override), tempfile.TemporaryDirectory() as root:
                self.make_tree(root)
                with self.assertRaises(ValueError):
                    replay_extracted(root, run_id=RUN, artifact_id=ARTIFACT,
                                     digest=DIGEST, metadata=metadata(**override),
                                     auditor=auditor)

    def test_missing_root_is_error_not_empty_capture(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                replay_extracted(Path(root) / "missing", run_id=RUN,
                                 artifact_id=ARTIFACT, digest=DIGEST,
                                 metadata=metadata(), auditor=auditor)

    def test_missing_files_is_error_not_green_noop(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                replay_extracted(root, run_id=RUN, artifact_id=ARTIFACT,
                                 digest=DIGEST, metadata=metadata(), auditor=auditor)

    def test_extracted_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_tree(root)
            (Path(root) / "link").symlink_to(Path(root) / "official_joint_evidence")
            with self.assertRaisesRegex(ValueError, "symlink"):
                replay_extracted(root, run_id=RUN, artifact_id=ARTIFACT,
                                 digest=DIGEST, metadata=metadata(), auditor=auditor)

    def test_nonfailclosed_replay_result_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_tree(root)
            with self.assertRaisesRegex(ValueError, "fail-closed"):
                replay_extracted(root, run_id=RUN, artifact_id=ARTIFACT,
                                 digest=DIGEST, metadata=metadata(),
                                 auditor=lambda raw, run, sha: {
                                     "run_id": run, "artifact_sha256": sha,
                                     "formal": True,
                                     "full_t12_source_certified": False,
                                 })

    def test_wrong_artifact_id_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_tree(root)
            with self.assertRaises(ValueError):
                replay_extracted(root, run_id=RUN, artifact_id=ARTIFACT-1,
                                 digest=DIGEST, metadata=metadata(), auditor=auditor)

    def test_bad_expected_sha_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_tree(root)
            with self.assertRaises(ValueError):
                replay_extracted(root, run_id=RUN, artifact_id=ARTIFACT,
                                 digest="not-a-sha", metadata=metadata(), auditor=auditor)

    def test_nested_originals_are_repacked_and_replayed(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_tree(root)
            state = {"checked": False}
            def check(raw, run, sha):
                state["checked"] = True
                return auditor(raw, run, sha)
            replay_extracted(root, run_id=RUN, artifact_id=ARTIFACT,
                             digest=DIGEST, metadata=metadata(), auditor=check)
            self.assertTrue(state["checked"])


if __name__ == "__main__":
    unittest.main()
