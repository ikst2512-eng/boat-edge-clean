import unittest
from research_receipt_run_audit import run_audit

class ReceiptRunAuditTests(unittest.TestCase):
    def test_invalid_id_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid"):
            run_audit("bogus","a"*40)
    def test_invalid_sha_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid"):
            run_audit("123","unsafe")
    def test_rejects_push_without_new_pairs(self):
        import tempfile
        import json
        from pathlib import Path
        from unittest.mock import patch
        run={"id":123,"head_sha":"a"*40,"created_at":"2026-10-28T00:01:00Z",
             "event":"push","head_branch":"research/paired-hit-evaluation-20261027",
             "repository":{"full_name":"ikst2512-eng/boat-edge-clean"}}
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return None
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"202610281201.json"
            path.write_text(json.dumps({"race_code":"202610281201"}),encoding="utf-8")
            with patch("research_receipt_run_audit.urlopen",return_value=Response()),patch(
                "research_receipt_run_audit.json.load",return_value=run),patch(
                "subprocess.check_output",return_value=b""):
                with self.assertRaisesRegex(ValueError,"did not introduce"):
                    run_audit("123","a"*40,d)

    def test_uncertified_pair_fails_entire_receipt(self):
        import json, tempfile
        from pathlib import Path
        from unittest.mock import patch
        run={"id":123,"head_sha":"a"*40,"created_at":"2026-10-28T00:30:00Z",
             "event":"push","head_branch":"research/paired-hit-evaluation-20261027",
             "repository":{"full_name":"ikst2512-eng/boat-edge-clean"}}
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return None
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)/"research_prospective_pairs"
            folder.mkdir()
            file=folder/"202610281201.json"
            raw=json.dumps({"race_code":"202610281201",
                "frozen_at_jst":"2026-10-28T09:00:00+09:00",
                "cutoff_jst":"2026-10-28T09:20:00+09:00"}).encode()
            file.write_bytes(raw)
            import os
            cwd=os.getcwd()
            try:
                os.chdir(root)
                with patch("research_receipt_run_audit.urlopen",return_value=Response()),patch(
                    "research_receipt_run_audit.json.load",return_value=run),patch(
                    "subprocess.check_output",side_effect=[
                        "research_prospective_pairs/202610281201.json"+chr(10),raw]):
                    with self.assertRaisesRegex(ValueError,"lack pre-cutoff"):
                        run_audit("123","a"*40,"research_prospective_pairs")
            finally:
                os.chdir(cwd)

if __name__=="__main__":
    unittest.main()
