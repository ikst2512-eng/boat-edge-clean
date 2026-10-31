import tempfile
import unittest
from pathlib import Path
from evaluate_clean_prospective_cohort import cohort,verified_payout

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
            self.assertEqual(r["awaiting_result_race_codes"],["202610290102"])
    def test_no_result_yields_null_rates(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(cohort("20261029",tmp)["hit_rate_pct"]["top10"])
    def test_roi_only_with_verified_payout(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"prospective_predictions").mkdir()
            (root/"four_mode_performance"/"verified_races").mkdir(parents=True)
            code="202610290101"
            (root/"prospective_predictions"/(code+".json")).write_text("{}")
            evidence={"race_code":code,"schema":"CLEAN_VERIFIED_FOUR_MODE_RACE_V1",
                      "verified":True,"simulated_only":True,"official_finish":"1-2-3",
                      "official_payout_yen_per_100":200}
            path=root/"four_mode_performance"/"verified_races"/(code+".json")
            path.write_text(json.dumps(evidence))
            def scored(code,root):
                return {"status":"evaluated","formal":False,"audited":True,"winning_ticket":"1-2-3",
                        "rank":1,"top3":True,"top5":True,"top10":True}
            result=cohort("20261029",root,scored)
            self.assertEqual(result["roi"]["top3"]["return_yen"],3400)
            self.assertEqual(result["roi"]["top5"]["return_yen"],2000)
            self.assertEqual(result["roi"]["top10"]["return_yen"],1000)
            self.assertEqual(result["payout_unavailable"],0)
            evidence["official_finish"]="2-1-3"
            path.write_text(json.dumps(evidence))
            no_proof=cohort("20261029",root,scored)
            self.assertIsNone(no_proof["roi"]["top3"]["roi_pct"])
            self.assertEqual(no_proof["payout_unavailable"],1)
    def test_inconsistent_rank_is_rejected_not_counted_as_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); d=root/"prospective_predictions"; d.mkdir()
            (d/"202610290101.json").write_text("{}")
            def scorer(code, root):
                return {"status":"evaluated","formal":False,"audited":True,
                        "rank":2,"top3":False,"top5":True,"top10":True}
            data=cohort("20261029",root,scorer)
            self.assertEqual(data["counts"]["audit_rejected"],1)
            self.assertEqual(data["counts"]["evaluated"],0)
            self.assertIsNone(data["hit_rate_pct"]["top10"])

    def test_nonmonotonic_hits_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); d=root/"prospective_predictions"; d.mkdir()
            (d/"202610290101.json").write_text("{}")
            def scorer(code, root):
                return {"status":"evaluated","formal":False,"audited":True,
                        "top3":True,"top5":False,"top10":True}
            data=cohort("20261029",root,scorer)
            self.assertEqual(data["counts"]["audit_rejected"],1)
            self.assertEqual(data["counts"]["evaluated"],0)

    def test_unverified_payout_is_rejected(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/"four_mode_performance"/"verified_races"/"202610290101.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"race_code":"202610290101","schema":"CLEAN_VERIFIED_FOUR_MODE_RACE_V1",
                "verified":False,"simulated_only":True,"official_finish":"1-2-3","official_payout_yen_per_100":200}))
            self.assertIsNone(verified_payout("202610290101",root))
if __name__=="__main__":unittest.main()
