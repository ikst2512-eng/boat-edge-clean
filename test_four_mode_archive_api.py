import json
import tempfile
import unittest
from pathlib import Path
from four_mode_archive_api import archived_four_modes


def sample(code):
    return {
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "race_code": code,
        "generated_at_jst": "2026-10-28T10:00:00+09:00",
        "deadline_jst": "2026-10-28T10:30:00+09:00",
        "modes": {name: {"tickets": [{"combo": "1-2-3", "p": 4.5}],
                         "target_hit_rate_pct": 40} for name in ("hit", "balance", "hole", "narrow")},
    }


class ArchiveApiTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        (self.root / "four_mode_forecasts").mkdir()
        self.code = "202610280101"

    def tearDown(self):
        self.dir.cleanup()

    def save(self, record):
        (self.root / "four_mode_forecasts" / (self.code + ".json")).write_text(
            json.dumps(record), encoding="utf-8")

    def test_missing_archive_does_not_generate_prediction(self):
        code, body = archived_four_modes(self.code, self.root)
        self.assertEqual(code, 404)
        self.assertEqual(body["status"], "not_archived")

    def test_exposes_all_four_modes_without_formal_claim(self):
        self.save(sample(self.code))
        status, result = archived_four_modes(self.code, self.root)
        self.assertEqual(status, 200)
        self.assertEqual(list(result["modes"]), ["hit", "balance", "hole", "narrow"])
        self.assertFalse(result["production_forecast"])
        self.assertFalse(result["verified_first_git_add"])
        self.assertIsNone(result["modes"]["hit"]["actual_hit_rate_pct"])

    def test_rejects_late_forecast(self):
        data = sample(self.code)
        data["generated_at_jst"] = "2026-10-28T10:35:00+09:00"
        self.save(data)
        self.assertEqual(archived_four_modes(self.code, self.root)[0], 422)

    def test_rejects_bad_ticket(self):
        data = sample(self.code)
        data["modes"]["hit"]["tickets"][0]["combo"] = "1-1-2"
        self.save(data)
        self.assertEqual(archived_four_modes(self.code, self.root)[0], 422)

    def test_invalid_race_key(self):
        self.assertEqual(archived_four_modes("../etc/passwd", self.root)[0], 422)


if __name__ == "__main__":
    unittest.main()
