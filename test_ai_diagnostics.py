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
        return json.dumps({"output": [{"type": "message", "content": [
            {"type": "output_text", "text": "改善案は確認待ち"}
        ]}]}).encode()


class DiagnosticsTests(unittest.TestCase):
    def test_missing_key_is_offline(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            self.assertEqual(ai_diagnostics.analyze({"gate": {}})["status"], "disabled")

    def test_sends_report_read_only(self):
        def fake(req, timeout):
            payload = json.loads(req.data)
            self.assertEqual(payload["store"], False)
            self.assertIn("本命", payload["instructions"])
            self.assertIn("balance", payload["input"])
            self.assertEqual(timeout, 35)
            return FakeResponse()
        result = ai_diagnostics.analyze({"balance": 1}, api_key="example", transport=fake)
        self.assertEqual(result["status"], "analysis_proposed")
        self.assertFalse(result["production_change_allowed"])

    def test_model_default_is_supported_name(self):
        with patch.dict('os.environ', {'OPENAI_MODEL': '', 'OPENAI_API_KEY': ''}):
            self.assertEqual(ai_diagnostics.analyze({})['status'], 'disabled')

    def test_no_empty_llm_output(self):
        with self.assertRaises(ValueError):
            ai_diagnostics.extract_text({"output": []})

    def test_large_report_rejected(self):
        with self.assertRaisesRegex(ValueError, "report_too_large"):
            ai_diagnostics.analyze({"x": "z" * 25000}, api_key="example")


if __name__ == "__main__":
    unittest.main()
