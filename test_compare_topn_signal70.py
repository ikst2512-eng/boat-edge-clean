import json
import tempfile
import unittest
from pathlib import Path
from compare_topn_signal70 import compare

class Signal70Tests(unittest.TestCase):
    def test_observational_split_never_calls_model_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=root/"prospective_predictions";d.mkdir()
            for name,rate in (("202610290101",1),("202610290102",0),("202610290103",1)):
                (d/(name+".json")).write_text(json.dumps({"national_win_rates":[rate]*6}))
            def scorer(code,root):
                if code.endswith("03"):return {"status":"result_unavailable"}
                return {"status":"evaluated","formal":False,"audited":True,"rank":2,
                        "winning_ticket":"1-2-3","top3":True,"top5":True,"top10":True}
            result=compare("20261029",root,scorer,lambda rates:.8 if rates[0] else .4)
            self.assertEqual(result["groups"]["signal_70_plus"]["evaluated"],1)
            self.assertEqual(result["groups"]["signal_70_plus"]["awaiting_result"],1)
            self.assertEqual(result["groups"]["below_70"]["evaluated"],1)
            self.assertIsNone(result["groups"]["signal_70_plus"]["roi_pct"]["top10"])
            self.assertFalse(result["signal_is_empirical_confidence"])
            self.assertEqual(result["groups"]["signal_70_plus"]["roi_denominator"],"payout_verified_only_not_all_evaluated_races")
            self.assertEqual(result["groups"]["signal_70_plus"]["payout_coverage_pct"],0.0)
if __name__=="__main__":unittest.main()
