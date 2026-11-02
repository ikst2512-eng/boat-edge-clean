import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ai_repair_agent import apply, parse_patches, propose, select_source_context
import json
from urllib.error import HTTPError


class RepairAgentTests(unittest.TestCase):
    def test_disallow_model_or_workflow_edits(self):
        for path in ("clean_four_modes.py", ".github/workflows/deploy-pages.yml", "../server.py", "tests/site-regression.cjs"):
            with self.assertRaises(ValueError):
                parse_patches([{"path":path,"old":"x","new":"y"}])

    def test_unique_exact_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"navigation.js").write_text("alpha beta gamma")
            changed=apply(root,[{"path":"navigation.js","old":"beta","new":"delta"}])
            self.assertEqual(changed,["navigation.js"])
            self.assertEqual((root/"navigation.js").read_text(),"alpha delta gamma")

    def test_duplicate_replacement_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"navigation.js").write_text("same same")
            with self.assertRaisesRegex(ValueError,"not_unique"):
                apply(root,[{"path":"navigation.js","old":"same","new":"changed"}])

    def test_multi_file_failure_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"navigation.js").write_text("safe")
            (root/"secondary_navigation.js").write_text("xxx")
            with self.assertRaises(ValueError):
                apply(root,[{"path":"navigation.js","old":"safe","new":"changed"},
                            {"path":"secondary_navigation.js","old":"missing","new":"changed"}])
            self.assertEqual((root/"navigation.js").read_text(),"safe")

    def test_mock_ai_can_propose_exact_patch_without_paid_api(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, n):
                return json.dumps({"candidates":[{"content":{"parts":[{"text":json.dumps({
                        "patches":[{"path":"navigation.js","old":"alpha","new":"beta"}],
                        "reason":"test fixture","tests":"navigation contract"})}
                ]}}]}).encode()
        def fake_transport(req,timeout):
            payload=json.loads(req.data)
            self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
            self.assertIn("x-goog-api-key",{k.lower() for k in req.headers})
            self.assertIn("navigation.js",json.dumps(payload["contents"]))
            return FakeResponse()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"navigation.js").write_text("alpha")
            result=propose("navigation sample",root,"fake-key","gemini-2.5-flash-lite",fake_transport)
            self.assertEqual(result["status"],"proposed")
            self.assertEqual(result["changed_files"],["navigation.js"])
            self.assertFalse(result["production_change_allowed"])
            self.assertEqual((root/"navigation.js").read_text(),"beta")

    def test_mock_ai_rejects_disallowed_workflow_edit(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self,n):
                return json.dumps({"candidates":[{"content":{"parts":[{"text":json.dumps({
                        "patches":[{"path":".github/workflows/ai-repair-proposal.yml",
                                    "old":"a","new":"b"}]})}
                ]}}]}).encode()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"unsafe_path"):
                propose("change workflows",directory,"fake-key","gemini-2.5-flash-lite",
                        lambda req,timeout:FakeResponse())

    def test_large_main_ui_includes_runtime_tail(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, n):
                return json.dumps({"candidates":[{"content":{"parts":[{"text":json.dumps({"patches":[]})}
                ]}}]}).encode()
        def fake(req, timeout):
            sent=json.loads(req.data)["contents"][0]["parts"][0]["text"]
            sources=json.loads(sent)["sources"]
            self.assertIn("RUNTIME_MARKER", sources["index.html"])
            self.assertIn("HEADER_MARKER", sources["index.html"])
            return Response()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"index.html").write_text("HEADER_MARKER"+("x"*180000)+"RUNTIME_MARKER")
            result=propose("repair UI rendering",root,"dummy","mock-model",fake)
            self.assertEqual(result["status"],"no_safe_patch")

    def test_issue_relevant_html_middle_is_available(self):
        source = "HEADER_MARKER" + "x" * 40000 + "\\nfunction forecastPaneBug(){return true;}\\n" + "y" * 40000 + "TAIL_MARKER"
        context = select_source_context(source, "forecastPaneBug")
        self.assertIn("forecastPaneBug", context)
        self.assertIn("HEADER_MARKER", context)
        self.assertIn("TAIL_MARKER", context)
        self.assertLessEqual(len(context), 35000)
        self.assertIn("\n[... contextual excerpt ...]\n", context)
        self.assertNotIn("\\n[... contextual excerpt ...]\\n", context)

    def test_api_429_reports_billing_or_rate_limit_without_leaking(self):
        def rate_limited(request, timeout):
            raise HTTPError(request.full_url, 429, "Too Many Requests", {}, None)
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/"navigation.js").write_text("unchanged")
            with self.assertRaisesRegex(RuntimeError, "free-tier quota or rate limit"):
                propose("navigation fails", directory, "fake-key", "mock", rate_limited)
            self.assertEqual((Path(directory)/"navigation.js").read_text(), "unchanged")

    def test_gemini_patch_real_navigation_source_in_isolation(self):
        # Exercise the actual shipped navigation source through Gemini's response
        # parsing, exact-match guardrails, and atomic file update, without API costs.
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, n):
                patch = {"patches": [{"path": "navigation.js",
                         "old": "const nav=document.querySelector('.site-global-nav');",
                         "new": "const nav=document.querySelector('nav.site-global-nav');"}],
                         "reason": "mocked navigation improvement", "tests": "contract"}
                return json.dumps({"candidates":[{"content":{"parts":[
                    {"text":json.dumps(patch)}]}}]}).encode()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = Path("navigation.js").read_text(encoding="utf-8")
            (root/"navigation.js").write_text(original, encoding="utf-8")
            result = propose("navigation selector explicitness", root,
                             "fake-key", "mock-model",
                             lambda req, timeout: FakeResponse())
            updated = (root/"navigation.js").read_text(encoding="utf-8")
            self.assertEqual(result["status"], "proposed")
            self.assertEqual(result["changed_files"], ["navigation.js"])
            self.assertFalse(result["production_change_allowed"])
            self.assertIn("const nav=document.querySelector('nav.site-global-nav');", updated)
            self.assertEqual(original.count("const nav=document.querySelector('.site-global-nav');"), 1)
            self.assertEqual(updated.count("const nav=document.querySelector('.site-global-nav');"), 0)
            self.assertEqual(Path("navigation.js").read_text(encoding="utf-8"), original)

    def test_gemini_workflow_preserves_review_gate_and_policy_fallback(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(encoding="utf-8")
        # No scheduled calls; AI patches can only be requested manually.
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\\n  schedule:", workflow)
        self.assertIn("if: github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("persist-credentials: false", workflow)
        # A successful push must survive restricted Actions PR creation.
        self.assertIn('git -c credential.helper=', workflow)
        self.assertIn('gh pr create --draft', workflow)
        self.assertIn('GitHub Actions is not permitted to create or approve pull requests', workflow)
        self.assertIn('manual draft PR needed', workflow)
        self.assertIn('exit 1', workflow)
        self.assertNotIn('gh pr merge', workflow)

    def test_no_api_key_no_network(self):
        with tempfile.TemporaryDirectory() as directory:
            def forbidden(*args,**kwargs):
                raise AssertionError("network unexpectedly called")
            self.assertEqual(propose("fix navigation",directory,None,"test",forbidden)["status"],"disabled")


if __name__ == "__main__":
    unittest.main()
