"""Focused regression for F-denominator audit: no network or predictions."""
import csv
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from scripts.research_official_c1_rate_gap_f_audit import audit, FOCUS, START, END


def fixture(directory: Path):
    base = directory / "official.csv"
    fields = ["venue_code", "venue_name", "c1_win_pct", "start_date", "end_date"]
    with base.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows({"venue_code": f"{i:02d}", "venue_name": str(i),
                     "c1_win_pct": 80, "start_date": str(START), "end_date": str(END)}
                    for i in range(1, 25))
    root = directory / "src"
    fields = ["レースコード", "1着_艇番", "決まり手", "風速(m)", "風向",
              "1コース_F", "1コース_スタートタイミング"] + [
                  f"{i}コース_艇番" for i in range(1, 7)
              ] + [f"{i}着_艇番" for i in range(2, 7)]
    rows_day = []
    for code in FOCUS:
        for race, winner, fmark, st in [(1, "1", "", "0.13"), (2, "2", "F", "-0.01")]:
            row = {"レースコード": f"20260801{code}{race:02d}",
                   "1着_艇番": winner, "決まり手": "逃　げ" if winner == "1" else "恵まれ",
                   "風速(m)": "3", "風向": "2",
                   "1コース_F": fmark, "1コース_スタートタイミング": st}
            row.update({f"{i}コース_艇番": str(i) for i in range(1, 7)})
            row.update({f"{i}着_艇番": str(i) if winner == "1" else
                        (str(i + 1) if i <= 5 else "") for i in range(1, 7)})
            rows_day.append(row)
    for offset in range((END-START).days+1):
        date = START + dt.timedelta(days=offset)
        path = root / f"data/results/realtime/{date:%Y}/{date:%m}/{date:%d}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            if date == START:
                w.writerows(rows_day)
    return root, base


class TestFStudy(unittest.TestCase):
    def test_f_removal_is_partial_not_official_certification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, base = fixture(Path(tmp))
            report = audit(root, base)
            self.assertEqual(len(report["source_manifest"]), 92)
            self.assertEqual(len(report["venues"]), 4)
            self.assertFalse(report["approved_for_forecasting"])
            self.assertFalse(report["official_primary_result_rows_reconciled"])
            for v in report["venues"]:
                self.assertEqual([v["raw_rows"], v["study_eligible"], v["c1_wins"], v["c1_F_mark"]], [2, 2, 1, 1])
                self.assertEqual(v["study_c1_win_pct"], 50.0)
                self.assertEqual(v["excluding_c1_F_c1_win_pct"], 100.0)
                self.assertEqual(v["c1_ranked_finish_n"], 1)
                self.assertEqual(v["c1_unranked_nonF"], 0)
                self.assertEqual(v["only_c1_with_ranked_finish_win_pct"], 100.0)
                self.assertEqual(v["remaining_gap_after_ranked_finish_subset_pt"], -20.0)
                self.assertEqual(v["original_gap_official_minus_study_pt"], 30.0)
                self.assertEqual(v["remaining_gap_after_F_exclusion_pt"], -20.0)
                self.assertFalse(v["cause_established"])

    def test_missing_day_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, base = fixture(Path(tmp))
            (root / "data/results/realtime/2026/09/01.csv").unlink()
            with self.assertRaisesRegex(FileNotFoundError, "missing_or_symlink_source"):
                audit(root, base)

    def test_bad_official_period_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, base = fixture(Path(tmp))
            text = base.read_text()
            base.write_text(text.replace("2026-10-31", "2026-09-30"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "baseline_period_mismatch"):
                audit(root, base)

    def test_duplicate_race_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, base = fixture(Path(tmp))
            file = root / "data/results/realtime/2026/08/01.csv"
            with file.open(encoding="utf-8") as f:
                allrows = list(csv.reader(f))
            with file.open("a", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow(allrows[1])
            with self.assertRaisesRegex(ValueError, "duplicate_race_code"):
                audit(root, base)

    def test_wrong_source_day_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, base = fixture(Path(tmp))
            file = root / "data/results/realtime/2026/08/01.csv"
            file.write_text(file.read_text().replace("202608010301", "202608020301"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "date_mismatch"):
                audit(root, base)


if __name__ == "__main__":
    unittest.main()
