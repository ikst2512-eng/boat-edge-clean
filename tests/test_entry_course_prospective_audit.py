import unittest
from itertools import permutations
from entry_course_prospective_audit import audit_frozen_comparison,evaluate_verified_prospective
T=["-".join(map(str,t)) for t in permutations(range(1,7),3)]
CODE="202610310708"
CUTOFF="2026-10-31T18:21:00+09:00"
def base():
    return {"race_code":CODE,"predictions":T[:10],"status":"research","validated":False,
            "generated_at":"2026-10-31T10:49:20+09:00","cutoff_jst":CUTOFF,
            "source_deadline_jst":"2026-10-31T18:33:00+09:00",
            "source_cards_sha256":"a"*64,"source_title_sha256":"b"*64,
            "input_sha256":"c"*64,"model_source_sha256":"d"*64}
def candidate():
    return {"race_code":CODE,"frozen_at":"2026-10-31T18:10:00+09:00",
            "cutoff_at":CUTOFF,"entry":[1,2,3,4,5,6],
            "entry_source":"verified_independent_preview","research_only":True,
            "source_receipts":[{"received_at":"2026-10-31T18:00:00+09:00","sha256":"e"*64}],
            "baseline":T[:],"course":T[::-1],"course_plus_st":T[:]}
def result():
    return {"race_code":CODE,"received_at":"2026-10-31T18:50:00+09:00","result":T[0]}
class FrozenComparisonTests(unittest.TestCase):
    def test_stored_baseline_missing_challenger_cannot_score(self):
        audit=audit_frozen_comparison(base(),None,result())
        self.assertFalse(audit["can_score"])
        self.assertIn("course_full_ranking_missing_or_invalid",audit["reasons"])
    def test_complete_before_cutoff_evidence_scored(self):
        gate=audit_frozen_comparison(base(),candidate(),result())
        self.assertTrue(gate["can_score"])
        report=evaluate_verified_prospective([dict(base=base(),candidate=candidate(),result=result())])
        self.assertEqual(report["matched_races"],1)
        self.assertEqual(report["modes"]["baseline"]["Top3"]["hits"],1)
        self.assertEqual(report["modes"]["course"]["Top3"]["hits"],0)
    def test_comparison_uses_exact_frozen_baseline_not_recomputed_position_prior(self):
        c=candidate();c["baseline"]=T[::-1]
        gate=audit_frozen_comparison(base(),c,result())
        self.assertFalse(gate["can_score"])
        self.assertIn("baseline_ranking_differs_from_frozen_prediction",gate["reasons"])
    def test_late_challenger_not_counted_even_with_old_base(self):
        c=candidate();c["frozen_at"]="2026-10-31T18:30:00+09:00"
        report=evaluate_verified_prospective([dict(base=base(),candidate=c,result=result())])
        self.assertEqual(report["matched_races"],0)
        self.assertIn("candidate_not_frozen_before_identical_cutoff",report["prospective_evidence_exclusions"])
    def test_late_or_unverified_sources_not_counted(self):
        c=candidate();c["source_receipts"][0]["received_at"]="2026-10-31T18:30:00+09:00"
        self.assertFalse(audit_frozen_comparison(base(),c,result())["can_score"])
        c=candidate();c["entry_source"]="manual"
        self.assertIn("candidate_entry_source_unverified",audit_frozen_comparison(base(),c,result())["reasons"])
    def test_invalid_and_missing_result_does_not_score(self):
        self.assertFalse(audit_frozen_comparison(base(),candidate())["can_score"])
        self.assertFalse(audit_frozen_comparison(base(),candidate(),{"race_code":CODE,"result":T[0],"received_at":"2026-10-31T18:00:00+09:00"})["can_score"])
    def test_missing_existing_source_hash_excluded(self):
        b=base();b["input_sha256"]="bad"
        self.assertIn("baseline_input_sha256_invalid",audit_frozen_comparison(b,candidate(),result())["reasons"])
    def test_zero_verified_cohort_returns_null_rates(self):
        report=evaluate_verified_prospective([{"base":base()}])
        self.assertEqual(report["matched_races"],0)
        self.assertIsNone(report["modes"]["baseline"]["Top3"]["hit_rate"])
        self.assertFalse(report["empirical_improvement_verified"])
if __name__=="__main__": unittest.main()
