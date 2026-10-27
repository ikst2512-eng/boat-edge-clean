import unittest
from research_scenario_candidate import scenario_candidates

class ScenarioCandidateTests(unittest.TestCase):
    def test_exhaustive_unique_ordered_candidates(self):
        rows=scenario_candidates([5.1,5.2,5.3,5.4,5.5,5.6])
        self.assertEqual(len(rows),10)
        self.assertEqual(len({r['ticket'] for r in rows}),10)
        self.assertTrue(all(r['estimated_probability_pct']>0 for r in rows))
        self.assertEqual(sorted([r['estimated_probability_pct'] for r in rows],reverse=True),[r['estimated_probability_pct'] for r in rows])
    def test_invalid_input_fails_closed(self):
        with self.assertRaises(ValueError):scenario_candidates([4.0]*5)
if __name__=='__main__':unittest.main()
