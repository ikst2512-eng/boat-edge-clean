import json
import tempfile
import unittest
from pathlib import Path
from research_model import probabilities
from research_hole_head_capture import first_place_candidates, analyze

class HoleHeadCaptureTests(unittest.TestCase):
    def test_one_or_two_heads(self):
        rates=[6.2,5.1,4.2,4.5,3.1,2.9]
        one=first_place_candidates(rates,1)
        two=first_place_candidates(rates,2)
        self.assertEqual(len(one),1)
        self.assertEqual(len(two),2)
        self.assertTrue(set(one).issubset(two))
        three=first_place_candidates(rates,3)
        self.assertEqual(len(three),3)
        self.assertTrue(set(two).issubset(three))
        with self.assertRaises(ValueError): first_place_candidates(rates,4)

    def test_result_is_head_only_not_ticket_accuracy(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            folder=root/"four_mode_forecasts"
            folder.mkdir()
            code="202610280101"
            rates=[6.2,5.1,4.2,4.5,3.1,2.9]
            finish="-".join(map(str,probabilities(rates)[0][0]))
            archive={"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1","race_code":code,
                     "input_national_win_rates":rates,
                     "modes":{"hole":{"tickets":[{"combo":finish}]}}}
            (folder/(code+".json")).write_text(json.dumps(archive),encoding="utf-8")
            h={"schema":"CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1","budget_yen":10000,
               "races":[{"race_code":code,"finish":finish}]}
            result=analyze(h,root)
            self.assertEqual(result["head_candidate_capture_counts"]["one_head"],1)
            self.assertEqual(result["head_candidate_capture_counts"]["two_heads"],1)
            self.assertEqual(result["head_candidate_capture_counts"]["three_heads"],1)
            self.assertIsNone(result["hole_roi"])
            self.assertIsNone(result["hole_ticket_hit_rates"])
            h["races"].append(h["races"][0])
            with self.assertRaisesRegex(ValueError,"duplicate_race"):
                analyze(h,root)

if __name__=="__main__": unittest.main()
