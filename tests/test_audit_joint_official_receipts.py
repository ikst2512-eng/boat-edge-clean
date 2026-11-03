import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
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
            if filename == "beforeinfo.json":
                manifest["url"] = "https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&hd=20261102&jcd=19&rno=10"
            else:
                manifest["official_url"] = "https://www.boatrace.jp/owpc/pc/race/odds3t?hd=20261102&jcd=19&rno=10"
            if late: manifest["request_started_at_jst"] = "2026-11-02T21:39:50+09:00"
            (folder / "manifest.json").write_text(json.dumps(manifest))
        return first, second

    def test_nonofficial_odds_html_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = self.make(root, complete=False)
            with self.assertRaises(ValueError):
                audit_pair(a, b)

    def test_forged_official_source_url_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = self.make(root)
            m = json.loads((b / "manifest.json").read_text())
            m["official_url"] = "https://example.invalid/owpc/pc/race/odds3t?hd=20261102&jcd=19&rno=10"
            (b / "manifest.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "official source URL mismatch"):
                audit_pair(a, b)

    def test_complete_pair_does_not_certify_uncaptured_entry_or_racecard(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = self.make(root)
            with patch("scripts.audit_joint_official_receipts.parse_official_odds_table", return_value={"fixture": 1}), patch(
                "scripts.audit_joint_official_receipts.inspect_odds_receipt",
                return_value={"valid_120_combinations": True, "complete_odds_observed_before_t12": True}
            ):
                result = audit_pair(a, b)
            self.assertTrue(result["both_complete_before_t12"])
            self.assertFalse(result["full_t12_source_certified"])
            self.assertFalse(result["independent_source_coverage"]["official_racecard_original"])
            self.assertFalse(result["independent_source_coverage"]["official_entry_original"])

    def test_tampered_odds_original_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = self.make(root)
            (b / "original.html").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                audit_pair(a, b)

    def test_prior_day_odds_http_start_is_not_valid_same_day_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = self.make(root)
            manifest_path = b / "manifest.json"
            m = json.loads(manifest_path.read_text())
            m["request_started_at_jst"] = "2026-11-01T23:59:59+09:00"
            manifest_path.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "race day mismatch"):
                audit_pair(a, b)

    def test_prior_day_beforeinfo_http_start_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = self.make(root)
            manifest_path = a / "manifest.json"
            m = json.loads(manifest_path.read_text())
            m["request_started_at_jst"] = "2026-11-01T23:59:59+09:00"
            manifest_path.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "race day mismatch"):
                audit_pair(a, b)

    def test_deadline_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = self.make(root)
            m = json.loads((b / "manifest.json").read_text())
            m["deadline_at_jst"] = "2026-11-02T21:52:00+09:00"
            (b / "manifest.json").write_text(json.dumps(m))
            with self.assertRaises(ValueError):
                audit_pair(a, b)
