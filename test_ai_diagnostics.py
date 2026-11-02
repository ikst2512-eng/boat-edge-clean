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
        return json.dumps({"candidates": [{"finishReason": "STOP", "content": {"parts": [
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

    def test_real_analysis_is_never_auto_promoted(self):
        report = ai_diagnostics.attach_frozen_race({}, "202610280101")
        result = ai_diagnostics.review_analysis_output(
            {"status": "analysis_proposed", "analysis": "的中率が改善する"}, 
            report["frozen_four_mode_research_case"])
        self.assertEqual(result["review_status"], "manual_evidence_review_required")
        self.assertFalse(result["improvement_proven"])
        self.assertFalse(result["production_change_allowed"])
        self.assertFalse(result["formal_hit_rate_allowed"])

    def test_empty_or_unverified_output_is_blocked(self):
        self.assertEqual(ai_diagnostics.review_analysis_output(
            {"status": "disabled"})["review_status"], "no_analysis")
        self.assertEqual(ai_diagnostics.review_analysis_output(
            {"status": "analysis_proposed", "analysis": "test"})["review_status"],
            "research_case_not_verified")

    def test_explicit_manual_requirement_rejects_disabled_analysis(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            output = Path(directory) / "out.json"
            report.write_text('{"gate":{}}', encoding="utf-8")
            with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
                with patch("sys.argv", ["ai_diagnostics.py", "--report", str(report),
                                        "--output", str(output), "--require-analysis"]):
                    with self.assertRaises(SystemExit) as exc:
                        ai_diagnostics.main()
            self.assertEqual(exc.exception.code, 2)
            self.assertEqual(json.loads(output.read_text())["status"], "disabled")

    def test_api_error_still_saves_safe_report(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            output = Path(directory) / "out.json"
            report.write_text('{"gate":{}}', encoding="utf-8")
            with patch("ai_diagnostics.analyze", side_effect=RuntimeError("Gemini HTTP 429")):
                with patch("sys.argv", ["ai_diagnostics.py", "--report", str(report),
                                        "--output", str(output), "--require-analysis"]):
                    with self.assertRaises(SystemExit) as exc:
                        ai_diagnostics.main()
            self.assertEqual(exc.exception.code, 2)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "api_error")
            self.assertFalse(data["production_change_allowed"])
            self.assertNotIn("Gemini HTTP 429", json.dumps(data))

    def test_input_hash_is_deterministic(self):
        import hashlib
        payload = {"gate": {"a": 1}, "b": 2}
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.assertEqual(len(hashlib.sha256(canonical).hexdigest()), 64)
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            inp, out = Path(directory) / "in.json", Path(directory) / "out.json"
            inp.write_text(json.dumps(payload), encoding="utf-8")
            with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
                with patch("sys.argv", ["ai_diagnostics.py", "--report", str(inp), "--output", str(out)]):
                    ai_diagnostics.main()
            record = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(record["research_input_sha256"], hashlib.sha256(canonical).hexdigest())

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

    def test_malformed_response_is_safely_rejected(self):
        for payload in ({"candidates": [None]}, {"candidates": [{"content": {"parts": [None]}}]},
                        {"candidates": [{"content": {"parts": "invalid"}}]},
                        {"candidates": [{"content": {"parts": [{"text": "  "}]}}]}):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    ai_diagnostics.extract_text(payload)

    def test_multiple_candidates_rejected_as_ambiguous(self):
        candidate = {"finishReason":"STOP", "content":{"parts":[{"text":"分析案"}]}}
        with self.assertRaisesRegex(ValueError, "ambiguous_candidate_count"):
            ai_diagnostics.extract_text({"candidates":[candidate,candidate]})

    def test_partial_or_blocked_gemini_output_is_not_success(self):
        for reason in ("MAX_TOKENS", "SAFETY", None):
            with self.subTest(reason=reason):
                response = {"candidates": [{"finishReason": reason,
                            "content": {"parts": [{"text": "未完了の分析案"}]}}]}
                with self.assertRaisesRegex(ValueError, "incomplete_or_blocked_generation"):
                    ai_diagnostics.extract_text(response)

    def test_oversize_ai_response_is_safely_rejected(self):
        with self.assertRaisesRegex(ValueError, "output_too_large"):
            ai_diagnostics.extract_text({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "X"*17000}]}}]})

    def test_manual_frozen_race_success_requires_review_not_auto_promotion(self):
        import hashlib
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            report, output, case_file = (base / n for n in ("in.json", "out.json", "case.json"))
            report.write_text('{"gate":{"data_quality":"research"}}', encoding="utf-8")
            fake_analysis = {"status": "analysis_proposed", "analysis": "根拠を再検証する",
                             "model": "test-only", "production_change_allowed": False}
            with patch("ai_diagnostics.analyze", return_value=fake_analysis):
                with patch("sys.argv", ["ai_diagnostics.py", "--report", str(report),
                                        "--output", str(output), "--case-output", str(case_file),
                                        "--race-code", "202610280101", "--require-analysis"]):
                    ai_diagnostics.main()
            recorded = json.loads(output.read_text(encoding="utf-8"))
            case = json.loads(case_file.read_text(encoding="utf-8"))
            self.assertEqual(recorded["status"], "analysis_proposed")
            self.assertEqual(recorded["evidence_review"]["review_status"],
                             "manual_evidence_review_required")
            self.assertFalse(recorded["evidence_review"]["formal_hit_rate_allowed"])
            self.assertFalse(recorded["evidence_review"]["improvement_proven"])
            self.assertFalse(recorded["evidence_review"]["production_change_allowed"])
            self.assertEqual(case["winning_ticket"], "4-1-3")
            self.assertEqual(recorded["research_input_digest_scope"],
                             "local_audit_payload_before_api_call")
            self.assertEqual(len(recorded["research_input_sha256"]), 64)

    def test_real_response_model_and_usage_are_recorded(self):
        class ActualResponse(FakeResponse):
            def read(self, max_bytes):
                return json.dumps({"modelVersion": "gemini-3.5-flash-lite",
                    "usageMetadata": {"promptTokenCount": 42, "candidatesTokenCount": 15,
                                      "totalTokenCount": 57},
                    "candidates": [{"finishReason": "STOP",
                                    "content": {"parts": [{"text": "レビュー対象"}]}}]}).encode()
        result = ai_diagnostics.analyze({"gate": {}}, api_key="example",
                                         transport=lambda request, timeout: ActualResponse())
        self.assertEqual(result["response_model_version"], "gemini-3.5-flash-lite")
        self.assertEqual(result["token_usage"]["totalTokenCount"], 57)
        self.assertFalse(result["production_change_allowed"])

    def test_invalid_response_usage_is_rejected(self):
        class BrokenResponse(FakeResponse):
            def read(self, max_bytes):
                return json.dumps({"usageMetadata": {"totalTokenCount": -1},
                    "candidates": [{"finishReason":"STOP",
                                    "content":{"parts":[{"text":"レビュー対象"}]}}]}).encode()
        with self.assertRaisesRegex(ValueError, "invalid_response_token_count"):
            ai_diagnostics.analyze({"gate": {}}, api_key="example",
                                   transport=lambda request, timeout: BrokenResponse())

    def test_large_report_rejected(self):
        with self.assertRaisesRegex(ValueError, "report_too_large"):
            ai_diagnostics.analyze({"x": "z" * 25000}, api_key="example")


if __name__ == "__main__":
    unittest.main()
