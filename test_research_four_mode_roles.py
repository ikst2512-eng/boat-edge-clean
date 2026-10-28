import unittest
from research_model import probabilities
from research_four_mode_roles import research_modes

class ResearchRoleTests(unittest.TestCase):
    def setUp(self):
        self.rows=probabilities([6.2,5.1,4.2,4.5,3.1,2.9])
    def test_roles_without_odds_fail_closed(self):
        result=research_modes(self.rows)
        self.assertEqual([len(result[m]["tickets"]) for m in ("narrow","hit","balance","hole")],[5,10,20,0])
        self.assertEqual(result["hole"]["status"],"odds_required")
        self.assertFalse(result["hit"]["target_proven"])
        for m in ("narrow","hit","balance"):
            self.assertEqual(len(set(x["combo"] for x in result[m]["tickets"])),len(result[m]["tickets"]))
    def test_odds_required_complete_and_valid(self):
        with self.assertRaises(ValueError):
            research_modes(self.rows, {"1-2-3":20})
        odds={"-".join(map(str,t)):30.0 for t,p in self.rows}
        odds["1-2-3"]=0
        with self.assertRaises(ValueError):
            research_modes(self.rows,odds)
        odds["1-2-3"]=30
        result=research_modes(self.rows,odds)
        self.assertEqual(len(result["hole"]["tickets"]),30)
        self.assertEqual(result["hole"]["status"],"research_only_not_a_betting_signal")

if __name__=="__main__":
    unittest.main()
