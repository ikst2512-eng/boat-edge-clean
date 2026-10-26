import io
import unittest
from clean_live_source_probe import probe

class Response:
    status=200
    headers={"Content-Type":"text/plain"}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return b"fixture bytes"

class SourceProbeTests(unittest.TestCase):
    def test_reports_retrieval_without_claiming_verification(self):
        result=probe("20261027","12","1",opener=lambda req,timeout: Response())
        self.assertEqual(result["status"],"UNVERIFIED")
        self.assertEqual(len(result["sources"]),5)
        for entry in result["sources"].values():
            self.assertEqual(entry["status"],"retrieved_unverified")
            self.assertEqual(len(entry["sha256"]),64)
        self.assertEqual(result["race_key"],"20261027-12-01")

    def test_failed_network_stays_unavailable(self):
        def failure(req,timeout): raise TimeoutError()
        result=probe("20261027","12","1",opener=failure)
        self.assertTrue(all(x["status"]=="unavailable" for x in result["sources"].values()))

    def test_invalid_identity_blocks_probe(self):
        with self.assertRaises(ValueError):
            probe("20261027","25","1")
        with self.assertRaises(ValueError):
            probe("20261027","12","13")
        with self.assertRaises(ValueError):
            probe("20260230","12","1")

if __name__=="__main__":
    unittest.main()
