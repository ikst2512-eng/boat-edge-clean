"""Research archive integrity only: wind-direction counts, never model approval."""
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "docs" / "research"
SUMMARY = ROOT / "venue_wind_202608_202610_24venues_research_only.json"
OCTOBER_PARTS = [
    ROOT / "venue_wind_202610_part01_11.json",
    ROOT / "venue_wind_202610_part12_22.json",
    ROOT / "venue_wind_202610_part23_31.json",
]
BANDS = ("0-2m", "3-4m", "5m+")


def count_directions(d):
    assert isinstance(d, dict)
    assert all(isinstance(v, int) and v >= 0 for v in d.values())
    assert all(k in ("", "1", "2", "3", "4", "5", "6", "7", "8")
               for k in d)
    return sum(d.values())


class VenueWindAggregateReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with SUMMARY.open(encoding="utf-8") as f:
            cls.data = json.load(f)

    def test_source_scope_and_research_only(self):
        d = self.data
        self.assertEqual(len(d["venues"]), 24)
        self.assertEqual(d["eligible_unique_races"], 13970)
        self.assertEqual(d["input_rows"], 14109)
        self.assertEqual(len(d["source_hashes_per_day"]), 92)
        self.assertFalse(d["official_binary_reconciliation"])
        self.assertEqual(d["status"], "research_observational_only")
        self.assertEqual(d["wind_direction_reconciliation"]["restored_race_count"], 4663)

    def test_every_national_venue_and_month_direction_count_matches_n(self):
        d = self.data
        venue_n = Counter()
        venue_dir = {band: Counter() for band in BANDS}
        for v in d["venues"]:
            self.assertEqual(set(v["by_month"]), {"2026-08", "2026-09", "2026-10"})
            for band in BANDS:
                overall = v["wind_bands"][band]
                self.assertEqual(count_directions(overall["wind_direction_counts"]), overall["n"])
                by_month_n = 0
                by_month_dir = Counter()
                for group in v["by_month"].values():
                    b = group[band]
                    self.assertEqual(count_directions(b["wind_direction_counts"]), b["n"])
                    by_month_n += b["n"]
                    by_month_dir.update(b["wind_direction_counts"])
                self.assertEqual(by_month_n, overall["n"])
                self.assertEqual(dict(by_month_dir), {
                    k: value for k, value in overall["wind_direction_counts"].items()
                    if value > 0
                })
                venue_n[band] += overall["n"]
                venue_dir[band].update(overall["wind_direction_counts"])
        for band in BANDS:
            national = d["national"][band]
            self.assertEqual(national["n"], venue_n[band])
            self.assertEqual(count_directions(national["wind_direction_counts"]),
                             national["n"])
            self.assertEqual(dict(venue_dir[band]), {
                k: value for k, value in national["wind_direction_counts"].items()
                if value > 0
            })
        self.assertEqual(sum(venue_n.values()), 13970)

    def test_october_direction_parts_match_all_venue_month_bins(self):
        observed = Counter()
        october_group_n = Counter()
        total = 0
        for path in OCTOBER_PARTS:
            with path.open(encoding="utf-8") as f:
                part = json.load(f)
            total += part["accepted"]
            for key, values in part["stats"].items():
                october_group_n[key] += values["n"]
            for key, n in part["wind_directions"].items():
                bits = key.split("|", 2)
                self.assertEqual(len(bits), 3)
                self.assertIn(bits[1], BANDS)
                self.assertIn(bits[2], ("", "1", "2", "3", "4", "5", "6", "7", "8"))
                observed[key] += n
        self.assertEqual(total, 4663)
        self.assertEqual(sum(october_group_n.values()), total)
        self.assertEqual(sum(observed.values()), total)
        for v in self.data["venues"]:
            for band in BANDS:
                key = v["code"] + "|" + band
                group = v["by_month"]["2026-10"][band]
                self.assertEqual(group["n"], october_group_n[key])
                for direction, n in group["wind_direction_counts"].items():
                    self.assertEqual(n, observed[key + "|" + direction])
                self.assertEqual(sum(observed[k] for k in observed if k.startswith(key + "|")),
                                 group["n"])


if __name__ == "__main__":
    unittest.main()
