"""Strict temporal split tests; fixtures do not claim observed hit rates."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from hole_strict_temporal_holdout import later_date_codes

class TemporalSplitTests(unittest.TestCase):
    def test_excludes_same_and_earlier_dates(self):
        training=["202610300101","202611010101"]
        pool=["202610290101","202610300102","202611010202",
              "202611020101","202611030101"]
        with patch("hole_strict_temporal_holdout.holdout_codes", return_value=pool):
            self.assertEqual(later_date_codes(Path("."),training),pool[-2:])

    def test_no_training_has_no_holdout(self):
        self.assertEqual(later_date_codes(Path("."),[]),[])

    def test_limit_and_same_date_exclusion(self):
        with patch("hole_strict_temporal_holdout.holdout_codes",
                   return_value=["202611020101","202611020102","202611030101"]):
            self.assertEqual(later_date_codes(Path("."),["202611010101"],1),
                             ["202611020101"])

if __name__=="__main__":
    unittest.main()
