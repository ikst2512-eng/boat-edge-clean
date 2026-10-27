import unittest
from research_official_result_parser import parse_result
URL="https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261027&jcd=01&rno=2"
class ResultParserTests(unittest.TestCase):
    def test_official_trifecta_row(self):
        html="<html><body><table><tr><th>勝式</th><th>組番</th><th>払戻金</th></tr><tr><td>3連単</td><td>1-2-4</td><td>¥1,240</td></tr></table></body></html>"
        row=parse_result(html,URL)
        self.assertEqual(row["race_code"],"202610270102")
        self.assertEqual(row["ticket"],"1-2-4")
        self.assertEqual(row["verification_status"],"UNVERIFIED_SOURCE_RECEIPT")
    def test_rejects_lookalike_host(self):
        with self.assertRaisesRegex(ValueError,"untrusted_official_result_url"):
            parse_result("3連単 1-2-4 ¥1,240",URL.replace("www.boatrace.jp","www.boatrace.jp.evil.org"))
    def test_rejects_ambiguous_rows(self):
        with self.assertRaisesRegex(ValueError,"missing_or_ambiguous_trifecta"):
            parse_result("3連単 1-2-4 ¥1,240 3連単 2-1-4 ¥2,200",URL)
    def test_rejects_missing_result(self):
        with self.assertRaisesRegex(ValueError,"missing_or_ambiguous_trifecta"):
            parse_result("オッズ 3連単 1-2-4",URL)
if __name__=="__main__":unittest.main()
