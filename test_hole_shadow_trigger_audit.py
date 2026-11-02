import unittest
from hole_shadow_trigger_audit import inspect_range

A="a"*40
B="b"*40
class TriggerAuditTests(unittest.TestCase):
    def test_counts_only_additions(self):
        def fake(cmd,text):
            self.assertIn("--diff-filter=A",cmd)
            return "A\tfour_mode_forecasts/202611030101.json\nA\tfour_mode_forecasts/bad.json\n"
        r=inspect_range(A,B,fake)
        self.assertEqual(r["new_forecast_codes"],["202611030101"])
        self.assertIsNone(r["capture_workflow_triggered"])
        self.assertIs(r["independent_predeadline_proof"],False)
    def test_invalid_sha(self):
        with self.assertRaises(ValueError):
            inspect_range("main",B)
        with self.assertRaises(ValueError):
            inspect_range("0"*40,B)
if __name__=="__main__":unittest.main()
