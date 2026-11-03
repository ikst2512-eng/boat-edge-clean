import unittest
from entry_waku10_pilot import prepare_waku10_pilot,PROTOCOL
from test_entry_course_late_preview import inputs,FROZEN
from test_entry_waku10_source import waku,source,NAMES
from research_model import probabilities

def fixture():
    base,card,batch=inputs()
    for i,r in enumerate(card["racers"]):
        r["name"]=NAMES[i]
    e=source(waku())
    e["race_code"]=base["race_code"]
    e["row"]["レースコード"]=base["race_code"]
    return base,card,e

class PilotTests(unittest.TestCase):
    def test_complete_120_ticket_research_only_study_uses_proper_st_label(self):
        base,card,e=fixture()
        out=prepare_waku10_pilot(base,card,e,frozen_at=FROZEN)
        self.assertEqual(out["protocol"],PROTOCOL)
        for key in ("baseline","waku10_course","waku10_course_plus_frame_st_proxy"):
            self.assertEqual(len(out[key]),120)
            self.assertEqual(len(set(out[key])),120)
        self.assertEqual(list(out["sample_counts"].values()),[10,10,9,10,9,9])
        self.assertTrue(out["frame_st_is_not_course_st"])
        self.assertFalse(out["formal"])
        self.assertFalse(out["calibrated"])
        self.assertTrue(out["not_equivalent_to_t12"])
    def test_swapped_actual_entry_not_rebranded_as_ten_same_course_starts(self):
        base,card,e=fixture()
        card["beforeinfo"]["start_exhibition"][0]["course"]=2
        card["beforeinfo"]["start_exhibition"][1]["course"]=1
        with self.assertRaisesRegex(ValueError,"insufficient_course_specific_frame_runs"):
            prepare_waku10_pilot(base,card,e,frozen_at=FROZEN)
    def test_late_waku10_receipt_fails(self):
        base,card,e=fixture()
        e["received_at"]="2026-11-03T18:30:00+09:00"
        with self.assertRaisesRegex(ValueError,"source_after_freeze"):
            prepare_waku10_pilot(base,card,e,frozen_at=FROZEN)
    def test_no_late_preview_fails_without_fake_entry(self):
        base,card,e=fixture()
        card["source_audit"]["beforeinfo"]["status"]="unavailable"
        with self.assertRaisesRegex(ValueError,"preview_unavailable"):
            prepare_waku10_pilot(base,card,e,frozen_at=FROZEN)
    def test_racecard_receipt_must_be_before_freeze(self):
        base,card,e=fixture()
        card["source_audit"]["race_card"]["fetched_at"]="2026-11-03T18:30:00+09:00"
        with self.assertRaisesRegex(ValueError,"card_receipt_invalid"):
            prepare_waku10_pilot(base,card,e,frozen_at=FROZEN)
    def test_insufficient_complete_history_still_excluded(self):
        base,card,e=fixture()
        e["row"]["艇3_過去1走_着順"]="F"
        e["row"]["艇3_過去2走_着順"]="欠"
        with self.assertRaisesRegex(ValueError,"insufficient_course_specific_frame_runs"):
            prepare_waku10_pilot(base,card,e,frozen_at=FROZEN)
if __name__=="__main__":unittest.main()
