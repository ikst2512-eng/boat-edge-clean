import unittest
from datetime import datetime,timezone,timedelta
from entry_course_candidate import challenger_rank,evaluate_matched
from research_model import TICKETS

ENTRY=[2,1,3,4,5,6]
RATES=[7.0,6.0,5.5,5,4.5,4]
def rows():
    return [dict(boat=boat,course=idx,courseStarts=50,courseWinRate=.1+.02*idx,
      courseTop2Rate=.3+.02*idx,courseTop3Rate=.55+.02*idx,
      courseAverageST=.12+.01*idx,courseDataSource="third_party_historical_asof",
      sufficient_sample=True,observedAt="2026-11-03T18:00:00+09:00")
      for idx,boat in enumerate(ENTRY,1)]
def full():
    return challenger_rank(RATES,ENTRY,rows(),include_st=True)

class CourseCandidateTests(unittest.TestCase):
    def test_three_read_only_variants_120_tickets_normalize(self):
        result=full()
        for name in ("baseline","course","course_plus_st"):
            ranking=result[name]
            self.assertEqual(len(ranking),120)
            self.assertEqual(len(set(t for t,p in ranking)),120)
            self.assertAlmostEqual(sum(p for t,p in ranking),1,places=9)
        self.assertFalse(result["forecast_usable"])
        self.assertFalse(result["validated"])
    def test_missing_course_sample_rejected_not_replaced_with_national_rate(self):
        rs=rows();rs[0]["courseStarts"]=3
        with self.assertRaisesRegex(ValueError,"course_sample"):
            challenger_rank(RATES,ENTRY,rs)
    def test_swapped_course_record_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,"course_sample"):
            challenger_rank(RATES,[1,2,3,4,5,6],rows())
    def test_missing_st_blocks_st_challenger(self):
        rs=rows();rs[0]["courseAverageST"]=None
        with self.assertRaisesRegex(ValueError,"missing_course_average_st"):
            challenger_rank(RATES,ENTRY,rs,include_st=True)
    def test_unverified_source_not_elevated(self):
        rs=rows();rs[0]["courseDataSource"]="manual"
        with self.assertRaisesRegex(ValueError,"course_sample"):
            challenger_rank(RATES,ENTRY,rs)
    def test_nonnumeric_rate_rejected(self):
        rs=rows();rs[0]["courseWinRate"]="0.2"
        with self.assertRaisesRegex(ValueError,"invalid_course_rate"):
            challenger_rank(RATES,ENTRY,rs)
    def test_matched_only_topn(self):
        tickets=["-".join(map(str,t)) for t in TICKETS]
        row={"race_code":"202611030708","cutoff_at":"2026-11-03T19:08:00+09:00",
             "frozen_at":"2026-11-03T19:00:00+09:00",
             "result_received_at":"2026-11-03T19:30:00+09:00",
             "result":tickets[0],"baseline":tickets,"course":tickets[::-1],
             "course_plus_st":tickets}
        evaluated=evaluate_matched([row])
        self.assertEqual(evaluated["matched_races"],1)
        self.assertEqual(evaluated["modes"]["baseline"]["Top3"]["hits"],1)
        self.assertEqual(evaluated["modes"]["course"]["Top3"]["hits"],0)
        self.assertEqual(evaluated["modes"]["course_plus_st"]["Top10"]["hits"],1)
        self.assertFalse(evaluated["empirical_improvement_verified"])
    def test_no_post_result_or_duplicate_data(self):
        tickets=["-".join(map(str,t)) for t in TICKETS]
        row={"race_code":"202611030708","cutoff_at":"2026-11-03T19:08:00+09:00",
             "frozen_at":"2026-11-03T19:09:00+09:00",
             "result_received_at":"2026-11-03T19:30:00+09:00",
             "result":tickets[0],"baseline":tickets,"course":tickets,
             "course_plus_st":tickets}
        got=evaluate_matched([row])
        self.assertEqual(got["matched_races"],0)
        self.assertIsNone(got["modes"]["baseline"]["Top3"]["hit_rate"])
        row["frozen_at"]="2026-11-03T19:00:00+09:00"
        got=evaluate_matched([row,row])
        self.assertEqual(got["matched_races"],1)
        self.assertEqual(got["excluded"]["duplicate_or_bad_race"],1)
    def test_invalid_candidate_ranking_disqualifies_entire_race(self):
        tickets=["-".join(map(str,t)) for t in TICKETS]
        row={"race_code":"202611030708","cutoff_at":"2026-11-03T19:08:00+09:00",
             "frozen_at":"2026-11-03T19:00:00+09:00",
             "result_received_at":"2026-11-03T19:30:00+09:00",
             "result":tickets[0],"baseline":tickets,"course":tickets[:10],
             "course_plus_st":tickets}
        self.assertEqual(evaluate_matched([row])["matched_races"],0)

if __name__=="__main__":
    unittest.main()
