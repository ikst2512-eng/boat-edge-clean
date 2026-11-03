import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from hole_forward_date_replay import analyze,ticket_variants

class ForwardDateTests(unittest.TestCase):
 def test_prior_period_is_not_independent(self):
  with self.assertRaises(ValueError):
   analyze(".",date="20261102")
 def test_two_ticket_bundle_is_result_blind(self):
  hole=["1-2-3","1-3-4","1-2-4","1-3-5","1-4-2"]
  donor=["1-5-2","1-5-3"]
  archive={"modes":{
   "hole":{"tickets":[{"combo":c} for c in hole]},
   "hit":{"tickets":[{"combo":c} for c in donor]},
   "balance":{"tickets":[]}}}
  v=ticket_variants(archive)
  self.assertEqual(v["bundle2"][2:4],donor)
  self.assertEqual(len(v["bundle2"]),len(hole))
  self.assertIn("1-3-4",v["bundle2"])
 def test_result_loss_is_reported_not_suppressed(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   (root/"four_mode_forecasts").mkdir()
   (root/"four_mode_forecasts"/"202611031801.json").write_text("{}")
   hole=["1-2-3","1-3-4","1-2-4","1-3-5","1-4-2"]
   archive={"generated_at_jst":"2026-11-03T07:00:00+09:00",
            "deadline_jst":"2026-11-03T08:40:00+09:00",
            "modes":{"hole":{"tickets":[{"combo":c} for c in hole]},
                     "hit":{"tickets":[{"combo":x} for x in ("1-5-2","1-5-3")]},
                     "balance":{"tickets":[]}}}
   with patch("hole_forward_date_replay.archived_four_modes",return_value=(200,archive)),patch(
        "hole_forward_date_replay.compare_race",return_value={
             "status":"historical_comparison_only","winning_ticket":"1-3-5"}):
    r=analyze(root)
   self.assertEqual(r["comparable"],1)
   self.assertEqual(r["hits"]["baseline"]["top5"],1)
   self.assertEqual(r["hits"]["bundle2"]["top5"],0)
   self.assertEqual(r["delta"]["bundle2"]["top5"]["lost"],1)
   self.assertFalse(r["formal"])
if __name__=="__main__":unittest.main()
