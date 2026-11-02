"""Original-source T12 component diagnostics must not loosen the joint gate."""
import tempfile
import unittest
from unittest.mock import patch
from scripts.audit_joint_official_receipts import audit_pair
from tests.test_audit_joint_official_receipts import JointReceiptTests


class ComponentDiagnosticsTests(unittest.TestCase):
    def test_incomplete_exhibition_is_explicitly_diagnosed(self):
        helper = JointReceiptTests()
        with tempfile.TemporaryDirectory() as root:
            a, b = helper.make(root, complete=False)
            with patch("scripts.audit_joint_official_receipts.parse_official_odds_table", return_value={"fixture": 1}), patch(
                "scripts.audit_joint_official_receipts.inspect_odds_receipt",
                return_value={"valid_120_combinations": True, "complete_odds_observed_before_t12": True}
            ):
                result = audit_pair(a, b)
            self.assertFalse(result["both_complete_before_t12"])
            self.assertFalse(result["forecast_usable"])
            self.assertFalse(result["full_t12_source_certified"])
            self.assertFalse(result["independent_source_coverage"]["official_racecard_original"])
            self.assertFalse(result["independent_source_coverage"]["official_entry_original"])
            self.assertEqual(result["missing_components"], ["exhibition_time_six"])
            self.assertTrue(result["component_checks"]["official_odds_120"])

    def test_complete_pair_exposes_no_missing_components_but_never_authorizes(self):
        helper = JointReceiptTests()
        with tempfile.TemporaryDirectory() as root:
            a, b = helper.make(root)
            with patch("scripts.audit_joint_official_receipts.parse_official_odds_table", return_value={"fixture": 1}), patch(
                "scripts.audit_joint_official_receipts.inspect_odds_receipt",
                return_value={"valid_120_combinations": True, "complete_odds_observed_before_t12": True}
            ):
                result = audit_pair(a, b)
            self.assertTrue(result["both_complete_before_t12"])
            self.assertFalse(result["full_t12_source_certified"])
            self.assertEqual(result["independent_source_coverage"], {
                "official_racecard_original": False,
                "official_entry_original": False,
                "official_beforeinfo_original": True,
                "official_odds_original": True,
            })
            self.assertEqual(result["missing_components"], [])
            self.assertFalse(result["forecast_usable"])
            self.assertFalse(result["t12_eligible"])
