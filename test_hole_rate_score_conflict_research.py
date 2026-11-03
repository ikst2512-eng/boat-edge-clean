import unittest
from pathlib import Path
from unittest.mock import patch
from hole_rate_score_conflict_research import alternatives,inspect
from test_hole_third_choice_research import archive

RATES=[5,3,8,7,6,1]
CODE="202611030101"

class ConflictTests(unittest.TestCase):
    def test_frozen_prefix_and_budget(self):
        picks,_=alternatives(archive(),RATES)
        for t in picks.values():
            self.assertEqual(len(t),10)
            self.assertEqual(len(set(t)),10)
            self.assertEqual(t[:5],picks["baseline"][:5])

    def test_conflicting_rate_and_score(self):
        a=archive()
        a["modes"]["hit"]["tickets"][0]["p"]=9
        a["modes"]["hit"]["tickets"][2]["p"]=9
        picks,bands=alternatives(a,[5,7.5,8,7,6,1])
        self.assertEqual(picks["national"][5:7],["1-5-3","1-6-3"])
        self.assertEqual(picks["score"][5:7],["1-5-2","1-6-2"])
        self.assertEqual(picks["score_guard_1pt"][5:7],["1-5-2","1-6-2"])
        self.assertEqual(bands[("1","5")],"rate_le_1pt")

    def test_no_rates_no_switch(self):
        p,_=alternatives(archive(),None)
        self.assertEqual(p["national"],p["score_guard_1pt"])

    def test_confirmed_count_and_excluded(self):
        a=archive()
        with patch("hole_rate_score_conflict_research.archived_four_modes",return_value=(200,a)),patch(
            "hole_rate_score_conflict_research.national_rates",return_value=RATES),patch(
            "hole_rate_score_conflict_research.compare_race",return_value={
            "status":"historical_comparison_only","winning_ticket":"1-5-3"}):
            r=inspect([CODE],Path("."))
        self.assertEqual(r["comparable"],1)
        self.assertEqual(r["top10"]["national"]["hits"],1)
        with patch("hole_rate_score_conflict_research.archived_four_modes",return_value=(200,a)),patch(
            "hole_rate_score_conflict_research.national_rates",return_value=RATES),patch(
            "hole_rate_score_conflict_research.compare_race",return_value={"status":"pending"}):
            r=inspect([CODE],Path("."))
        self.assertEqual(r["comparable"],0)
        self.assertEqual(r["unavailable"]["unconfirmed_result"],1)

if __name__=="__main__":
    unittest.main()
