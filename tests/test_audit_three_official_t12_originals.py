import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.capture_official_racelist_receipt import capture
from scripts.audit_three_official_t12_originals import audit_three_originals

RACE = "202611021910"
JST = timezone(timedelta(hours=9))
DEADLINE = "2026-11-02T21:51:00+09:00"
START = "2026-11-02T21:20:00+09:00"
RECEIVED = "2026-11-02T21:20:05+09:00"


class ThreeOriginalAuditTests(unittest.TestCase):
    def make(self, root):
        root = Path(root)
        boats = ["4180", "5112", "4786", "4159", "4663", "5087"]
        full = "１２３４５６"
        rows = "".join(
            f'<tr><td class="is-boatColor{i} is-fs14" rowspan="4">{full[i-1]}</td>'
            f'<td><a href="/owpc/pc/data/racersearch/profile?toban={reg}">Racer</a></td></tr>'
            for i, reg in enumerate(boats, 1))
        original = ('<?xml version="1.0"?><html><body>' + rows + '</body></html>').encode()
        clock_values = iter((datetime.fromisoformat(START), datetime.fromisoformat(RECEIVED)))
        report = capture(RACE, root, "threeorig", fetch=lambda _: original,
                         clock=lambda: next(clock_values))
        self.assertEqual(report["status"], "official_racelist_html_observed_research_only")
        card = root / "observations" / "threeorig" / "20261102" / RACE
        before, odds = root / "before", root / "odds"
        before.mkdir(); odds.mkdir()
        source = {"maindata": {"hd": "20261102", "jcd": "19", "rno": "10",
                  "deadline": "21:51",
                  "teiinfolist": [{"teino": str(i), "racerno": boats[i-1], "extime": "6.75", "tilt": "0"}
                                  for i in range(1,7)],
                  "sttenjiinfolist": [{"teino": str(i), "cs": 7-i, "st": ".05"}
                                      for i in range(1,7)]}}
        raw_before = json.dumps(source).encode()
        raw_odds = b"<html><body>odds</body></html>"
        for directory, filename, data, status, extra in (
                (before, "beforeinfo.json", raw_before,
                 "official_json_observed_not_t12_certified",
                 {"url": "https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&hd=20261102&jcd=19&rno=10"}),
                (odds, "original.html", raw_odds, "official_odds_observed_research_only",
                 {"official_url": "https://www.boatrace.jp/owpc/pc/race/odds3t?hd=20261102&jcd=19&rno=10",
                  "deadline_at_jst": DEADLINE})):
            (directory / filename).write_bytes(data)
            m = {"race_code": RACE, "status": status, "sha256": hashlib.sha256(data).hexdigest(),
                 "bytes": len(data), "request_started_at_jst": START,
                 "received_at_jst": RECEIVED, **extra}
            (directory / "manifest.json").write_text(json.dumps(m))
        return card, before, odds

    def joined(self, card, before, odds):
        with patch("scripts.audit_joint_official_receipts.parse_official_odds_table", return_value={"fixture": 1}), patch(
            "scripts.audit_joint_official_receipts.inspect_odds_receipt",
            return_value={"valid_120_combinations": True, "complete_odds_observed_before_t12": True}
        ):
            return audit_three_originals(card, before, odds)

    def test_three_originals_report_research_completion_but_not_final_entry(self):
        with tempfile.TemporaryDirectory() as root:
            card, before, odds = self.make(root)
            result = self.joined(card, before, odds)
            self.assertTrue(result["all_research_components_observed_by_t12"])
            self.assertEqual(result["missing_components"], [])
            self.assertEqual(result["registrations_by_lane"]["1"], "4180")
            self.assertEqual(result["latest_original_received_jst"], RECEIVED)
            self.assertEqual(result["t12_receipt_margin_seconds"], 19 * 60 - 5)
            self.assertEqual(result["exhibition_course_to_boat"]["1"], "6")
            self.assertFalse(result["final_race_entry_verified"])
            self.assertFalse(result["full_t12_source_certified"])
            self.assertFalse(result["forecast_usable"])
            self.assertFalse(result["t12_eligible"])

    def test_beforeinfo_duplicate_boat_number_never_counts_as_complete(self):
        with tempfile.TemporaryDirectory() as root:
            card, before, odds = self.make(root)
            path = before / "beforeinfo.json"
            payload = json.loads(path.read_text())
            payload["maindata"]["teiinfolist"][5]["teino"] = "5"
            raw = json.dumps(payload).encode()
            path.write_bytes(raw)
            mpath = before / "manifest.json"
            m = json.loads(mpath.read_text())
            m["sha256"] = hashlib.sha256(raw).hexdigest()
            m["bytes"] = len(raw)
            mpath.write_text(json.dumps(m))
            result = self.joined(card, before, odds)
            self.assertFalse(result["component_checks"]["beforeinfo_six_unique_boats"])
            self.assertIn("beforeinfo_six_unique_boats", result["missing_components"])
            self.assertFalse(result["all_research_components_observed_by_t12"])
            self.assertFalse(result["forecast_usable"])

    def test_official_beforeinfo_racer_number_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            card, before, odds = self.make(root)
            path = before / "beforeinfo.json"
            payload = json.loads(path.read_text())
            payload["maindata"]["teiinfolist"][0]["racerno"] = "9999"
            raw = json.dumps(payload).encode()
            path.write_bytes(raw)
            manifest_path = before / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["sha256"] = hashlib.sha256(raw).hexdigest()
            manifest["bytes"] = len(raw)
            manifest_path.write_text(json.dumps(manifest))
            result = self.joined(card, before, odds)
            self.assertFalse(result["all_research_components_observed_by_t12"])
            self.assertIn("racer_registration_ids_match", result["missing_components"])
            self.assertFalse(result["full_t12_source_certified"])
            self.assertFalse(result["forecast_usable"])

    def test_late_racecard_cannot_pass(self):
        with tempfile.TemporaryDirectory() as root:
            card, before, odds = self.make(root)
            mpath = card / "manifest.json"
            m = json.loads(mpath.read_text())
            m["request_started_at_jst"] = "2026-11-02T21:40:00+09:00"
            m["received_at_jst"] = "2026-11-02T21:40:05+09:00"
            mpath.write_text(json.dumps(m))
            result = self.joined(card, before, odds)
            self.assertFalse(result["all_research_components_observed_by_t12"])
            self.assertIn("racecard_received_by_t12", result["missing_components"])

    def test_late_beforeinfo_cannot_pass(self):
        with tempfile.TemporaryDirectory() as root:
            card, before, odds = self.make(root)
            mpath = before / "manifest.json"
            m = json.loads(mpath.read_text())
            m["request_started_at_jst"] = "2026-11-02T21:40:00+09:00"
            m["received_at_jst"] = "2026-11-02T21:40:05+09:00"
            mpath.write_text(json.dumps(m))
            result = self.joined(card, before, odds)
            self.assertIn("beforeinfo_received_by_t12", result["missing_components"])

    def test_tampered_racecard_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            card, before, odds = self.make(root)
            (card / "racelist.html").write_bytes(b"<html>changed</html>")
            with self.assertRaisesRegex(ValueError, "source bytes mismatch"):
                self.joined(card, before, odds)

    def test_different_odds_race_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            card, before, odds = self.make(root)
            mpath = odds / "manifest.json"
            m = json.loads(mpath.read_text())
            m["race_code"] = "202611021911"
            mpath.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "race identity mismatch"):
                self.joined(card, before, odds)
