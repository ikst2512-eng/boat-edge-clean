import tempfile
import json
import hashlib
import json
import unittest
from datetime import datetime
from pathlib import Path
from research_model import JST
from scripts.capture_official_beforeinfo_probe import capture

class OfficialProbeTests(unittest.TestCase):
    def test_http_receipt_is_not_t12_proof(self):
        with tempfile.TemporaryDirectory() as d:
            now=datetime(2026,11,1,12,0,tzinfo=JST)
            result=capture("202611010708",d,fetch=lambda url:b"<html>beforeinfo</html>",clock=lambda:now)
            self.assertEqual(result["status"],"raw_http_observed_not_t12_certified")
            self.assertFalse(result["t12_eligible"])
            self.assertFalse(result["forecast_usable"])
            self.assertEqual(result["complete_six_lanes"],"unverified")
            manifest_path=Path(d)/"20261101/202611010708/manifest.json"
            self.assertTrue(manifest_path.exists())
            saved=json.loads(manifest_path.read_text())
            raw=(manifest_path.parent/"beforeinfo.html").read_bytes()
            self.assertEqual(saved["sha256"],hashlib.sha256(raw).hexdigest())
            self.assertEqual(saved["received_at_jst"],now.isoformat())
            self.assertFalse(saved["forecast_usable"])
            manifest=(Path(d)/"20261101/202611010708/manifest.json").read_text(encoding="utf-8")
            self.assertTrue(manifest.endswith("\n"))
            self.assertEqual(json.loads(manifest),result)
            self.assertEqual((Path(d)/"20261101/202611010708/beforeinfo.html").read_bytes(),b"<html>beforeinfo</html>")
            self.assertEqual(capture("202611010708",d,fetch=lambda url:b"x",clock=lambda:now)["status"],"official_probe_failed")
    def test_failure_fails_closed(self):
        def missing(url): raise TimeoutError("offline")
        with tempfile.TemporaryDirectory() as d:
            r=capture("202611010708",d,fetch=missing)
            self.assertEqual(r["status"],"official_probe_failed")
            self.assertFalse(r["t12_eligible"])
            self.assertEqual(list(Path(d).rglob("*.html")),[])
    def test_partial_manifest_write_cleans_evidence_directory(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            original=Path.open
            def fail_manifest(path,*args,**kwargs):
                if str(path).endswith("manifest.json"):
                    raise OSError("disk failure")
                return original(path,*args,**kwargs)
            with patch.object(Path,"open",fail_manifest):
                result=capture("202611010708",d,fetch=lambda url:b"<html>ok</html>")
            self.assertEqual(result["status"],"official_probe_failed")
            self.assertFalse((Path(d)/"20261101/202611010708").exists())

    def test_rejects_bad_race_code(self):
        for code in ("202611010799","202611010000","2026110107AA","202611010708/../"):
            with self.assertRaises(ValueError):capture(code)

if __name__=="__main__":unittest.main()
