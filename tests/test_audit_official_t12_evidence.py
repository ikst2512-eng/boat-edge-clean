import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.audit_official_t12_evidence import recheck

JST = timezone(timedelta(hours=9))
CUTOFF = "2026-11-02T19:54:00+09:00"
RACE = "202611021511"


class EvidenceRecheckTests(unittest.TestCase):
    def make_evidence(self, root, *, complete=True):
        folder = Path(root)
        racers = [{"teino": str(i), "extime": "6.80" if complete else "", "tilt": "-0.5"}
                  for i in range(1, 7)]
        rows = [{"teino": str(i), "cs": i, "st": "F.01"} for i in range(1, 7)]
        payload = {"maindata": {"hd": "20261102", "jcd": "15", "rno": "11",
                               "deadline": "20:06", "teiinfolist": racers, "sttenjiinfolist": rows}}
        raw = json.dumps(payload).encode()
        (folder / "beforeinfo.json").write_bytes(raw)
        manifest = {"race_code": RACE, "request_started_at_jst": "2026-11-02T19:51:34+09:00",
                    "received_at_jst": "2026-11-02T19:51:35+09:00",
                    "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        (folder / "manifest.json").write_text(json.dumps(manifest))
        return folder

    def test_complete_snapshot_is_evidence_not_formal_forecast(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_evidence(root)
            result = recheck(root, CUTOFF, RACE)
            self.assertTrue(result["complete_official_beforeinfo_observed_before_t12"])
            self.assertTrue(result["source_sha256_verified"])
            self.assertFalse(result["t12_eligible"])
            self.assertFalse(result["forecast_usable"])

    def test_partial_snapshot_does_not_pass(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_evidence(root, complete=False)
            self.assertFalse(recheck(root, CUTOFF, RACE)["complete_official_beforeinfo_observed_before_t12"])

    def test_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.make_evidence(root)
            (path / "beforeinfo.json").write_bytes(b"{}")
            with self.assertRaises(ValueError):
                recheck(root, CUTOFF, RACE)

    def test_cutoff_and_identity_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            self.make_evidence(root)
            with self.assertRaises(ValueError):
                recheck(root, "2026-11-02T19:53:00+09:00", RACE)
            with self.assertRaises(ValueError):
                recheck(root, CUTOFF, "202611021512")

    def test_late_receipt_is_not_pre_cutoff(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.make_evidence(root)
            m = json.loads((path / "manifest.json").read_text())
            m["received_at_jst"] = "2026-11-02T19:54:01+09:00"
            (path / "manifest.json").write_text(json.dumps(m))
            self.assertFalse(recheck(root, CUTOFF, RACE)["complete_official_beforeinfo_observed_before_t12"])


if __name__ == "__main__":
    unittest.main()
