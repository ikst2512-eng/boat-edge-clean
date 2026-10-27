import unittest
from datetime import datetime
from unittest.mock import patch
import clean_schedule as s


class ScheduleTests(unittest.TestCase):
    def test_parses_valid_schedule(self):
        row={"レースコード":"202610270101","電話投票締切予定":"15:22"}
        o=s.parse_schedule("20261027",[row],datetime.now(s.JST))
        self.assertEqual(o["races"][0]["deadline_jst"][:16],"2026-10-27T15:22")
        self.assertFalse(o["results_confirmed"])

    def test_duplicate_rejected(self):
        row={"レースコード":"202610270101","電話投票締切予定":"1522"}
        with self.assertRaises(ValueError):
            s.parse_schedule("20261027",[row,row],datetime.now(s.JST))

    def test_invalid_date_without_network(self):
        self.assertEqual(s.clean_schedule("20261340")[0],400)

    def test_upstream_failure_no_old_fallback(self):
        with patch.object(s,"read_rows",side_effect=TimeoutError()):
            status,data=s.clean_schedule("20261027")
        self.assertEqual((status,data["status"]),(503,"source_unavailable"))


if __name__=="__main__":
    unittest.main()
