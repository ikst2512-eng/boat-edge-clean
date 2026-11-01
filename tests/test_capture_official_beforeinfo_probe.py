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
            self.assertEqual(saved["request_started_at_jst"],now.isoformat())
            self.assertEqual(saved["response_url"],saved["url"])
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
            "https://www.boatrace.jp/owsp/sp/race/beforeinfo?hd=20261101&jcd=07&rno=9",
            "https://www.boatrace.jp/owsp/sp/race/beforeinfo?hd=20261102&jcd=07&rno=8",
            "https://www.boatrace.jp/owsp/sp/race/beforeinfo?hd=20261101&jcd=07&rno=8&extra=1",
        )
        for target in urls:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as d:
                with patch("scripts.capture_official_beforeinfo_probe.urlopen",return_value=FakeResponse(target)):
                    report=capture("202611010708",d)
                self.assertEqual(report["status"],"official_probe_failed")
                self.assertFalse(list(Path(d).rglob("manifest.json")))
                self.assertFalse(report["forecast_usable"])

    def test_valid_redirect_host_is_recorded_as_actual_response(self):
        from unittest.mock import patch
        class Response:
            status=200
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def geturl(self): return "https://boatrace.jp/owsp/sp/race/beforeinfo?hd=20261101&jcd=07&rno=8"
            def read(self,size): return b"<html>valid response</html>"
        with tempfile.TemporaryDirectory() as d:
            with patch("scripts.capture_official_beforeinfo_probe.urlopen",return_value=Response()):
                result=capture("202611010708",d)
            self.assertEqual(result["status"],"raw_http_observed_not_t12_certified")
            self.assertEqual(result["response_url"],"https://boatrace.jp/owsp/sp/race/beforeinfo?hd=20261101&jcd=07&rno=8")
            self.assertNotEqual(result["response_url"],result["url"])
            self.assertEqual(json.loads((Path(d)/"20261101/202611010708/manifest.json").read_text())["response_url"],result["response_url"])
            self.assertFalse(result["t12_eligible"])

    def test_backward_clock_cannot_be_saved_as_observation(self):
        from datetime import timedelta
        t=datetime(2026,11,1,12,0,tzinfo=JST)
        ticks=iter((t,t-timedelta(seconds=2)))
        with tempfile.TemporaryDirectory() as d:
            result=capture("202611010708",d,fetch=lambda url:b"<html></html>",clock=lambda:next(ticks))
            self.assertEqual(result["status"],"official_probe_failed")
            self.assertFalse(result["observation_chronology_valid"])
            self.assertFalse(list(Path(d).rglob("manifest.json")))

    def test_http_200_non_html_is_not_saved_as_evidence(self):
        for body in (b'{"error":"not ready"}',b"temporarily unavailable",b""):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as root:
                result=capture("202611010708",root,fetch=lambda url:body)
                self.assertEqual(result["status"],"official_probe_failed")
                self.assertFalse(result["forecast_usable"])
                self.assertFalse(list(Path(root).rglob("manifest.json")))
        with tempfile.TemporaryDirectory() as root:
            result=capture("202611010708",root,fetch=lambda url:bytes.fromhex("efbbbf")+b"  <!DOCTYPE html><html></html>")
            self.assertEqual(result["status"],"raw_http_observed_not_t12_certified")

    def test_failure_fails_closed(self):
        def missing(url): raise TimeoutError("offline")
        with tempfile.TemporaryDirectory() as d:
            r=capture("202611010708",d,fetch=missing)
            self.assertEqual(r["status"],"official_probe_failed")
            self.assertIn("request_started_at_jst",r)
            self.assertIn("received_at_jst",r)
            self.assertTrue(r["observation_chronology_valid"])
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
