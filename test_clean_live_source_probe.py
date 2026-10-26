import io
import unittest
from clean_live_source_probe import probe, html_diagnostics

class Response:
    status=200
    headers={"Content-Type":"text/plain"}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return b"fixture bytes"

class SourceProbeTests(unittest.TestCase):
    def test_explicit_fullwidth_boat_rows_extracted(self):
        rows = []
        for lane, number in enumerate(("4989", "4684", "5046", "3284", "5243", "5464"), 1):
            fullwidth = "１２３４５６"[lane - 1]
            rows.append(f'<tr><td>{fullwidth}</td><td><a href="/profile?toban={number}">{number}</a></td></tr>')
        html = ("<html><body><table>" + "".join(rows) + "</table></body></html>").encode()
        from clean_live_source_probe import html_diagnostics
        result = html_diagnostics(html)
        self.assertEqual(result["lane_registration_candidates"], {
            1: "4989", 2: "4684", 3: "5046", 4: "3284", 5: "5243", 6: "5464",
        })
        self.assertFalse(result["html_is_race_verified"])

    def test_missing_explicit_boat_row_is_not_six_lane_verified(self):
        html = b'<html><tr><td><a href="/profile?toban=4989">4989</a></td></tr></html>'
        from clean_live_source_probe import html_diagnostics
        self.assertEqual(html_diagnostics(html)["lane_registration_candidates"], {})

    def test_official_beforeinfo_numeric_fields_by_lane(self):
        rows = []
        for lane, number in enumerate(("4989", "4684", "5046", "3284", "5243", "5464"), 1):
            rows.append(f'<tr><td>{lane} 選手{lane} 52.0kg 6.{60+lane} -0.5 <a href="/profile?toban={number}">{number}</a></td></tr>')
        html = ("<html><body><table>" + "".join(rows) + "</table></body></html>").encode()
        result = html_diagnostics(html)
        self.assertEqual(len(result["preview_value_candidates"]), 6)
        self.assertEqual(result["preview_value_candidates"][1]["time"], "6.61")
        self.assertEqual(result["preview_value_candidates"][6]["tilt"], "-0.5")
        self.assertIs(result["html_is_race_verified"], False)

    def test_official_html_structure_is_not_verification(self):
        html=b'<html><head><title>Race</title></head><body><a href="/racer?toban=1234">A</a></body></html>'
        result=html_diagnostics(html)
        self.assertEqual(result["html_inspection"], "structure_only_unverified")
        self.assertFalse(result["html_is_race_verified"])
        self.assertEqual(result["racer_link_count"], 1)

    def test_non_html_response_is_blocked(self):
        self.assertEqual(html_diagnostics(b'not html')["html_inspection"], "blocked_not_html")

    def test_reports_retrieval_without_claiming_verification(self):
        result=probe("20261027","12","1",opener=lambda req,timeout: Response())
        self.assertEqual(result["status"],"UNVERIFIED")
        self.assertFalse(result["readiness_gate"]["can_publish"])
        self.assertFalse(result["readiness_gate"]["can_score_fresh"])
        self.assertFalse(result["readiness_gate"]["official_preview_values_verified"])
        self.assertEqual(len(result["sources"]),6)
        for entry in result["sources"].values():
            self.assertEqual(entry["status"],"retrieved_unverified")
            self.assertEqual(len(entry["sha256"]),64)
        self.assertEqual(result["race_key"],"20261027-12-01")

    def test_real_csv_row_presence_is_not_official_verification(self):
        class CSVResponse(Response):
            def read(self, n):
                return "レースコード,艇1_選手名\n202610261201,例\n".encode("utf-8")
        result=probe("20261026","12","1",opener=lambda req,timeout: CSVResponse())
        self.assertEqual(result["sources"]["race_csv"]["race_rows"],1)
        self.assertEqual(result["sources"]["race_csv"]["race_identity_status"],"single_row_unverified")
        self.assertEqual(result["sources"]["official_racelist"]["race_identity_status"],"not_parsed")

    def test_missing_race_is_blocked(self):
        class CSVResponse(Response):
            def read(self, n):
                return "レースコード\n202610261202\n".encode("utf-8")
        result=probe("20261026","12","1",opener=lambda req,timeout: CSVResponse())
        self.assertEqual(result["sources"]["race_csv"]["race_rows"],0)
        self.assertEqual(result["sources"]["race_csv"]["race_identity_status"],"blocked")

    def test_failed_network_stays_unavailable(self):
        def failure(req,timeout): raise TimeoutError()
        result=probe("20261027","12","1",opener=failure)
        self.assertTrue(all(x["status"]=="unavailable" for x in result["sources"].values()))

    def test_invalid_identity_blocks_probe(self):
        with self.assertRaises(ValueError):
            probe("20261027","25","1")
        with self.assertRaises(ValueError):
            probe("20261027","12","13")
        with self.assertRaises(ValueError):
            probe("20260230","12","1")

if __name__=="__main__":
    unittest.main()
