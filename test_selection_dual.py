import unittest
from pathlib import Path
from selection_dual import report
ROOT=Path(__file__).resolve().parent
class DualSelectionTests(unittest.TestCase):
 def test_full_history_and_read_only_selection(self):
  data=report(ROOT)
  self.assertEqual(data["schema"],"CLEAN_DUAL_RESEARCH_V1")
  self.assertEqual(data["prediction_publication_policy"],"all_races_unfiltered")
  self.assertEqual(data["sample_races"],113)
  self.assertTrue(data["selection_is_observational"])
  self.assertFalse(data["prospectively_validated"])
  self.assertEqual(data["ledgers"]["all"]["races"],113)
  self.assertEqual(data["ledgers"]["all"]["hits"],57)
  self.assertEqual(data["ledgers"]["all"]["return_yen"],633250)
  self.assertEqual(data["ledgers"]["confidence_60"]["races"],98)
  self.assertEqual(data["ledgers"]["confidence_70"]["races"],47)
  self.assertEqual(data["ledgers"]["confidence_70"]["hits"],30)
  self.assertEqual(data["ledgers"]["confidence_70"]["return_yen"],298900)
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
