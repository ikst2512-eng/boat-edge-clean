import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from official_prerace_capture import capture_beforeinfo, save_raw_receipt, JST
from official_beforeinfo_research_parser import research_start_exhibition, research_saved_start_exhibition

def fixture(order=(1, 2, 3, 4, 5, 6), st=".08"):
    return ("<html><body>" + "".join(
        '<div class="table1_boatImage1"><span class="table1_boatImage1Number">' +
        str(num) + '</span><span class="table1_boatImage1Time">' + st +
        '</span></div>' for num in order) + "</body></html>").encode()

class ResearchParserTests(unittest.TestCase):
    def test_six_boats_course_distinct_from_number(self):
        p = research_start_exhibition(fixture((2,1,3,4,6,5)))
        self.assertEqual([r["boat_number"] for r in p["start_exhibition"]], [2,1,3,4,6,5])
        self.assertEqual([r["exhibition_course"] for r in p["start_exhibition"]], list(range(1,7)))
        self.assertEqual(p["start_exhibition"][0]["exhibition_st"], .08)
        self.assertFalse(p["actual_entry_verified"])
        self.assertEqual(p["status"], "research_unverified")

    def test_st_forms(self):
        for st, target in (("F.04", -.04), ("0.08", .08), (".08", .08)):
            self.assertAlmostEqual(research_start_exhibition(fixture(st=st))["start_exhibition"][0]["exhibition_st"], target)

    def test_archived_receipt_provenance_and_tamper_rejection(self):
        now = datetime(2026, 10, 27, 14, 50, tzinfo=JST)
        deadline = now + timedelta(minutes=10)
        raw = fixture((2,1,3,4,6,5))
        class Response:
            status = 200
            headers = {"Content-Type": "text/html"}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return raw
        receipt, data = capture_beforeinfo("20261027-12-01", deadline,
            now=now, completed_at=now, opener=lambda *args, **kwargs: Response())
        with tempfile.TemporaryDirectory() as directory:
            paths = save_raw_receipt(receipt, data, directory, deadline=deadline)
            result = research_saved_start_exhibition(directory, receipt["race_key"],
                receipt["sha256"], deadline=deadline)
            self.assertEqual(result["race_key"], receipt["race_key"])
            self.assertEqual(result["raw_sha256"], receipt["sha256"])
            self.assertFalse(result["actual_entry_verified"])
            self.assertEqual(result["start_exhibition"][0]["boat_number"], 2)
            Path(paths[0]).write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                research_saved_start_exhibition(directory, receipt["race_key"],
                    receipt["sha256"], deadline=deadline)

    def test_hidden_duplicate_and_unrelated_fields_ignored(self):
        hidden = '<template><div class="table1_boatImage1"><span class="table1_boatImage1Number">1</span><span class="table1_boatImage1Time">.08</span></div></template>'
        unrelated = '<span class="table1_boatImage1Time">.90</span>'
        raw = ('<html><body>' + hidden + unrelated + fixture().decode().replace('<html><body>', '').replace('</body></html>', '') + '</body></html>').encode()
        data = research_start_exhibition(raw)
        self.assertEqual(len(data["start_exhibition"]), 6)
        self.assertAlmostEqual(data["start_exhibition"][0]["exhibition_st"], .08)

    def test_css_and_aria_hidden_duplicate_ignored(self):
        for wrapper in ('<div aria-hidden="true">', '<div style="display:none">',
                        '<div style="visibility: hidden">'):
            ghost = '<div class="table1_boatImage1"><span class="table1_boatImage1Number">1</span></div>'
            raw = (wrapper + ghost + '</div>' + fixture().decode()).encode()
            self.assertEqual(len(research_start_exhibition(raw)["start_exhibition"]), 6)

    def test_nested_boat_block_rejected(self):
        raw = fixture().decode().replace(
            '<span class="table1_boatImage1Number">1</span>',
            '<div class="table1_boatImage1"><span class="table1_boatImage1Number">1</span></div>',
            1).encode()
        with self.assertRaises(ValueError):
            research_start_exhibition(raw)

    def test_missing_duplicate_or_bad_st_rejected(self):
        for raw in (fixture((1,2,3,4,5)), fixture((1,2,3,4,5,5)),
                    fixture(st=""), fixture(st="L.08"), fixture(st="9.99")):
            with self.assertRaises(ValueError):
                research_start_exhibition(raw)

if __name__ == "__main__":
    unittest.main()
