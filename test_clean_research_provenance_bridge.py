import unittest
from datetime import datetime, timedelta, timezone
from clean_research_provenance_bridge import compare_capture_identity

JST=timezone(timedelta(hours=9))
CAP=datetime(2026,10,26,14,0,tzinfo=JST)
DEADLINE=CAP+timedelta(minutes=15)
RACE={"race_key":"20261026-21-01","status":"html_candidates_unverified"}
BEFORE={"race_key":"20261026-21-01","status":"research_unverified",
        "verified_preview":False,"actual_entry_verified":False,
        "raw_sha256":"a"*64,"captured_at":CAP.isoformat(),
        "start_exhibition":[{"boat_number":i} for i in range(1,7)]}

class BridgeTests(unittest.TestCase):
    def test_safe_bridge_remains_unverified(self):
        result=compare_capture_identity(RACE,BEFORE,deadline=DEADLINE)
        self.assertEqual(result["status"],"bridged_unverified")
        self.assertFalse(result["official_preview_values_equal"])
        self.assertFalse(result["actual_entry_verified"])
    def test_other_race(self):
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"race_key":"20261026-21-02"},deadline=DEADLINE)
    def test_late_capture(self):
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"captured_at":DEADLINE.isoformat()},deadline=DEADLINE)
    def test_capture_inside_two_minute_margin(self):
        too_late = DEADLINE - timedelta(seconds=90)
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"captured_at":too_late.isoformat()},deadline=DEADLINE)
    def test_capture_at_two_minute_boundary(self):
        boundary = DEADLINE - timedelta(minutes=2)
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"captured_at":boundary.isoformat()},deadline=DEADLINE)
    def test_naive_timestamp(self):
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"captured_at":CAP.replace(tzinfo=None).isoformat()},deadline=DEADLINE)
    def test_duplicate_lanes(self):
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"start_exhibition":[{"boat_number":1}]*6},deadline=DEADLINE)
    def test_flag_promotion(self):
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"verified_preview":True},deadline=DEADLINE)

if __name__=="__main__":
    unittest.main()
