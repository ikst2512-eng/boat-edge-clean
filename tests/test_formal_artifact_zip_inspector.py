"""Synthetic downloaded artifact tests. No model or results access."""
import hashlib
import io
import json
import unittest
import zipfile
from itertools import permutations
from formal_artifact_zip_inspector import inspect_downloaded_artifact
from formal_candidate_validator import InvalidCandidate


class DownloadedZipTests(unittest.TestCase):
    def sample(self):
        code = "202610280101"
        candidate = {"race_code": code, "deadline_at": "2026-10-28T09:15:00+09:00",
                     "generated_at": "2026-10-28T09:00:00+09:00",
                     "source_snapshot_sha256": "a" * 64,
                     "probabilities": {"-".join(t): 1/120 for t in permutations("123456", 3)}}
        raw = json.dumps(candidate).encode()
        digest = hashlib.sha256(raw).hexdigest()
        receipt = json.dumps({"candidate_sha256": digest, "race_code": code,
                              "schema": "fresh-prospective-receipt-v1",
                              "status": "candidate_only_not_formal_or_public",
                              "independent_github_arrival_verified": False,
                              "workflow_run_id": 123, "workflow_attempt": 1,
                              "deadline_at": candidate["deadline_at"],
                              "source_snapshot_sha256": candidate["source_snapshot_sha256"],
                              "runner_recorded_at": "2026-10-28T09:02:00+09:00"}).encode()
        def make_zip(contents):
            mem = io.BytesIO()
            with zipfile.ZipFile(mem, "w") as z:
                for name, data in contents.items():
                    z.writestr(name, data)
            return mem.getvalue()
        members = {f"prospective_candidates/{code}.json": raw,
                   "prospective_receipt.json": receipt}
        return code, digest, members, make_zip

    def test_matching_bytes_do_not_approve(self):
        code, digest, members, make_zip = self.sample()
        result = inspect_downloaded_artifact(make_zip(members), code, digest)
        self.assertTrue(result["downloaded_bytes_consistent"])
        self.assertFalse(result["formal_approved"])
        self.assertEqual(result["workflow_run_id"], 123)
        self.assertEqual(result["workflow_attempt"], 1)

    def test_tampered_bytes(self):
        code, digest, members, make_zip = self.sample()
        members[f"prospective_candidates/{code}.json"] += b" "
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, digest)

    def test_extra_member(self):
        code, digest, members, make_zip = self.sample()
        members["extra.txt"] = b"bad"
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, digest)

    def test_symlink_member_rejected(self):
        code, digest, members, make_zip = self.sample()
        import stat
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w") as zipped:
            link = zipfile.ZipInfo(f"prospective_candidates/{code}.json")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            zipped.writestr(link, members[f"prospective_candidates/{code}.json"])
            zipped.writestr("prospective_receipt.json", members["prospective_receipt.json"])
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(mem.getvalue(), code, digest)

    def test_malformed_expected_digest(self):
        code, digest, members, make_zip = self.sample()
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, "g" * 64)

    def test_forged_approval_status(self):
        code, digest, members, make_zip = self.sample()
        receipt = json.loads(members["prospective_receipt.json"])
        receipt["status"] = "formal_approved"
        members["prospective_receipt.json"] = json.dumps(receipt).encode()
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, digest)

    def test_duplicate_receipt_key(self):
        code, digest, members, make_zip = self.sample()
        receipt = members["prospective_receipt.json"]
        members["prospective_receipt.json"] = receipt.replace(b'"race_code":', b'"race_code":"202610280201","race_code":', 1)
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, digest)

    def test_deadline_mismatch(self):
        code, digest, members, make_zip = self.sample()
        receipt = json.loads(members["prospective_receipt.json"])
        receipt["deadline_at"] = "2026-10-28T10:15:00+09:00"
        members["prospective_receipt.json"] = json.dumps(receipt).encode()
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, digest)

    def test_source_digest_mismatch(self):
        code, digest, members, make_zip = self.sample()
        receipt = json.loads(members["prospective_receipt.json"])
        receipt["source_snapshot_sha256"] = "b" * 64
        members["prospective_receipt.json"] = json.dumps(receipt).encode()
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, digest)

    def test_runner_time_before_generation(self):
        code, digest, members, make_zip = self.sample()
        receipt = json.loads(members["prospective_receipt.json"])
        receipt["runner_recorded_at"] = "2026-10-28T08:59:00+09:00"
        members["prospective_receipt.json"] = json.dumps(receipt).encode()
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, digest)

    def test_runner_receipt_inside_cutoff(self):
        code, digest, members, make_zip = self.sample()
        receipt = json.loads(members["prospective_receipt.json"])
        receipt["runner_recorded_at"] = "2026-10-28T09:04:00+09:00"
        members["prospective_receipt.json"] = json.dumps(receipt).encode()
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, digest)

    def test_source_digest_malformed(self):
        code, digest, members, make_zip = self.sample()
        candidate = json.loads(members[f"prospective_candidates/{code}.json"])
        candidate["source_snapshot_sha256"] = "g" * 64
        raw = json.dumps(candidate).encode()
        members[f"prospective_candidates/{code}.json"] = raw
        digest = hashlib.sha256(raw).hexdigest()
        receipt = json.loads(members["prospective_receipt.json"])
        receipt["candidate_sha256"] = digest
        receipt["source_snapshot_sha256"] = "g" * 64
        members["prospective_receipt.json"] = json.dumps(receipt).encode()
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, digest)

    def test_wrong_receipt_digest(self):
        code, digest, members, make_zip = self.sample()
        members["prospective_receipt.json"] = json.dumps(
            {"candidate_sha256": "0"*64, "race_code": code}).encode()
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, digest)


if __name__ == "__main__":
    unittest.main()
