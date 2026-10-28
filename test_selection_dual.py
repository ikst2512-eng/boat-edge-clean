import unittest
import json
from pathlib import Path
from selection_dual import report
ROOT=Path(__file__).resolve().parent
class DualSelectionTests(unittest.TestCase):
 def test_full_history_and_read_only_selection(self):
  data=report(ROOT)
  self.assertEqual(data["schema"],"CLEAN_DUAL_RESEARCH_V1")
  self.assertEqual(data["prediction_publication_policy"],"all_races_unfiltered")
  history=json.loads((ROOT/"four_mode_performance"/"history-10000.json").read_text(encoding="utf-8"))
  self.assertEqual(data["sample_races"],len(history["races"]))
  self.assertTrue(data["selection_is_observational"])
  self.assertFalse(data["prospectively_validated"])
  all_races=data["ledgers"]["all"]
  self.assertEqual(all_races["races"],len(history["races"]))
  self.assertEqual(all_races["investment_yen"],10000*len(history["races"]))
  self.assertGreaterEqual(all_races["hits"],0)
  self.assertLessEqual(all_races["hits"],all_races["races"])
  self.assertEqual(all_races["profit_yen"],all_races["return_yen"]-all_races["investment_yen"])
  self.assertEqual(data["minimum_confidence"],0.70)
  self.assertEqual(data["below_minimum_policy"],"skip_selection_keep_forecast")
  self.assertNotIn("confidence_60",data["ledgers"])
  for name in ("confidence_70",):
   selected=data["ledgers"][name]
   self.assertLessEqual(selected["races"],all_races["races"])
   self.assertEqual(selected["investment_yen"],selected["races"]*10000)
   self.assertEqual(selected["profit_yen"],selected["return_yen"]-selected["investment_yen"])
  self.assertLessEqual(data["ledgers"]["confidence_70"]["races"],all_races["races"])
 def test_navigation_preserves_full_forecast(self):
  html=(ROOT/"index.html").read_text(encoding="utf-8")
  page=(ROOT/"selection.html").read_text(encoding="utf-8")
  server=(ROOT/"server.py").read_text(encoding="utf-8")
  self.assertIn('href="/forecast"',html)
  self.assertIn('href="/selection"',html)
  self.assertIn('"/api/selection-research"',server)
  self.assertIn('"/selection"',server)
  self.assertIn('href="/forecast"',page)
  self.assertIn("信頼度70%以上",page)
  self.assertNotIn("信頼度60%以上",page)
if __name__=="__main__":unittest.main()
