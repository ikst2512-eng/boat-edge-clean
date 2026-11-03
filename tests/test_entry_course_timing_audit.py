import unittest
from entry_course_timing_audit import classify_course_timing

BASE={"cutoff_jst":"2026-11-03T18:21:00+09:00",
      "source_deadline_jst":"2026-11-03T18:33:00+09:00",
      "generated_at":"2026-11-03T10:49:20+09:00"}

def preview(at):
    return {"status":"ok","sources":{
        "stt":{"observed_at":at},"tkz":{"observed_at":at}}}

class TimingTests(unittest.TestCase):
    def test_t5_preview_is_not_t12_evidence(self):
        x=classify_course_timing(BASE,preview("2026-11-03T18:28:00+09:00"))
        self.assertEqual(x["status"],"preview_after_t12_late_research_only")
        self.assertFalse(x["eligible_for_t12_comparison"])
        self.assertTrue(x["late_experiment_possible"])
        self.assertFalse(x["equal_information_comparison_verified"])
    def test_t12_exact_boundary_is_not_eligible(self):
        x=classify_course_timing(BASE,preview(BASE["cutoff_jst"]))
        self.assertFalse(x["eligible_for_t12_comparison"])
    def test_truly_early_preview_is_eligible_for_time_gate_only(self):
        x=classify_course_timing(BASE,preview("2026-11-03T18:20:00+09:00"))
        self.assertTrue(x["eligible_for_t12_comparison"])
        self.assertFalse(x["formal_forecast_approved"])
    def test_after_late_cutoff_is_not_eligible(self):
        x=classify_course_timing(BASE,preview("2026-11-03T18:32:00+09:00"))
        self.assertEqual(x["status"],"preview_too_late_for_late_research")
        self.assertFalse(x["late_experiment_possible"])
    def test_no_preview_is_explicit(self):
        x=classify_course_timing(BASE,None)
        self.assertEqual(x["status"],"preview_unavailable")
    def test_missing_one_source_is_not_evidence(self):
        p=preview("2026-11-03T18:20:00+09:00")
        del p["sources"]["tkz"]
        self.assertEqual(classify_course_timing(BASE,p)["status"],"preview_receipt_missing")
    def test_future_preview_is_blocked(self):
        x=classify_course_timing(BASE,preview("2026-11-03T18:35:00+09:00"))
        self.assertEqual(x["status"],"preview_after_deadline")
        self.assertFalse(x["late_experiment_possible"])
    def test_untrusted_baseline_timing_is_blocked(self):
        base=dict(BASE,generated_at="2026-11-03T18:25:00+09:00")
        self.assertEqual(classify_course_timing(base,preview("2026-11-03T18:20:00+09:00"))["status"],"invalid_baseline_timing")
    def test_bad_late_margin_is_rejected(self):
        x=classify_course_timing(BASE,preview("2026-11-03T18:20:00+09:00"),late_margin_minutes="2")
        self.assertEqual(x["status"],"invalid_late_window")
if __name__=="__main__":unittest.main()
