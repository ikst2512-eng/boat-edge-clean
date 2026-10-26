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
        candidate = {"race_code": code,
                     "probabilities": {"-".join(t): 1/120 for t in permutations("123456", 3)}}
        raw = json.dumps(candidate).encode()
        digest = hashlib.sha256(raw).hexdigest()
        receipt = json.dumps({"candidate_sha256": digest, "race_code": code}).encode()
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

    def test_wrong_receipt_digest(self):
        code, digest, members, make_zip = self.sample()
        members["prospective_receipt.json"] = json.dumps(
            {"candidate_sha256": "0"*64, "race_code": code}).encode()
        with self.assertRaises(InvalidCandidate):
            inspect_downloaded_artifact(make_zip(members), code, digest)


if __name__ == "__main__":
    unittest.main()
