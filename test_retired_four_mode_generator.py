"""Retired live four-mode generator must stay absent; historical evidence remains readable."""
import unittest
from unittest.mock import patch

import clean_four_modes


class RetiredFourModeGeneratorTests(unittest.TestCase):
    def test_live_forecast_is_not_exported(self):
        self.assertFalse(hasattr(clean_four_modes, "forecast"))

    def test_archive_reader_remains_available(self):
        self.assertTrue(callable(clean_four_modes.load_archived))

    def test_archive_missing_is_not_regenerated(self):
        from urllib.error import HTTPError
        with patch("clean_four_modes.Path.is_file", return_value=False), patch(
            "clean_four_modes.urlopen", side_effect=HTTPError("archive", 404, "not found", None, None)
        ):
            result = clean_four_modes.load_archived("202610300101")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
