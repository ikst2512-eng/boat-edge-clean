import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.audit_joint_official_receipts import audit_pair

RACE = "202611021910"
START = "2026-11-02T21:20:00+09:00"
RECEIVED = "2026-11-02T21:20:05+09:00"


class JointReceiptTests(unittest.TestCase):
    def make(self, root, *, complete=True, late=False):
        root = Path(root)
        first, second = root / "before", root / "odds"
        first.mkdir(); second.mkdir()
        rows = [{"teino": str(i), "extime": "6.75" if complete else "",
                 "tilt": "0.0"} for i in range(1, 7)]
        source = {"maindata": {"hd": "20261102", "jcd": "19", "rno": "10",
                  "deadline": "21:51", "teiinfolist": rows,
                  "sttenjiinfolist": [{"teino": str(i), "cs": str(i), "st": "F.01"} for i in range(1, 7)]}}
        odds = {f"{a}-{b}-{c}": 10.5 for a in range(1, 7) for b in range(1, 7) for c in range(1, 7) if len({a,b,c}) == 3}
        for folder, filename, raw, status, extra in [
            (first, "beforeinfo.json", json.dumps(source).encode(), "official_json_observed_not_t12_certified", {}),
            (second, "original.html", b"<html></html>", "official_odds_observed_research_only",
             {"deadline_at_jst": "2026-11-02T21:51:00+09:00"})]:
            (folder / filename).write_bytes(raw)
            manifest = {"race_code": RACE, "request_started_at_jst": START,
                        "received_at_jst": "2026-11-02T21:40:00+09:00" if late else RECEIVED,
                        "status": status, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), **extra}
            if late: manifest["request_started_at_jst"] = "2026-11-02T21:39:50+09:00"
            (folder / "manifest.json").write_text(json.dumps(manifest))
        return first, second

    def test_partial_is_not_complete(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = self.make(root, complete=False)
            report = audit_pair(a, b)
            self.assertFalse(report["both_complete_before_t12"])
            self.assertFalse(report["forecast_usable"])

    def test_tampered_odds_original_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = self.make(root)
            (b / "original.html").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                audit_pair(a, b)

    def test_deadline_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = self.make(root)
            m = json.loads((b / "manifest.json").read_text())
            m["deadline_at_jst"] = "2026-11-02T21:52:00+09:00"
            (b / "manifest.json").write_text(json.dumps(m))
            with self.assertRaises(ValueError):
                audit_pair(a, b)
