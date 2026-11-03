import unittest
from scripts.audit_four_mode_daily_main_archives import audit, parse_additions, scheduled_audit_alert, positive_eligible_run_ids

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
        self.assertFalse(scheduled_audit_alert(missing, "schedule"))
        self.assertTrue(scheduled_audit_alert(missing, "schedule", [self.positive_capture()]))
        self.assertFalse(scheduled_audit_alert(missing, "push"))
        self.assertFalse(scheduled_audit_alert(missing, "pull_request"))
        pr = audit("20261104", [OLD], {OLD: [A]}, main_context=False)
        self.assertFalse(scheduled_audit_alert(pr, "schedule"))

    def test_daily_cron_alerts_on_incomplete_first_add_only(self):
        bad = audit("20261104", [P], {}, main_context=True)
        good = audit("20261104", [P], {P: [A]}, main_context=True)
        self.assertTrue(scheduled_audit_alert(bad, "schedule"))
        self.assertFalse(scheduled_audit_alert(good, "schedule"))


    @staticmethod
    def positive_capture(at="2026-11-04T00:07:00Z", eligible=3, present=True):
        return {"runs": [{"run_id": 415, "created_at": at,
                          "artifact_present": present, "generated_today": 0, "newly_generated": eligible}]}

    def test_cross_day_or_missing_artifact_not_positive(self):
        missing = audit("20261104", [OLD], {OLD: [A]}, main_context=True)
        self.assertFalse(scheduled_audit_alert(missing, "schedule",
                                               [self.positive_capture("2026-11-03T14:00:00Z")]))
        self.assertFalse(scheduled_audit_alert(missing, "schedule",
                                               [self.positive_capture(present=False)]))
        self.assertFalse(scheduled_audit_alert(missing, "schedule",
                                               [self.positive_capture(eligible=0)]))
        self.assertEqual(positive_eligible_run_ids("20261104", [self.positive_capture()]), [415])

    def test_existing_local_archives_do_not_prove_new_candidates(self):
        missing = audit("20261104", [OLD], {OLD: [A]}, main_context=True)
        record = self.positive_capture(eligible=0)
        record["runs"][0]["generated_today"] = 149
        self.assertFalse(scheduled_audit_alert(missing, "schedule", [record]))
        self.assertEqual(positive_eligible_run_ids("20261104", [record]), [])

    def test_staged_valid_and_claimed_push_are_positive(self):
        for key in ("staged_valid", "claimed_added_forecasts"):
            report = self.positive_capture(eligible=0)
            report["runs"][0][key] = 2
            self.assertEqual(positive_eligible_run_ids("20261104", [report]), [415])

    def test_positive_same_day_from_dispatch_evidence(self):
        missing = audit("20261104", [OLD], {OLD: [A]}, main_context=True)
        report = {"schema": "FOUR_MODE_DISPATCH_PUBLICATION_EVIDENCE_V1", **self.positive_capture()}
        self.assertTrue(scheduled_audit_alert(missing, "schedule", [report]))
        self.assertFalse(scheduled_audit_alert(missing, "push", [report]))

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
