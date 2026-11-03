import unittest
from scripts.audit_four_mode_daily_main_archives import audit, parse_additions, scheduled_audit_alert

A = "a" * 40
B = "b" * 40
P = "four_mode_forecasts/202611040101.json"
P2 = "four_mode_forecasts/202611040102.json"
OLD = "four_mode_forecasts/202611030101.json"


class DailyMainArchivesTest(unittest.TestCase):
    def test_november_fourth_first_add_proven_only_as_git_evidence(self):
        adds = parse_additions(A + "\n\n" + P + "\n" + P2 + "\n\n" + B + "\n\n" + OLD + "\n")
        result = audit("20261104", [P, P2, OLD, "four_mode_forecasts/capture_status.json"],
                       adds, main_context=True)
        self.assertEqual(result["today_archive_count"], 2)
        self.assertEqual(result["today_single_first_add_count"], 2)
        self.assertTrue(result["main_git_addition_evidence_present"])
        self.assertEqual(result["assessment"], "new_day_git_archives_found")
        self.assertFalse(result["independent_remote_first_seen_verified"])
        self.assertFalse(result["source_predeadline_verified"])

    def test_capture_status_metadata_is_not_an_archive(self):
        raw = A + "\n\n" + "four_mode_forecasts/capture_status.json" + "\n" + P + "\n"
        adds = parse_additions(raw)
        self.assertEqual(adds, {P: [A]})

    def test_no_new_day_is_pending_not_success(self):
        result = audit("20261104", [OLD], {OLD: [A]}, main_context=True)
        self.assertEqual(result["today_archive_count"], 0)
        self.assertEqual(result["assessment"], "no_new_day_archives_yet")
        self.assertFalse(result["main_git_addition_evidence_present"])

    def test_missing_or_readded_archive_not_proven(self):
        result = audit("20261104", [P, P2], {P: [A, B]}, main_context=True)
        self.assertEqual(result["assessment"], "git_first_add_incomplete")
        self.assertEqual(result["today_multiple_first_add_count"], 1)
        self.assertEqual(result["today_missing_first_add_count"], 1)

    def test_pr_checkout_cannot_claim_main(self):
        result = audit("20261104", [P], {P: [A]}, main_context=False)
        self.assertEqual(result["assessment"], "not_main_checkout")
        self.assertFalse(result["main_git_addition_evidence_present"])

    def test_daily_cron_alerts_on_absence_without_affecting_pr_or_push(self):
        missing = audit("20261104", [OLD], {OLD: [A]}, main_context=True)
        self.assertTrue(scheduled_audit_alert(missing, "schedule"))
        self.assertFalse(scheduled_audit_alert(missing, "push"))
        self.assertFalse(scheduled_audit_alert(missing, "pull_request"))
        pr = audit("20261104", [OLD], {OLD: [A]}, main_context=False)
        self.assertFalse(scheduled_audit_alert(pr, "schedule"))

    def test_daily_cron_alerts_on_incomplete_first_add_only(self):
        bad = audit("20261104", [P], {}, main_context=True)
        good = audit("20261104", [P], {P: [A]}, main_context=True)
        self.assertTrue(scheduled_audit_alert(bad, "schedule"))
        self.assertFalse(scheduled_audit_alert(good, "schedule"))

    def test_reject_malformed_history_and_tree(self):
        with self.assertRaises(ValueError):
            parse_additions(P)
        with self.assertRaises(ValueError):
            audit("20261104", [P, P], {}, main_context=True)
        with self.assertRaises(ValueError):
            audit("2026-11-04", [], {}, main_context=True)
        with self.assertRaises(ValueError):
            audit("20261104", [123], {}, main_context=True)


if __name__ == "__main__":
    unittest.main()
