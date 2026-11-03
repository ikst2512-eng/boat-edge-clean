import unittest
from hole_future_cumulative_rollup import rollup

MODES=("baseline","donor_order","max_ticket_score","third_national_rate")
def flags(b=False,a=False):
    return {m:{"top3":False,"top5":False,"top10":b if m=="baseline" else a}
            for m in MODES}
def report(rows,start="2026-11-04",end="2026-11-06",complete=False):
    return {"schema":"HOLE_FUTURE_ARTIFACT_BATCH_V1",
            "formal":False,"independent_first_receipt_verified":False,
            "window_start_jst":start,"window_end_exclusive_jst":end,
            "capture_window_complete":complete,
            "per_race_flags":rows,"race_codes":sorted(rows),
            "comparable":len(rows)}

class CumulativeEvidenceTests(unittest.TestCase):
    def test_overlapping_identical_race_is_counted_once(self):
        a=report({"202611040101":flags(False,True)})
        b=report({"202611040101":flags(False,True),"202611050101":flags(True,False)},
                 "2026-11-04","2026-11-07")
        out=rollup([a,b])
        self.assertEqual(out["comparable"],2)
        self.assertEqual(out["hits"]["baseline"]["top10"],1)
        self.assertEqual(out["hits"]["third_national_rate"]["top10"],1)
        self.assertEqual(out["delta"]["third_national_rate"]["top10"],
                         {"gained":1,"lost":1,"net":0})
        self.assertEqual(out["incomplete_window_reports"],2)
        self.assertFalse(out["formal"])
    def test_conflicting_later_evidence_quarantined(self):
        a=report({"202611040101":flags(False,True)})
        b=report({"202611040101":flags(False,False)},
                 "2026-11-04","2026-11-07")
        out=rollup([a,b])
        self.assertEqual(out["comparable"],0)
        self.assertEqual(out["conflicted_codes_quarantined"],["202611040101"])
    def test_report_without_per_race_flags_never_counts_prior_totals(self):
        old=report({"202611040101":flags(False,True)})
        del old["per_race_flags"]
        out=rollup([old])
        self.assertEqual(out["comparable"],0)
        self.assertEqual(out["invalid_report_counts"]["missing_or_inconsistent_race_flags"],1)
    def test_unverified_claim_is_not_accepted(self):
        bad=report({"202611040101":flags(False,True)})
        bad["independent_first_receipt_verified"]=True
        out=rollup([bad])
        self.assertEqual(out["comparable"],0)
        self.assertEqual(out["invalid_report_counts"]["untrusted_report"],1)
    def test_top5_mutation_cannot_be_counted(self):
        f=flags(False,True)
        f["third_national_rate"]["top5"]=True
        out=rollup([report({"202611040101":f})])
        self.assertEqual(out["invalid_report_counts"]["top5_shift"],1)
        self.assertEqual(out["comparable"],0)
    def test_out_of_window_report_cannot_inflate_cumulative_accuracy(self):
        valid=report({"202611040101":flags(False,True)})
        bad=report({"202611050101":flags(False,True)},
                   "2026-11-04","2026-11-05")
        out=rollup([valid,bad])
        self.assertEqual(out["comparable"],1)
        self.assertEqual(out["race_codes"],["202611040101"])
        self.assertEqual(out["invalid_report_counts"]["race_outside_report_window"],1)
    def test_invalid_calendar_date_is_not_accepted(self):
        bad=report({"202611310101":flags(False,True)})
        out=rollup([bad])
        self.assertEqual(out["comparable"],0)
        self.assertEqual(out["invalid_report_counts"]["race_outside_report_window"],1)
    def test_boundary_start_inclusive_end_exclusive(self):
        out=rollup([report({"202611040101":flags(False,True)},
                           "2026-11-04","2026-11-05")])
        self.assertEqual(out["comparable"],1)
        bad=rollup([report({"202611050101":flags(False,True)},
                            "2026-11-04","2026-11-05")])
        self.assertEqual(bad["comparable"],0)
    def test_nonmonotonic_topk_hit_flags_are_rejected(self):
        row=flags(False,True)
        row["third_national_rate"]["top3"]=True
        row["third_national_rate"]["top5"]=True
        row["third_national_rate"]["top10"]=False
        # Match Top3/5 across methods to isolate monotonicity failure.
        for mode in MODES:
            row[mode]["top3"]=True
            row[mode]["top5"]=True
        out=rollup([report({"202611040101":row})])
        self.assertEqual(out["comparable"],0)
        self.assertEqual(out["invalid_report_counts"]["nonmonotonic_hit_flags"],1)
    def test_malformed_report_window_rejected(self):
        bad=report({"202611040101":flags(False,True)})
        bad["window_start_jst"]="not-a-date"
        out=rollup([bad])
        self.assertEqual(out["comparable"],0)
        self.assertEqual(out["invalid_report_counts"]["invalid_window"],1)
    def test_empty_reports_not_formal_proof(self):
        out=rollup([])
        self.assertEqual(out["comparable"],0)
        self.assertFalse(out["historical_reporting_coverage_proven"])
        self.assertFalse(out["prospective_validation"])
if __name__=="__main__":unittest.main()
