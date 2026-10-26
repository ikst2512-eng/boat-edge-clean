import unittest
from datetime import datetime, timedelta, timezone
from clean_research_provenance_bridge import compare_capture_identity

JST=timezone(timedelta(hours=9))
CAP=datetime(2026,10,26,14,0,tzinfo=JST)
DEADLINE=CAP+timedelta(minutes=15)
RACE={"race_key":"20261026-21-01","status":"html_candidates_unverified",
      "official_provenance_verified":False,
      "racers":[{"lane":i,"registration":f"{4000+i}"} for i in range(1,7)]}
BEFORE={"race_key":"20261026-21-01","status":"research_unverified",
        "verified_preview":False,"actual_entry_verified":False,
        "results_seen":False,"unlock":False,"scoring":False,
        "raw_sha256":"a"*64,"captured_at":CAP.isoformat(),
        "start_exhibition":[{"boat_number":i,"exhibition_course":i,"exhibition_st":0.12} for i in range(1,7)]}

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
    def test_utc_capture_offset_rejected(self):
        utc = CAP.astimezone(timezone.utc)
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"captured_at":utc.isoformat()},deadline=DEADLINE)
    def test_utc_deadline_offset_rejected(self):
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,BEFORE,deadline=DEADLINE.astimezone(timezone.utc))
    def test_invalid_calendar_date(self):
        with self.assertRaises(ValueError):
            compare_capture_identity({**RACE,"race_key":"20260230-21-01"},
                                     {**BEFORE,"race_key":"20260230-21-01"},deadline=DEADLINE)
    def test_non_dict_six_boat_row(self):
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"start_exhibition":[None]+[{"boat_number":i} for i in range(2,7)]},deadline=DEADLINE)
    def test_boolean_boat_number(self):
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"start_exhibition":[{"boat_number":True}]+[{"boat_number":i} for i in range(2,7)]},deadline=DEADLINE)
    def test_missing_racelist_racer(self):
        with self.assertRaises(ValueError):
            compare_capture_identity({**RACE,"racers":RACE["racers"][:5]},BEFORE,deadline=DEADLINE)
    def test_duplicate_racelist_registration(self):
        racers=[dict(x) for x in RACE["racers"]]
        racers[5]["registration"]=racers[0]["registration"]
        with self.assertRaises(ValueError):
            compare_capture_identity({**RACE,"racers":racers},BEFORE,deadline=DEADLINE)
    def test_unsafe_racelist_promotion(self):
        with self.assertRaises(ValueError):
            compare_capture_identity({**RACE,"official_provenance_verified":True},BEFORE,deadline=DEADLINE)
    def test_duplicate_exhibition_course(self):
        rows=[dict(x) for x in BEFORE["start_exhibition"]]
        rows[5]["exhibition_course"]=1
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"start_exhibition":rows},deadline=DEADLINE)
    def test_nonfinite_exhibition_st(self):
        rows=[dict(x) for x in BEFORE["start_exhibition"]]
        rows[0]["exhibition_st"]=float("nan")
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"start_exhibition":rows},deadline=DEADLINE)
    def test_missing_exhibition_st(self):
        rows=[dict(x) for x in BEFORE["start_exhibition"]]
        del rows[0]["exhibition_st"]
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"start_exhibition":rows},deadline=DEADLINE)
    def test_scoring_flag_cannot_unlock(self):
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,{**BEFORE,"scoring":True},deadline=DEADLINE)
    def test_missing_results_lock_flag(self):
        unsafe=dict(BEFORE)
        del unsafe["results_seen"]
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,unsafe,deadline=DEADLINE)
    def test_shuffled_exhibition_entry_is_valid_research(self):
        rows=[dict(x) for x in BEFORE["start_exhibition"]]
        rows[0]["exhibition_course"],rows[1]["exhibition_course"]=2,1
        result=compare_capture_identity(RACE,{**BEFORE,"start_exhibition":rows},deadline=DEADLINE)
        self.assertEqual(result["status"],"bridged_unverified")
        self.assertFalse(result["actual_entry_verified"])
    def test_pr15_parser_with_matching_receipt(self):
        parser_only={k:v for k,v in BEFORE.items() if k not in ("results_seen","unlock","scoring")}
        receipt={"status":"raw_html_only","race_key":BEFORE["race_key"],
                 "sha256":BEFORE["raw_sha256"],"fetched_at":BEFORE["captured_at"],
                 "verified_preview":False,"actual_entry_verified":False,
                 "results_seen":False,"unlock":False,"scoring":False}
        result=compare_capture_identity(RACE,parser_only,deadline=DEADLINE,official_receipt=receipt)
        self.assertEqual(result["status"],"bridged_unverified")
    def test_receipt_hash_mismatch(self):
        receipt={"status":"raw_html_only","race_key":BEFORE["race_key"],
                 "sha256":"b"*64,"fetched_at":BEFORE["captured_at"],
                 "verified_preview":False,"actual_entry_verified":False,
                 "results_seen":False,"unlock":False,"scoring":False}
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,BEFORE,deadline=DEADLINE,official_receipt=receipt)
    def test_receipt_unlock_rejected(self):
        receipt={"status":"raw_html_only","race_key":BEFORE["race_key"],
                 "sha256":BEFORE["raw_sha256"],"fetched_at":BEFORE["captured_at"],
                 "verified_preview":False,"actual_entry_verified":False,
                 "results_seen":False,"unlock":True,"scoring":False}
        with self.assertRaises(ValueError):
            compare_capture_identity(RACE,BEFORE,deadline=DEADLINE,official_receipt=receipt)
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
