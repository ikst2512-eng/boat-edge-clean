"""Check same-day, future-only V133 probe selection without any network access."""
import unittest
from datetime import datetime
from scripts.probe_live_v133_real import upcoming, JST


class V133OneShotProbeContract(unittest.TestCase):
    def test_actual_schedule_format_only_selects_upcoming_not_completed(self):
        now = datetime(2026, 11, 14, 19, 27, tzinfo=JST)
        schedule = {
            "date": "2026-11-14",
            "venues": [
                {"jcd": "07", "races": [
                    {"race_no": 9, "deadline": "19:00"},
                    {"race_no": 10, "deadline": "19:36"},
                    {"race_no": 11, "deadline": "20:07"},
                ]},
                {"jcd": "24", "races": [
                    {"race_no": 10, "deadline": "19:47"},
                    {"race_no": 12, "deadline": "20:45"},
                ]},
                {"jcd": "99", "races": [{"race_no": 10, "deadline": "19:30"}]},
            ],
        }
        candidates = upcoming(schedule, now)
        self.assertEqual(len(candidates), 2)
        self.assertEqual([(x[2], x[3]) for x in candidates], [("07", 10), ("24", 10)])

    def test_wrong_date_and_no_upcoming_never_generate_backfill(self):
        now = datetime(2026, 11, 14, 22, 0, tzinfo=JST)
        self.assertEqual(upcoming({"date": "2026-11-13", "venues": []}, now), [])
        self.assertEqual(upcoming({"date": "2026-11-14", "venues": [
            {"jcd": "07", "races": [{"race_no": 10, "deadline": "19:36"}]}
        ]}, now), [])


if __name__ == "__main__":
    unittest.main()
