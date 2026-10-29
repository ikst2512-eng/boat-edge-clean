import tempfile
import unittest
from pathlib import Path
from evaluate_clean_prospective_cohort import cohort

class TopNCohortTests(unittest.TestCase):
    def test_only_verified_results_are_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d=root/"prospective_predictions";d.mkdir()
            for name in ("202610290101","202610290102","202610290103"):
                (d/(name+".json")).write_text("{}")
            def scorer(code,root):
                if code.endswith("01"):return {"status":"evaluated","formal":False,"audited":True,"top3":False,"top5":True,"top10":True}
                if code.endswith("02"):return {"status":"result_unavailable"}
                raise ValueError("no first Git add")
            r=cohort("20261029",root,scorer)
            self.assertEqual(r["counts"],{"archives":3,"evaluated":1,"awaiting_result":1,"audit_rejected":1})
            self.assertEqual(r["hit_rate_pct"],{"top3":0.0,"top5":100.0,"top10":100.0})
    def test_no_result_yields_null_rates(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(cohort("20261029",tmp)["hit_rate_pct"]["top10"])
if __name__=="__main__":unittest.main()
