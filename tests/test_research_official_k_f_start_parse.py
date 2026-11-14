"""Official K F0.xx format regression: never silently omit the actual course/ST."""
import csv
import io
import unittest

from scripts.research_official_k_one_day_compare import COURSE, compare, git_blob_sha


class OfficialFStartTests(unittest.TestCase):
    def test_f0_start_course_is_parsed(self):
        row = " 55   12  6.94   1   F0.01      .  . "
        found = COURSE.search(row)
        self.assertIsNotNone(found)
        self.assertEqual(found.group(1), "1")
        self.assertEqual(found.group(2), "F0.01")
        self.assertEqual(COURSE.search(row.replace("F0.01", "F.04")).group(2), "F.04")
        self.assertEqual(COURSE.search(row.replace("F0.01", "L0.01")).group(2), "L0.01")

    def fixture(self):
        columns = ["レースコード", "1着_艇番", "決まり手",
                   "風速(m)", "波の高さ(cm)"]
        columns += [f"{i}着_艇番" for i in range(1, 7)]
        columns += [f"{i}コース_艇番" for i in range(1, 7)]
        columns += [f"{i}コース_スタートタイミング" for i in range(1, 7)]
        columns += [f"{i}コース_F" for i in range(1, 7)]
        row = {"レースコード": "202608010301", "1着_艇番": "1",
               "決まり手": "逃げ", "風速(m)": "3", "波の高さ(cm)": "2"}
        for i in range(1, 7):
            row[f"{i}着_艇番"] = str(i) if i <= 5 else ""
            row[f"{i}コース_艇番"] = str(i)
            row[f"{i}コース_スタートタイミング"] = "0.15" if i <= 5 else "-0.01"
            row[f"{i}コース_F"] = "F" if i == 6 else ""
        io_stream = io.StringIO(newline="")
        writer = csv.DictWriter(io_stream, fieldnames=columns)
        writer.writeheader()
        writer.writerow(row)
        entries = [
            {"boat": i, "status": f"{i:02d}" if i <= 5 else "F",
             "course": i, "st": "0.15" if i <= 5 else "F0.01"}
            for i in range(1, 7)
        ]
        official = {"202608010301": {
            "venue": "03", "entries": entries, "method": "逃げ", "wind_m": 3,
            "wave_cm": 2,
        }}
        return official, row, columns

    def test_f_actual_course_start_and_mark_are_checked(self):
        official, row, columns = self.fixture()
        buf = io.StringIO(newline="")
        w = csv.DictWriter(buf, fieldnames=columns)
        w.writeheader()
        w.writerow(row)
        raw = buf.getvalue().encode("utf-8")
        result = compare(official, raw, git_blob_sha(raw), day="20260801")
        self.assertEqual(result["field_discrepancy_count"], 0)
        self.assertEqual(result["field_match_counts"]["course6"], 1)
        self.assertEqual(result["field_match_counts"]["fmark6"], 1)
        self.assertEqual(result["field_match_counts"]["st6"], 1)
        self.assertEqual(result["course_not_fully_comparable_race_codes"], [])

    def test_f_st_mismatch_is_not_silent(self):
        official, row, columns = self.fixture()
        row["6コース_スタートタイミング"] = "-0.03"
        buf = io.StringIO(newline="")
        w = csv.DictWriter(buf, fieldnames=columns)
        w.writeheader()
        w.writerow(row)
        raw = buf.getvalue().encode("utf-8")
        result = compare(official, raw, git_blob_sha(raw), day="20260801")
        self.assertIn(
            {"race_code": "202608010301", "field": "st6"},
            result["field_discrepancies"],
        )


if __name__ == "__main__":
    unittest.main()
