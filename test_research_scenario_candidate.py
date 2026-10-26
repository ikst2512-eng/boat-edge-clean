"""Scenario candidate invariants only; no claims about real-world accuracy."""
import unittest
from research_scenario_candidate import scenario_probabilities, TICKETS

class ScenarioCandidateTests(unittest.TestCase):
    def test_distribution(self):
        out = scenario_probabilities([6, 5, 7, 6, 4, 5])
        self.assertEqual(len(out), 120)
        self.assertEqual({t for t, _ in out}, set(TICKETS))
        self.assertAlmostEqual(sum(p for _, p in out), 1.0, places=10)
        self.assertTrue(all(p > 0 for _, p in out))

    def test_entry_reorders_courses(self):
        rates = [6] * 6
        old = dict(scenario_probabilities(rates))
        moved = dict(scenario_probabilities(rates, entry=(2, 1, 3, 4, 5, 6)))
        self.assertNotEqual(old[(1, 2, 3)], moved[(1, 2, 3)])
        win_old = sum(p for (a, b, c), p in old.items() if a == 1)
        win_new = sum(p for (a, b, c), p in moved.items() if a == 1)
        self.assertGreater(win_old, win_new)

    def test_skill_affects_probabilities(self):
        low = dict(scenario_probabilities([6] * 6))
        high = dict(scenario_probabilities([6, 9, 6, 6, 6, 6]))
        self.assertGreater(
            sum(p for (a, _, _), p in high.items() if a == 2),
            sum(p for (a, _, _), p in low.items() if a == 2))

    def test_optional_features_and_missing(self):
        neutral = scenario_probabilities([6] * 6)
        same = scenario_probabilities([6] * 6, motor=[None] * 6,
                                      exhibition=[None] * 6, st=[None] * 6,
                                      fl=[None] * 6)
        self.assertEqual(neutral, same)

    def test_invalid_entries_and_features(self):
        with self.assertRaises(ValueError):
            scenario_probabilities([6] * 6, entry=(1, 1, 3, 4, 5, 6))
        with self.assertRaises(ValueError):
            scenario_probabilities([6] * 6, motor=[50] * 5)
        with self.assertRaises(ValueError):
            scenario_probabilities([6] * 6, exhibition=[float("nan")] * 6)
        with self.assertRaises(ValueError):
            scenario_probabilities([6] * 6, fl=[-1] * 6)

if __name__ == "__main__":
    unittest.main()
