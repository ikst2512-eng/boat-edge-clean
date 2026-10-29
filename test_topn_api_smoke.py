"""Smoke-test real CLEAN top-N HTTP response on localhost."""
import json
import os
import subprocess
import sys
import time
import unittest
from urllib.request import urlopen
from urllib.error import HTTPError

PORT=18763
class TopNApiSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=subprocess.Popen([sys.executable,"server.py"],env={**os.environ,"PORT":str(PORT)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(30):
            try:
                with urlopen(f"http://127.0.0.1:{PORT}/healthz",timeout=1) as r:
                    if r.status==200:return
            except OSError:time.sleep(.2)
        raise RuntimeError("CLEAN server did not start")
    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        try:cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:cls.server.kill()
    def test_research_day_and_schema(self):
        with urlopen(f"http://127.0.0.1:{PORT}/api/prospective-topn?day=20261029",timeout=20) as r:
            self.assertEqual(r.status,200)
            data=json.load(r)
        self.assertEqual(data["schema"],"CLEAN_PROSPECTIVE_TOPN_COHORT_V1")
        counts=data["counts"]
        self.assertEqual(counts["archives"],sum(counts[k] for k in ("evaluated","awaiting_result","audit_rejected")))
        self.assertFalse(data["formal"])
        self.assertTrue(data["unverified_races_excluded"])
        print("TOPN_HTTP_SMOKE",json.dumps({"counts":counts,"hit_rate_pct":data["hit_rate_pct"]},sort_keys=True))
    def test_reject_bad_day(self):
        with self.assertRaises(HTTPError) as err:
            urlopen(f"http://127.0.0.1:{PORT}/api/prospective-topn?day=invalid",timeout=5)
        self.assertEqual(err.exception.code,422)
if __name__=="__main__":unittest.main()
