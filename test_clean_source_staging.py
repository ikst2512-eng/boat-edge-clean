import copy
import unittest
from clean_source_staging import validate_staged_race


def sample():
    return {
        "race_key": "20261027-12-01",
        "source_url": "https://www.boatrace.jp/owpc/pc/race/racelist?hd=20261027&jcd=12&rno=1",
        "fetched_at": "2026-10-27T08:00:00+09:00",
        "racers": [{"lane": i, "name": f"fixture{i}"} for i in range(1, 7)],
        "results_seen": False, "unlock": False, "scoring": False,
    }


class RaceSourceStagingTest(unittest.TestCase):
    def test_valid_fixture_only_stages(self):
        self.assertEqual(validate_staged_race(sample())["status"], "staged_unpublished")

    def test_rejects_cross_race(self):
        x = sample()
        x["source_url"] = x["source_url"].replace("rno=1", "rno=2")
        with self.assertRaisesRegex(ValueError, "cross-race"):
            validate_staged_race(x)

    def test_rejects_untrusted_source(self):
        x = sample()
        x["source_url"] = x["source_url"].replace("www.boatrace.jp", "boatrace.jp.evil.example")
        with self.assertRaises(ValueError):
            validate_staged_race(x)

    def test_rejects_duplicate_lane(self):
        x = sample()
        x["racers"][-1]["lane"] = 1
        with self.assertRaises(ValueError):
            validate_staged_race(x)

    def test_rejects_missing_lane(self):
        x = sample()
        x["racers"].pop()
        with self.assertRaises(ValueError):
            validate_staged_race(x)

    def test_rejects_results_guard(self):
        for field in ("results_seen", "unlock", "scoring"):
            x = sample()
            x[field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_staged_race(x)

    def test_rejects_naive_timestamp(self):
        x = sample()
        x["fetched_at"] = "2026-10-27T08:00:00"
        with self.assertRaises(ValueError):
            validate_staged_race(x)


if __name__ == "__main__":
    unittest.main()
