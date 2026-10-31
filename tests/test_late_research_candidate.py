import unittest
from scripts.late_research_candidate import candidate, exhibition_sensitive_candidate

class CandidateTest(unittest.TestCase):
    def test_altered_actual_course_changes_order_without_using_result(self):
        base={"race_code":"202610312311","both_sources_received_at_jst":"2026-10-31T19:55:00+09:00",
              "boats":[{"boat":i,"entry_course":i,"exhibition_time":6.7,
                        "tilt":0,"start_exhibition":"0.12"} for i in range(1,7)]}
        result=candidate(base)
        self.assertEqual(len(result["predictions"]),10)
        self.assertEqual(len(set(result["predictions"])),10)
        self.assertEqual(result["predictions"][0],"1-2-3")
        self.assertFalse(result["validated"])
        swapped={**base,"boats":[dict(x,entry_course=(2 if x["boat"]==1 else 1 if x["boat"]==2 else x["entry_course"])) for x in base["boats"]]}
        self.assertEqual(candidate(swapped)["predictions"][0],"2-1-3")
        self.assertEqual(candidate(swapped)["model_version"],"late-course-mechanical-baseline-v0")

    def test_invalid_duplicate_course_rejected(self):
        base={"race_code":"202610312311","both_sources_received_at_jst":"2026-10-31T19:55:00+09:00",
              "boats":[{"boat":i,"entry_course":1,"exhibition_time":6.7} for i in range(1,7)]}
        with self.assertRaises(ValueError):
            candidate(base)

    def test_exhibition_contrast_changes_order_only_when_timing_is_different(self):
        pair={"race_code":"202610312311","both_sources_received_at_jst":"2026-10-31T19:55:00+09:00",
              "boats":[{"boat":i,"entry_course":i,"exhibition_time":6.7} for i in range(1,7)]}
        ordinary=exhibition_sensitive_candidate(pair)
        self.assertEqual(ordinary["predictions"][0],"1-2-3")
        changed={**pair,"boats":[dict(x,exhibition_time=6.3 if x["boat"]==2 else x["exhibition_time"]) for x in pair["boats"]]}
        self.assertEqual(candidate(changed)["predictions"][0],"1-2-3")
        modified=exhibition_sensitive_candidate(changed)
        self.assertEqual(modified["predictions"][0],"2-1-3")
        self.assertEqual(len(set(modified["predictions"])),10)
        self.assertFalse(modified["validated"])

    def test_exhibition_contrast_rejects_missing_or_invalid_time(self):
        pair={"race_code":"202610312311","both_sources_received_at_jst":"2026-10-31T19:55:00+09:00",
              "boats":[{"boat":i,"entry_course":i,"exhibition_time":None if i==2 else 6.7} for i in range(1,7)]}
        with self.assertRaises(ValueError):
            exhibition_sensitive_candidate(pair)


if __name__=="__main__":
    unittest.main()
