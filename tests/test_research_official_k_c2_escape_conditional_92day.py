"""Off-line research-only unit tests, never mutate forecasts or main."""
import unittest
from scripts.research_official_k_c2_escape_conditional_92day import (
    race_outcome, wind_bin, public_counts, verify_original_zip,
)
from collections import Counter
from tempfile import TemporaryDirectory
from pathlib import Path

def race(winner=1, method="逃げ", special=None, missing_course=None):
    special=special or {}
    entries=[]
    for course in range(1,7):
        entries.append({
            "course": None if course == missing_course else course,
            "boat": course,
            "status": special.get(course, "01" if winner==course else f"{course+1:02d}"),
            "st": "0.15",
        })
    return {"entries": entries, "method": method, "unsettled": False}

class TestKConditional(unittest.TestCase):
    def test_one_course_escape(self):
        x=race_outcome(race())
        self.assertEqual(x["c1_escapement"], 1)
        self.assertEqual(x["c2_sashi"], 0)
        self.assertEqual(x["c1_win"], 1)

    def test_one_course_non_escape_win(self):
        x=race_outcome(race(method="抜き"))
        self.assertEqual((x["c1_win"],x["c1_escapement"]),(1,0))

    def test_two_course_sashi(self):
        x=race_outcome(race(winner=2,method="差し"))
        self.assertEqual((x["c2_win"], x["c2_sashi"]), (1, 1))
        self.assertEqual(x["c1_escapement"],0)

    def test_three_and_four_makuri(self):
        x=race_outcome(race(winner=3,method="まくり"))
        y=race_outcome(race(winner=4,method="まくり"))
        self.assertEqual((x["c3_makuri"],x["c4_makuri"]), (1,0))
        self.assertEqual((y["c3_makuri"],y["c4_makuri"]), (0,1))

    def test_missing_actual_course_denied(self):
        self.assertIsNone(race_outcome(race(missing_course=4)))

    def test_c1_invalid_denied(self):
        self.assertIsNone(race_outcome(race(winner=2,method="差し",special={1:"S1"})))

    def test_c2_f_denied(self):
        self.assertIsNone(race_outcome(race(special={2:"F"})))

    def test_unsettled_denied(self):
        d=race();d["unsettled"]=True
        self.assertIsNone(race_outcome(d))

    def test_wind_band_boundaries(self):
        self.assertEqual([wind_bin(x) for x in (0,2,3,4,5,10)],
                         ["0-2m","0-2m","3-4m","3-4m","5m+","5m+"])
        with self.assertRaises(ValueError): wind_bin(-1)

    def test_original_zip_rejects_mismatching_file(self):
        with TemporaryDirectory() as d:
            f = Path(d) / "official.zip"
            f.write_bytes(b"fake_zip_with_matching_embedded_manifest_impossible")
            with self.assertRaisesRegex(ValueError, "artifact_size_not_frozen"):
                verify_original_zip(f)

    def test_original_zip_rejects_missing_file(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "missing_or_symlink"):
                verify_original_zip(Path(d) / "missing.zip")

    def test_original_zip_rejects_same_size_forgery(self):
        with TemporaryDirectory() as d:
            f = Path(d) / "official.zip"
            with f.open("wb") as out:
                out.truncate(3398466)
            with self.assertRaisesRegex(ValueError, "SHA_does_not_match"):
                verify_original_zip(f)

    def test_original_zip_rejects_symlink(self):
        with TemporaryDirectory() as d:
            source = Path(d) / "source.zip"
            source.write_bytes(b"not_the_archive")
            linked = Path(d) / "linked.zip"
            linked.symlink_to(source)
            with self.assertRaisesRegex(ValueError, "missing_or_symlink"):
                verify_original_zip(linked)

    def test_zero_denominator_not_false_zero(self):
        self.assertIsNone(public_counts(Counter())["c2_sashi"]["percent"])
        self.assertEqual(public_counts(Counter(eligible=10,c2_sashi=1))["c2_sashi"]["percent"],10.0)

if __name__ == "__main__":
    unittest.main()
