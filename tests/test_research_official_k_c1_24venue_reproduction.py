"""Synthetic, network-free safety and precision tests for primary 24-venue C1 reproduction."""
import csv
import tempfile
import unittest
from pathlib import Path

from scripts.research_official_k_c1_24venue_reproduction import audit, frozen_baseline
from scripts.research_official_k_one_day_compare import parse_k


def write_baseline(p: Path):
    fields = ["venue_code", "venue_name", "c1_win_pct", "start_date", "end_date"]
    with p.open("w", encoding="utf-8", newline="") as fd:
        w = csv.DictWriter(fd, fieldnames=fields)
        w.writeheader()
        w.writerows(
            {"venue_code": f"{n:02d}", "venue_name": f"場{n:02d}",
             "c1_win_pct": "50.0", "start_date": "2026-08-01",
             "end_date": "2026-10-31"} for n in range(1, 25)
        )


def unsettled_k_text(include_not_established=True):
    text = [
        "24KBGN",
        "   1R       予選                H1800m  晴  風  東  8m  波  7cm",
        "  着 艇 登番 ｽﾀｰﾄﾀｲﾐﾝｸ ﾚｰｽﾀｲﾑ                  ",
    ]
    text.extend(
        f"  F   {i} 4966 Sample 72   36  7.00   {i}   F0.01       .  ."
        for i in range(1, 7)
    )
    if include_not_established:
        text.append("  レース不成立")
    return "\n".join(text) + "\n"


class PrimaryVenueRateTests(unittest.TestCase):
    def test_24_venue_precise_fixed_period(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "baseline.csv"
            write_baseline(p)
            self.assertEqual(len(frozen_baseline(p)), 24)
            p.write_text(p.read_text().replace("2026-10-31", "2026-11-01"))
            with self.assertRaisesRegex(ValueError, "window_mismatch"):
                frozen_baseline(p)

    def test_missing_daily_K_is_not_silently_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            p = path / "baseline.csv"
            write_baseline(p)
            with self.assertRaisesRegex(FileNotFoundError, "official_K_missing"):
                audit(path / "empty", p)

    def test_cancelled_race_accepted_only_with_explicit_mark_and_option(self):
        x = unsettled_k_text()
        with self.assertRaisesRegex(ValueError, "official_winner_missing"):
            parse_k(x, day="20260807", expected_races=1)
        result = parse_k(x, day="20260807", expected_races=1, allow_unsettled=True)
        self.assertTrue(result["202608072401"]["unsettled"])
        self.assertEqual([x["status"] for x in result["202608072401"]["entries"]],
                         ["F"] * 6)
        with self.assertRaisesRegex(ValueError, "official_winner_missing"):
            parse_k(unsettled_k_text(False), day="20260807",
                    expected_races=1, allow_unsettled=True)

    def test_reject_duplicate_or_invalid_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "baseline.csv"
            write_baseline(p)
            raw = p.read_text()
            p.write_text(raw.replace("24,場24", "23,場24"))
            with self.assertRaisesRegex(ValueError, "24_venue_baseline_invalid"):
                frozen_baseline(p)

    def test_reject_excess_official_precision(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "baseline.csv"
            write_baseline(p)
            p.write_text(p.read_text().replace("50.0", "50.25", 1))
            with self.assertRaisesRegex(ValueError, "precision_invalid"):
                frozen_baseline(p)


if __name__ == "__main__":
    unittest.main()
