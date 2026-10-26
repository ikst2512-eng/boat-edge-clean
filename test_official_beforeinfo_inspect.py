import unittest
from official_beforeinfo_inspect import inspect_beforeinfo_html

RECEIPT={"race_key":"20261027-22-05","status":"raw_html_only","verified_preview":False}

class InspectionTests(unittest.TestCase):
    def test_complete_headings_never_verify_values(self):
        html="<html><body><table><tr><th>展示タイム</th><th>チルト</th></tr></table><h2>スタート展示</h2><p>気温 風速 水温 波高</p></body></html>".encode()
        result=inspect_beforeinfo_html(RECEIPT,html)
        self.assertTrue(all(result["sections_present"].values()))
        self.assertEqual(result["status"],"inspection_only")
        self.assertFalse(result["verified_preview"])
        self.assertFalse(result["actual_entry_verified"])
        self.assertEqual(result["racers"],[])
        self.assertEqual(result["start_exhibition"],[])
    def test_incomplete_html_is_not_verified(self):
        result=inspect_beforeinfo_html(RECEIPT,b"<html><body><p>展示タイム</p></body></html>")
        self.assertIn("start_exhibition",result["missing_sections"])
        self.assertFalse(result["verified_preview"])
    def test_script_labels_are_not_evidence(self):
        result=inspect_beforeinfo_html(RECEIPT,b"<html><script>var label='\xe5\xb1\x95\xe7\xa4\xba\xe3\x82\xbf\xe3\x82\xa4\xe3\x83\xa0';</script></html>")
        self.assertFalse(result["sections_present"]["exhibition_time"])
    def test_reject_promotion(self):
        with self.assertRaises(ValueError):
            inspect_beforeinfo_html({**RECEIPT,"verified_preview":True},b"<html></html>")

if __name__=="__main__":
    unittest.main()
