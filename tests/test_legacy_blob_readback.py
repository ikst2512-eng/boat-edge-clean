import hashlib
import json
import unittest
from scripts.verify_legacy_blob_readback import verify_blob_readback


class LegacyBlobReadbackTests(unittest.TestCase):
    def payload(self):
        raw = json.dumps({"race_key": "20261027-01-01", "finish_order": [3, 4, 1]}).encode()
        row = {"race_code": "202610270101", "status": "FINISH_ORDER_MATCH",
               "legacy_git_blob_sha1": "a" * 40,
               "legacy_sha256": hashlib.sha256(raw).hexdigest(),
               "legacy_finish_order": [3, 4, 1]}
        return {"schema": "CLEAN_LEGACY_RESULT_COMPARISON_V1",
                "records": [row], "summary": {"FINISH_ORDER_MATCH": 1}}, raw

    def test_byte_readback(self):
        data, raw = self.payload()
        report = verify_blob_readback(data, lambda repo, sha: raw)
        self.assertEqual(report["verified_legacy_blobs"], 1)
        self.assertFalse(report["independent_backup_restored"])
        self.assertFalse(report["delete_authorized"])

    def test_tamper_is_rejected(self):
        data, raw = self.payload()
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify_blob_readback(data, lambda repo, sha: raw + b"changed")


if __name__ == "__main__":
    unittest.main()
