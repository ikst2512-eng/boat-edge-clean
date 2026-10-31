import tempfile
import unittest
import json
from pathlib import Path
from compare_fixed_threshold_holdout import report

class Tests(unittest.TestCase):
 def test_discovery_and_holdout_separate_and_pending_excluded(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/"prospective_predictions";folder.mkdir()
   for day in ("20261029","20261030","20261031"):
    (folder/(day+"0101.json")).write_text(json.dumps({"national_win_rates":[1]*6}))
    (folder/(day+"0102.json")).write_text(json.dumps({"national_win_rates":[0]*6}))
   def scored(code,root):
    if code.endswith("02"):return {"status":"result_unavailable"}
    return {"status":"evaluated","audited":True,"formal":False,"rank":2,
            "top3":True,"top5":True,"top10":True,"winning_ticket":"1-2-3"}
   result=report(root=root,scorer=scored,signal=lambda x:.77,payout=lambda code,root:("1-2-3",200))
   self.assertEqual([d["role"] for d in result["days"]],["discovery","later_holdout","second_holdout"])
   for d in result["days"]:
    self.assertEqual(d["pending"],1)
    self.assertEqual(d["evaluated"],1)
    self.assertEqual(d["thresholds"]["70"]["selected"],1)
    self.assertEqual(d["thresholds"]["75"]["selected"],1)
    self.assertEqual(d["thresholds"]["80"]["selected"],0)
    self.assertEqual(d["thresholds"]["70"]["hits"]["top3"],1)
    self.assertEqual(d["thresholds"]["70"]["roi_pct"]["top3"],68.0)
 def test_selection_coverage_and_lift_match_same_day_baseline(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/"prospective_predictions";folder.mkdir()
   for day in ("20261029","20261030"):
    for idx in (1,2):
     (folder/(day+f"01{idx:02d}.json")).write_text(json.dumps({"national_win_rates":[idx]*6}))
   def scored(code,root):
    hit=code.endswith("01")
    return {"status":"evaluated","audited":True,"formal":False,
            "rank":1 if hit else None,"top3":hit,"top5":hit,"top10":hit,
            "winning_ticket":"1-2-3"}
   out=report(root=root,scorer=scored,signal=lambda rates:.75 if rates[0]==1 else .65,
              payout=lambda code,root:("1-2-3",200))
   for day in out["days"]:
    self.assertEqual(day["all_hit_rate_pct"]["top10"],50.0)
    row=day["thresholds"]["70"]
    self.assertEqual(row["selected"],1)
    self.assertEqual(row["selected_pct"],50.0)
    self.assertEqual(row["hit_rate_pct"]["top10"],100.0)
    self.assertEqual(row["lift_pp"]["top10"],50.0)
    self.assertIsNone(day["thresholds"]["80"]["lift_pp"]["top10"])
 def test_rejects_other_day_order(self):
  with self.assertRaises(ValueError):report(days=("20261030","20261029"))
if __name__=="__main__":unittest.main()
