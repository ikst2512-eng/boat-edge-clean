import unittest
from pathlib import Path
from scripts.joint_t12_failure_reason import classify


class FailureReasonTests(unittest.TestCase):
    def test_cutoff_is_only_claimed_with_explicit_gate(self):
        self.assertEqual(classify("beforeinfo_after_t12"), "cutoff")
        self.assertEqual(classify("insufficient_time_to_fetch_odds"), "cutoff")
        self.assertNotEqual(classify("beforeinfo_failed_or_deadline_missing", "HTTPError"), "cutoff")

    def test_http_error_does_not_prove_unpublished_source(self):
        self.assertEqual(classify("beforeinfo_failed_or_deadline_missing", "HTTPError"), "http_unresolved")
        self.assertEqual(classify("odds_failed", "HTTPError"), "http_unresolved")

    def test_transport_storage_unknown_and_audit(self):
        self.assertEqual(classify("odds_failed", "TimeoutError"), "transport")
        self.assertEqual(classify("odds_failed", "URLError"), "transport")
        self.assertEqual(classify("odds_failed", "OSError"), "storage_or_io_unresolved")
        self.assertEqual(classify("odds_failed", "KeyError"), "unknown")
        self.assertEqual(classify("joint_original_audit_failed"), "audit_invalid")

    def test_workflow_diagnostics_do_not_change_prediction_gates(self):
        source = Path(".github/workflows/official-joint-t12-dispatch.yml").read_text()
        self.assertIn("from scripts.joint_t12_failure_reason import classify", source)
        self.assertIn("failure['failure_category']=classify(", source)
        self.assertIn("result['failure_category']=classify(", source)
        self.assertIn("if can_retry(", source)
        self.assertIn("if result['both_complete_before_t12']:", source)


if __name__ == "__main__":
    unittest.main()
