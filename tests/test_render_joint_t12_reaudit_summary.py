import unittest
from scripts.render_joint_t12_reaudit_summary import format_reaudit


class ReauditSummaryTests(unittest.TestCase):
    def test_only_source_verified_count_displayed(self):
        report = {"full_history_verified":False,
                  "verified_complete_pair_attempts_in_inspected_artifacts":2,
                  "artifact_results":[{"verified_complete_pairs":2,"status":"source_reaudit_complete"},
                                      {"verified_complete_pairs":0,"status":"source_reaudit_unresolved"}]}
        output = format_reaudit(report)
        self.assertIn("Independently verified complete attempt pairs | 2", output)
        self.assertIn("Archives unresolved | 1", output)
        self.assertIn("not determined", output)

    def test_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            format_reaudit({"full_history_verified":False,
                            "verified_complete_pair_attempts_in_inspected_artifacts":1,
                            "artifact_results":[]})


if __name__ == "__main__":
    unittest.main()
