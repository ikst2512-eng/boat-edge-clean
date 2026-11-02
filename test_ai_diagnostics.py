import json
import unittest
from unittest.mock import patch
import ai_diagnostics


class FakeResponse:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, max_bytes):
        return json.dumps({"candidates": [{"content": {"parts": [
            {"text": "改善案は確認待ち"}
        ]}}]}).encode()


class DiagnosticsTests(unittest.TestCase):
    def test_attach_research_case_is_never_formal(self):
        with patch("four_mode_frozen_diagnostic.compare_race", return_value={
            "status": "historical_comparison_only", "formal": False,
            "modes": {"hit": {"coverage_diagnostic": "winner_third_absent"}}}):
            payload = ai_diagnostics.attach_frozen_race({"gate": {}}, "202610310912")
        self.assertFalse(payload["formal_hit_rate_allowed"])
        self.assertEqual(payload["race_dynamics_evidence"], "not_provided")
        self.assertEqual(payload["frozen_four_mode_research_case"]["modes"]["hit"]["coverage_diagnostic"], "winner_third_absent")

    def test_untrusted_race_rejected_before_api_call(self):
        with patch("four_mode_frozen_diagnostic.compare_race", return_value={"status": "result_unavailable"}):
            with self.assertRaisesRegex(ValueError, "historical_race_unavailable"):
                ai_diagnostics.attach_frozen_race({}, "202610310912")

    def test_actual_saved_race_is_read_only_historical_case(self):
        case = ai_diagnostics.attach_frozen_race({"gate": {}}, "202610280101")
        actual = case["frozen_four_mode_research_case"]
        self.assertEqual(actual["winning_ticket"], "4-1-3")
        self.assertEqual(set(actual["modes"]), {"hit", "balance", "hole", "narrow"})
        self.assertEqual(actual["modes"]["narrow"]["coverage_diagnostic"], "winner_head_absent")
        self.assertFalse(case["formal_hit_rate_allowed"])
        self.assertFalse(actual["remote_first_seen_verified"])
        self.assertEqual(case["race_dynamics_evidence"], "not_provided")

    def test_missing_key_is_offline(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            self.assertEqual(ai_diagnostics.analyze({"gate": {}})["status"], "disabled")

    def test_sends_report_read_only(self):
        def fake(req, timeout):
            payload = json.loads(req.data)
            self.assertIn("gemini-3.5-flash-lite:generateContent", req.full_url)
            self.assertEqual(req.get_header("X-goog-api-key"), "example")
            self.assertIn("本命", payload["system_instruction"]["parts"][0]["text"])
            self.assertIn("balance", payload["contents"][0]["parts"][0]["text"])
            self.assertEqual(timeout, 35)
            return FakeResponse()
        result = ai_diagnostics.analyze({"balance": 1}, api_key="example", transport=fake)
        self.assertEqual(result["status"], "analysis_proposed")
        self.assertFalse(result["production_change_allowed"])

    def test_model_default_is_supported_name(self):
        with patch.dict('os.environ', {'GEMINI_MODEL': '', 'GEMINI_API_KEY': ''}):
            self.assertEqual(ai_diagnostics.analyze({})['status'], 'disabled')

    def test_no_empty_llm_output(self):
        with self.assertRaises(ValueError):
            ai_diagnostics.extract_text({"candidates": []})

    def test_large_report_rejected(self):
        with self.assertRaisesRegex(ValueError, "report_too_large"):
            ai_diagnostics.analyze({"x": "z" * 25000}, api_key="example")


if __name__ == "__main__":
    unittest.main()
