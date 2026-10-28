import unittest
from pathlib import Path
from selection_dual import report
ROOT=Path(__file__).resolve().parent
class DualSelectionTests(unittest.TestCase):
 def test_full_history_and_read_only_selection(self):
  data=report(ROOT)
  self.assertEqual(data["schema"],"CLEAN_DUAL_RESEARCH_V1")
  self.assertEqual(data["prediction_publication_policy"],"all_races_unfiltered")
  self.assertLessEqual(len(data["recent_verified_races"]),24)
  for item in data["recent_verified_races"]:
   self.assertIn(item["selection"],("candidate","skip"))
   self.assertEqual(item["selection"]=="candidate",item["confidence_pct"]>=70 or abs(item["confidence_pct"]-70)<0.005)
   self.assertIn(item["cohort"],("retrospective","post_policy"))
  # The verified history grows daily: assert internal accounting, not a stale fixed sample count.
  import json
  history=json.loads((ROOT/"four_mode_performance"/"history-10000.json").read_text(encoding="utf-8"))
  count=len(history["races"])
  self.assertGreater(count,0)
  self.assertEqual(data["sample_races"],count)
  all_ledger=data["ledgers"]["all"]
  self.assertEqual(all_ledger["races"],count)
  self.assertEqual(all_ledger["investment_yen"],count*10000)
  self.assertGreaterEqual(all_ledger["hits"],0)
  self.assertLessEqual(all_ledger["hits"],count)
  for name in ("confidence_70",):
   ledger=data["ledgers"][name]
   self.assertGreaterEqual(ledger["races"],0)
   self.assertLessEqual(ledger["races"],count)
   self.assertLessEqual(ledger["hits"],ledger["races"])
   self.assertEqual(ledger["investment_yen"],ledger["races"]*10000)
  self.assertEqual(data["minimum_confidence"],0.70)
 def test_navigation_preserves_full_forecast(self):
  html=(ROOT/"index.html").read_text(encoding="utf-8")
  page=(ROOT/"selection.html").read_text(encoding="utf-8")
  server=(ROOT/"server.py").read_text(encoding="utf-8")
  self.assertIn('href="/forecast"',html)
  self.assertIn('href="/selection"',html)
  self.assertIn('"/api/selection-research"',server)
  self.assertIn('"/selection"',server)
  self.assertIn('href="/forecast"',page)
if __name__=="__main__":unittest.main()
