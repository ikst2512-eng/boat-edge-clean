import json
import hashlib
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scripts.capture_official_racelist_receipt import capture
from scripts.audit_official_racelist_receipt import audit_racelist, audit_racelist_with_official_deadline

RACE = "202611031201"
JST = timezone(timedelta(hours=9))


class AuditRacelistReceiptTests(unittest.TestCase):
    def make(self, root):
        times = iter((datetime(2026,11,3,10,0,tzinfo=JST), datetime(2026,11,3,10,0,1,tzinfo=JST)))
        result = capture(RACE, root, "proof", fetch=lambda _: b"<!doctype html><html><body>fixture</body></html>", clock=lambda: next(times))
        self.assertEqual(result["status"], "official_racelist_html_observed_research_only")
        return Path(root) / "observations" / "proof" / "20261103" / RACE

    def make_beforeinfo(self, root):
        directory = Path(root) / "beforeproof"
        directory.mkdir()
        race = {"maindata": {"hd": "20261103", "jcd": "12", "rno": "1",
                "deadline": "10:14", "teiinfolist": []}}
        raw = json.dumps(race).encode()
        (directory / "beforeinfo.json").write_bytes(raw)
        manifest = {
            "race_code": RACE, "status": "official_json_observed_not_t12_certified",
            "url": "https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&hd=20261103&jcd=12&rno=1",
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "request_started_at_jst": "2026-11-03T09:59:00+09:00",
            "received_at_jst": "2026-11-03T09:59:01+09:00",
        }
        (directory / "manifest.json").write_text(json.dumps(manifest))
        return directory

    def test_cutoff_is_derived_from_official_source(self):
        with tempfile.TemporaryDirectory() as root:
            racecard = self.make(root)
            beforeinfo = self.make_beforeinfo(root)
            result = audit_racelist_with_official_deadline(racecard, beforeinfo, RACE)
            self.assertTrue(result["received_by_t12"])
            self.assertTrue(result["cutoff_source_verified"])
            self.assertEqual(result["official_deadline_jst"], "2026-11-03T10:14:00+09:00")
            self.assertFalse(result["full_t12_source_certified"])

    def test_tampered_deadline_original_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            racecard = self.make(root)
            beforeinfo = self.make_beforeinfo(root)
            (beforeinfo / "beforeinfo.json").write_bytes(b'{"maindata":{"deadline":"23:59"}}')
            with self.assertRaisesRegex(ValueError, "integrity mismatch"):
                audit_racelist_with_official_deadline(racecard, beforeinfo, RACE)

    def test_forged_official_cutoff_url_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            racecard = self.make(root)
            beforeinfo = self.make_beforeinfo(root)
            manifest_file = beforeinfo / "manifest.json"
            m = json.loads(manifest_file.read_text())
            m["url"] = "https://example.invalid"
            manifest_file.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, "official URL mismatch"):
                audit_racelist_with_official_deadline(racecard, beforeinfo, RACE)

    def test_valid_original_is_not_six_racer_or_entry_proof(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.make(root)
            report = audit_racelist(directory, RACE, "2026-11-03T10:05:00+09:00")
            self.assertTrue(report["original_hash_verified"])
            self.assertEqual(report["html_diagnostics"]["html_body_count"], 1)
            self.assertEqual(report["html_diagnostics"]["html_table_count"], 0)
            self.assertFalse(report["html_diagnostics"]["six_racer_rows_verified"])
            self.assertTrue(report["received_before_supplied_cutoff"])
            self.assertNotIn("received_by_t12", report)
            self.assertFalse(report["cutoff_source_verified"])
            self.assertFalse(report["six_racers_verified"])
            self.assertFalse(report["entry_verified"])
            self.assertFalse(report["full_t12_source_certified"])

    def test_xml_declared_xhtml_original_passes_integrity_audit(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.make(root)
            raw = b'<?xml version="1.0"?><html><body>test</body></html>'
            (directory / "racelist.html").write_bytes(raw)
            path = directory / "manifest.json"
            manifest = json.loads(path.read_text())
            manifest["sha256"] = hashlib.sha256(raw).hexdigest()
            manifest["bytes"] = len(raw)
            path.write_text(json.dumps(manifest))
            report = audit_racelist(directory, RACE, "2026-11-03T10:05:00+09:00")
            self.assertTrue(report["original_hash_verified"])
            self.assertFalse(report["six_racers_verified"])

    def test_late_receipt_is_not_t12(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.make(root)
            report = audit_racelist(directory, RACE, "2026-11-03T09:59:00+09:00")
            self.assertFalse(report["received_before_supplied_cutoff"])
            self.assertNotIn("received_by_t12", report)

    def test_tampered_original_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.make(root)
            (directory / "racelist.html").write_bytes(b"<html>tampered</html>")
            with self.assertRaisesRegex(ValueError, "source bytes mismatch"):
                audit_racelist(directory, RACE, "2026-11-03T10:05:00+09:00")

    def test_wrong_origin_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.make(root)
            path = directory / "manifest.json"
            manifest = json.loads(path.read_text())
            manifest["official_url"] = "https://example.com"
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "source identity mismatch"):
                audit_racelist(directory, RACE, "2026-11-03T10:05:00+09:00")

    def test_reversed_or_non_jst_time_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.make(root)
            path = directory / "manifest.json"
            manifest = json.loads(path.read_text())
            manifest["received_at_jst"] = "2026-11-03T00:00:00+00:00"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                audit_racelist(directory, RACE, "2026-11-03T10:05:00+09:00")
