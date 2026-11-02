import unittest
from scripts.inspect_official_racelist_registrations import inspect_six_registrations

IDS = ["4180", "5112", "4786", "4159", "4663", "5087"]
FULL = "１２３４５６"

def original_like(rows=6, duplicate=False):
    fragments = []
    for i in range(rows):
        lane = i + 1
        registration = IDS[0] if duplicate and i == 5 else IDS[i]
        fragments.append(
            f'<tr><td class="is-boatColor{lane} is-fs14" rowspan="4">{FULL[i]}</td>'
            f'<td rowspan="4"><a href="/owpc/pc/data/racersearch/profile?toban={registration}">'
            f'<img src="/racerphoto/{registration}.jpg" /></a></td></tr>'
        )
    return ('<?xml version="1.0"?><html>' + ''.join(fragments) + '</html>').encode()

class SixRacerOriginalTests(unittest.TestCase):
    def test_six_distinct_registration_pairs(self):
        result = inspect_six_registrations(original_like())
        self.assertTrue(result["six_racers_verified"])
        self.assertEqual(result["registrations_by_lane"], {str(i+1): v for i,v in enumerate(IDS)})
        self.assertFalse(result["entry_verified"])
        self.assertFalse(result["forecast_usable"])

    def test_five_rows_fail_closed(self):
        self.assertFalse(inspect_six_registrations(original_like(5))["six_racers_verified"])

    def test_duplicate_registration_fail_closed(self):
        self.assertFalse(inspect_six_registrations(original_like(duplicate=True))["six_racers_verified"])

    def test_wrong_visual_lane_rejected(self):
        raw = original_like().replace(b'>\xef\xbc\x91</td>', b'>\xef\xbc\x92</td>', 1)
        with self.assertRaises(ValueError):
            inspect_six_registrations(raw)

    def test_empty_shell_never_certifies(self):
        self.assertFalse(inspect_six_registrations(b'<html><body></body></html>')["six_racers_verified"])
