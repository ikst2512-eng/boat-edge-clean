"""Negative tests for a fixed-sample, predeclared, *unscored* forward study."""
import json
import tempfile
import unittest
from pathlib import Path
from forward_hole_rank3_protocol import PROTOCOL, SOURCE, validate


class ForwardProtocolTests(unittest.TestCase):
    def test_study_is_pinned_and_does_not_score_any_race(self):
        report = validate()
        self.assertEqual(report["status"], "forward_protocol_recorded_not_scored")
        self.assertEqual(report["minimum_future_verified_pairs_required"], 300)
        self.assertIsNone(report["actual_future_eligible_race_count"])
        self.assertFalse(report["future_capture_inventory_checked"])
        self.assertFalse(report["prospective_results_checked"])
        self.assertFalse(report["formal"])
        self.assertFalse(report["production_promotion_allowed"])

    def alter(self, mutation, error):
        data = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        mutation(data)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, error):
                validate(path=path)

    def test_cannot_shorten_sample_after_seeing_results(self):
        self.alter(lambda x: x.__setitem__("first_n_eligible_races", 20),
                   "protocol_contract_changed")

    def test_cannot_change_primary_metric_or_alpha(self):
        self.alter(lambda x: x["endpoint"].__setitem__("primary", "top3"),
                   "metric_contract_changed")
        self.alter(lambda x: x["evaluation"].__setitem__("alpha", .10),
                   "statistics_contract_changed")

    def test_cannot_claim_formal_accuracy_just_by_flag(self):
        self.alter(lambda x: x.__setitem__("formal", True),
                   "protocol_contract_changed")
        self.alter(lambda x: x["governance"].__setitem__(
            "official_accuracy_requires_separate_independent_certification", False),
            "governance_guard_missing")

    def test_cannot_weaken_before_result_evidence(self):
        self.alter(lambda x: x["include_only_if"].__setitem__(
            "github_server_observation", "git_committer_clock_only"),
            "future_evidence_gate_changed")
        self.alter(lambda x: x["selector"].__setitem__(
            "selection_after_outcome_forbidden", False),
            "predeclared_selector_changed")

    def test_no_post_result_selection_or_slot_replacement(self):
        self.alter(lambda x: x["enrollment"].__setitem__(
            "decision_inputs", "results_and_archive"),
            "pre_result_enrollment_contract_changed")
        self.alter(lambda x: x["enrollment"].__setitem__(
            "pending_result_retains_original_enrolled_slot", False),
            "pre_result_enrollment_contract_changed")
        self.alter(lambda x: x["enrollment"].__setitem__(
            "first_n_pre_result_eligible_races", 100),
            "pre_result_enrollment_contract_changed")

    def test_selector_file_mutation_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            modified = Path(tmp) / "selector.py"
            modified.write_bytes(SOURCE.read_bytes() + b"\n# changed\n")
            with self.assertRaisesRegex(ValueError, "selector_code_mismatch"):
                validate(source=modified)


if __name__ == "__main__":
    unittest.main()
