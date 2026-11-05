"""Safety regressions for strictly retrospective wind-by-course research."""
import csv
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from scripts.research_venue_wind_outcomes import classify, export, study, wilson


DAY = dt.date(2026, 10, 1)


def record(code="202610010101", wind="1", finish=None, courses=None, decision="逃　げ", f=""):
    row = {"レースコード": code, "風速(m)": wind, "決まり手": decision}
    for i, boat in enumerate(courses or [1, 2, 3, 4, 5, 6], 1):
        row[f"{i}コース_艇番"] = str(boat)
        row[f"{i}コース_F"] = f if i == 1 else ""
    for i, boat in enumerate(finish or [1, 2, 3, 4, 5, 6], 1):
        row[f"{i}着_艇番"] = str(boat)
    return row


class DescriptiveEvidenceTests(unittest.TestCase):
    def test_correct_course_not_lane_and_escape_normalization(self):
        out, problem = classify(record(courses=[2, 1, 3, 4, 5, 6]), DAY, set())
        self.assertIsNone(problem)
        self.assertEqual(out, (0, 0, 0, 1))

    def test_wind_bucket_boundaries(self):
        for wind, bucket in [("2", 0), ("3", 1), ("4", 1), ("5", 2)]:
            self.assertEqual(classify(record(wind=wind), DAY, set())[0][1], bucket)

    def test_reject_missing_wind_or_incomplete_six_finish(self):
        self.assertEqual(classify(record(wind=""), DAY, set())[1], "invalid_wind")
        r = record()
        r["6着_艇番"] = ""
        self.assertEqual(classify(r, DAY, set())[1], "incomplete_finish")

    def test_reject_flying_bad_course_and_duplicates(self):
        self.assertEqual(classify(record(f="F"), DAY, set())[1], "flying")
        self.assertEqual(classify(record(courses=[1, 1, 3, 4, 5, 6]), DAY, set())[1], "incomplete_course")
        seen = set()
        self.assertIsNone(classify(record(), DAY, seen)[1])
        self.assertEqual(classify(record(), DAY, seen)[1], "duplicate")

    def test_missing_day_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                study(Path(tmp), DAY, DAY)

    def test_one_day_manifest_and_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / "data/results/realtime/2026/10/01.csv"
            file.parent.mkdir(parents=True)
            data = [record(), record(code="202610010102", wind="5", finish=[2, 1, 3, 4, 5, 6], decision="差し")]
            with file.open("w", encoding="utf-8", newline="") as fd:
                writer = csv.DictWriter(fd, fieldnames=list(data[0]))
                writer.writeheader()
                writer.writerows(data)
            counts, rejected, sources = study(root, DAY, DAY)
            self.assertEqual(rejected["valid"], 2)
            self.assertEqual(counts[0][0], [1, 1, 1])
            self.assertEqual(counts[0][2], [1, 0, 0])
            self.assertEqual(len(sources[0]["source_sha256"]), 64)
            dest = root / "report.csv"
            export(counts, dest)
            with dest.open(encoding="utf-8-sig") as fd:
                self.assertEqual(len(list(csv.DictReader(fd))), 72)
            self.assertEqual(wilson(1, 1)[1], "100.0")


if __name__ == "__main__":
    unittest.main()
