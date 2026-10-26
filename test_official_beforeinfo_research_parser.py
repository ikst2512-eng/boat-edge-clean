import unittest
from official_beforeinfo_research_parser import research_start_exhibition

def fixture(order=(1, 2, 3, 4, 5, 6), st=".08"):
    return ("<html><body>" + "".join(
        '<div class="table1_boatImage1"><span class="table1_boatImage1Number">' +
        str(num) + '</span><span class="table1_boatImage1Time">' + st +
        '</span></div>' for num in order) + "</body></html>").encode()

class ResearchParserTests(unittest.TestCase):
    def test_six_boats_course_distinct_from_number(self):
        p = research_start_exhibition(fixture((2,1,3,4,6,5)))
        self.assertEqual([r["boat_number"] for r in p["start_exhibition"]], [2,1,3,4,6,5])
        self.assertEqual([r["exhibition_course"] for r in p["start_exhibition"]], list(range(1,7)))
        self.assertEqual(p["start_exhibition"][0]["exhibition_st"], .08)
        self.assertFalse(p["actual_entry_verified"])
        self.assertEqual(p["status"], "research_unverified")

    def test_st_forms(self):
        for st, target in (("F.04", -.04), ("0.08", .08), (".08", .08)):
            self.assertAlmostEqual(research_start_exhibition(fixture(st=st))["start_exhibition"][0]["exhibition_st"], target)

    def test_missing_duplicate_or_bad_st_rejected(self):
        for raw in (fixture((1,2,3,4,5)), fixture((1,2,3,4,5,5)),
                    fixture(st=""), fixture(st="L.08"), fixture(st="9.99")):
            with self.assertRaises(ValueError):
                research_start_exhibition(raw)

if __name__ == "__main__":
    unittest.main()
