import unittest
from scripts.inspect_official_odds_receipt import inspect_odds_receipt

RACE = "202611021512"
DEADLINE = "2026-11-02T20:36:00+09:00"
ODDS = {f"{a}-{b}-{c}": "12.3" for a in range(1,7) for b in range(1,7)
        for c in range(1,7) if len({a,b,c}) == 3}


class OfficialOddsReceiptTests(unittest.TestCase):
    def test_complete_early_is_research_only(self):
        row = inspect_odds_receipt(ODDS, race_code=RACE,
                                   received_at_jst="2026-11-02T20:23:59+09:00",
                                   deadline_jst=DEADLINE)
        self.assertEqual(row["odds_entries"], 120)
        self.assertTrue(row["complete_odds_observed_before_t12"])
        self.assertFalse(row["forecast_usable"])
        self.assertFalse(row["source_immutability_verified"])

    def test_complete_late_is_not_t12(self):
        row = inspect_odds_receipt(ODDS, race_code=RACE,
                                   received_at_jst="2026-11-02T20:24:01+09:00",
                                   deadline_jst=DEADLINE)
        self.assertTrue(row["valid_120_combinations"])
        self.assertFalse(row["complete_odds_observed_before_t12"])

    def test_invalid_coverage_or_nonfinite_values(self):
        for data in ({**ODDS, "1-1-2": "9"}, {k:v for k,v in ODDS.items() if k!="1-2-3"},
                     {**ODDS, "1-2-3": "NaN"}, {**ODDS, "1-2-3": True},
                     {**ODDS, "1-2-3": 0}):
            with self.subTest(size=len(data)):
                row = inspect_odds_receipt(data, race_code=RACE,
                    received_at_jst="2026-11-02T20:20:00+09:00",
                    deadline_jst=DEADLINE)
                self.assertFalse(row["valid_120_combinations"])
                self.assertFalse(row["forecast_usable"])

    def test_bad_clock_rejected(self):
        with self.assertRaises(ValueError):
            inspect_odds_receipt(ODDS, race_code=RACE,
                received_at_jst="2026-11-02T11:20:00+00:00",deadline_jst=DEADLINE)


if __name__ == "__main__":
    unittest.main()
