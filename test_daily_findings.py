import unittest
from pathlib import Path
from daily_findings import daily_findings
ROOT=Path(__file__).resolve().parent
class FindingsTests(unittest.TestCase):
 def test_findings_are_grounded_and_report_scope(self):
  data=daily_findings(ROOT)
  self.assertEqual(data["schema"],"CLEAN_DAILY_FINDINGS_V1")
  self.assertEqual(data["minimum_confidence"],0.7)
  self.assertGreater(data["latest_verified_sample"],0)
  self.assertLessEqual(data["confidence_70"]["races"],data["all_races"]["races"])
  self.assertTrue(data["research_only"])
  self.assertTrue(all(not x["sample_only"] for x in data["recent_days"]))
  self.assertEqual(sum(x["verified_races"] for x in data["recent_days"]),data["latest_verified_sample"])
  self.assertTrue(all(x["verified_races"]==x["candidate_races"]+x["skipped_races"] for x in data["recent_days"]))
  self.assertTrue(all(x["kind"] in ("観測結果","未検証") for x in data["findings"]))
 def test_tab_and_routes_exist(self):
  h=(ROOT/"index.html").read_text(encoding="utf-8")
  s=(ROOT/"server.py").read_text(encoding="utf-8")
  page=(ROOT/"daily_findings.html").read_text(encoding="utf-8")
  self.assertIn('class="daily-head-tab"',h)
  self.assertIn('href="/daily-findings"',h)
  self.assertIn('"/api/daily-findings"',s)
  self.assertIn('"/daily-findings"',s)
  self.assertIn("未確認の内容は掲載しません",page)
if __name__=="__main__":unittest.main()
