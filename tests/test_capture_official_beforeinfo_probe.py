import tempfile
import json
import hashlib
import subprocess
import sys
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
            self.assertTrue((manifest_path.parent/"beforeinfo.html").exists())
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
    def test_redirect_must_remain_on_official_https_beforeinfo(self):
        from unittest.mock import patch
        class FakeResponse:
            status=200
            def __init__(self,url): self.url=url
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def geturl(self): return self.url
            def read(self,size): return b"<html>raw</html>"
        urls=(
            "http://www.boatrace.jp/owsp/sp/race/beforeinfo?hd=20261101",
            "https://www.boatrace.jp/owsp/sp/race/result?hd=20261101",
            "https://other.example/owsp/sp/race/beforeinfo",
        )
        for target in urls:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as d:
                with patch("scripts.capture_official_beforeinfo_probe.urlopen",return_value=FakeResponse(target)):
                    report=capture("202611010708",d)
                self.assertEqual(report["status"],"official_probe_failed")
                self.assertFalse(list(Path(d).rglob("manifest.json")))
                self.assertFalse(report["forecast_usable"])

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

    def test_cli_reports_failed_observation_as_failed_job(self):
        with tempfile.TemporaryDirectory() as d:
            # Bad day is rejected by the CLI, never reported as an observed page.
            proc=subprocess.run([sys.executable,"-m","scripts.capture_official_beforeinfo_probe",
                                 "202611010799","--root",d],capture_output=True,text=True)
            self.assertNotEqual(proc.returncode,0)
            self.assertFalse(list(Path(d).rglob("manifest.json")))

    def test_cli_network_failure_exits_nonzero(self):
        import runpy
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            with patch("urllib.request.urlopen", side_effect=TimeoutError("offline")):
                with patch.object(sys, "argv", ["probe", "202611010708", "--root", d]):
                    with self.assertRaises(SystemExit) as exc:
                        runpy.run_module("scripts.capture_official_beforeinfo_probe", run_name="__main__")
            self.assertEqual(exc.exception.code, 1)
            self.assertFalse(list(Path(d).rglob("manifest.json")))

    def test_rejects_bad_race_code(self):
        for code in ("202611010799","202611010000","2026110107AA","202611010708/../"):
            with self.assertRaises(ValueError):capture(code)

if __name__=="__main__":unittest.main()
