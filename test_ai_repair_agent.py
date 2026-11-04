import tempfile
import hashlib
import os
import subprocess
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
                return json.dumps({"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":json.dumps({
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
            self.assertEqual(result["file_sha256"], {
                "navigation.js": hashlib.sha256(b"beta").hexdigest()
            })
            self.assertFalse(result["production_change_allowed"])
            self.assertEqual((root/"navigation.js").read_text(),"beta")

    def test_mock_ai_rejects_disallowed_workflow_edit(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self,n):
                return json.dumps({"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":json.dumps({
                        "patches":[{"path":".github/workflows/ai-repair-proposal.yml",
                                    "old":"a","new":"b"}]})}
                ]}}]}).encode()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"unsafe_path"):
                propose("change workflows",directory,"fake-key","gemini-2.5-flash-lite",
                        lambda req,timeout:FakeResponse())

    def test_gemini_incomplete_or_ambiguous_output_never_edits_files(self):
        class Response:
            def __init__(self, payload):
                self.payload = payload
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, n):
                return json.dumps(self.payload).encode()

        patch = {"patches": [{"path": "navigation.js", "old": "alpha", "new": "beta"}]}
        for candidates in (
            [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": json.dumps(patch)}]}}],
            [{"finishReason": "SAFETY", "content": {"parts": [{"text": json.dumps(patch)}]}}],
            [{"content": {"parts": [{"text": json.dumps(patch)}]}}],
            [],
            [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(patch)}]}}] * 2,
        ):
            with self.subTest(candidates=candidates), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "navigation.js"
                target.write_text("alpha")
                with self.assertRaisesRegex(ValueError, "invalid_gemini_response"):
                    propose("navigation repair", directory, "fake-key", "mock",
                            lambda request, timeout: Response({"candidates": candidates}))
                self.assertEqual(target.read_text(), "alpha")

    def test_large_main_ui_includes_runtime_tail(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, n):
                return json.dumps({"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":json.dumps({"patches":[]})}
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
        source = "HEADER_MARKER" + "x" * 40000 + "\nfunction forecastPaneBug(){return true;}\n" + "y" * 40000 + "TAIL_MARKER"
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
                return json.dumps({"candidates":[{"finishReason":"STOP","content":{"parts":[
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
            self.assertEqual(result["file_sha256"], {
                "navigation.js": hashlib.sha256(updated.encode("utf-8")).hexdigest()
            })
            self.assertFalse(result["production_change_allowed"])
            self.assertIn("const nav=document.querySelector('nav.site-global-nav');", updated)
            self.assertEqual(original.count("const nav=document.querySelector('.site-global-nav');"), 1)
            self.assertEqual(updated.count("const nav=document.querySelector('.site-global-nav');"), 0)
            self.assertEqual(Path("navigation.js").read_text(encoding="utf-8"), original)

    def test_gemini_workflow_preserves_review_gate_and_policy_fallback(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(encoding="utf-8")
        # No scheduled calls; AI patches can only be requested manually.
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  schedule:", workflow)
        self.assertIn("if: github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("persist-credentials: false", workflow)
        # A successful push must survive restricted Actions PR creation.
        self.assertIn('git -c credential.helper=', workflow)
        self.assertIn('gh pr create --draft', workflow)
        self.assertIn('GitHub Actions is not permitted to create or approve pull requests', workflow)
        self.assertIn('manual draft PR needed', workflow)
        self.assertIn('exit 1', workflow)
        self.assertNotIn('gh pr merge', workflow)

    def test_ai_repair_dispatch_ref_guard(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(encoding="utf-8")
        propose = workflow.split("  propose:\n", 1)[1]
        guard = propose.split("      - name: Refuse AI repair dispatch outside main\n", 1)[1]
        self.assertLess(
            propose.index("      - name: Refuse AI repair dispatch outside main"),
            propose.index("      - uses: actions/checkout@v4"))
        script = guard.split("        run: |\n", 1)[1].split("      - uses: actions/checkout@v4", 1)[0]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        self.assertEqual(subprocess.run(["bash", "-n"], input=script,
                                        text=True, capture_output=True).returncode, 0)
        for ref, expected in (("refs/heads/main", 0),
                              ("refs/heads/feature-branch", 1),
                              ("refs/tags/release", 1)):
            with self.subTest(ref=ref):
                result = subprocess.run(["bash", "-c", script],
                                        env={"DISPATCH_REF": ref, "PATH": "/usr/bin:/bin"},
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, expected)
                if expected:
                    self.assertIn("must be dispatched from main", result.stdout)

    def test_proposal_report_matches_tracked_diff_before_publish(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(encoding="utf-8")
        block = workflow.split("      - name: Validate AI report against actual tracked diff\n", 1)[1]
        block = block.split("      - name: Publish reviewed-by-CI patch as draft PR\n", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        self.assertEqual(subprocess.run(["bash", "-n"], input=script,
                                        text=True, capture_output=True).returncode, 0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "navigation.js").write_text("original\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            report_file = root / "ai_repair_proposal.json"
            cases = (
                ("clean", None, "no_safe_patch", [], 0),
                ("valid_patch", "changed\n", "proposed", ["navigation.js"], 0),
                ("claimed_no_patch", "changed\n", "no_safe_patch", [], 1),
                ("wrong_file", "changed\n", "proposed", ["index.html"], 1),
                ("empty_claim", "changed\n", "proposed", [], 1),
                ("false_claim", None, "proposed", ["navigation.js"], 1),
                ("duplicate_claim", "changed\n", "proposed", ["navigation.js", "navigation.js"], 1),
            )
            for label, replacement, status, claimed, expected in cases:
                with self.subTest(label=label):
                    (root / "navigation.js").write_text(replacement or "original\n")
                    report_file.write_text(json.dumps({
                        "status": status, "changed_files": claimed,
                        "production_change_allowed": False
                    }))
                    # The validation step exits before the independent UI tests
                    # for clean runs, and fails early for inconsistent changes.
                    result = subprocess.run(["bash", "-c", script], cwd=root,
                                            text=True, capture_output=True)
                    if expected:
                        self.assertNotEqual(result.returncode, 0, label + result.stdout + result.stderr)
                    elif replacement is None:
                        self.assertEqual(result.returncode, 0, label + result.stdout + result.stderr)
                    else:
                        # In valid-patch case the guard passes, then the
                        # unrelated site regression command may be absent.
                        self.assertIn("AI proposal report/diff validated: proposed 1", result.stdout)

    def test_ui_test_side_effect_cannot_change_validated_ai_patch(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(encoding="utf-8")
        segment = workflow.split("      - name: Validate AI report against actual tracked diff\n", 1)[1]
        segment = segment.split("      - name: Refuse stale main before publishing AI draft\n", 1)[0]
        snippet = "          before_diff=" + segment.split("          before_diff=", 1)[1]
        snippet = "\n".join(line[10:] if line.startswith("          ") else line
                            for line in snippet.splitlines())
        # Substitute local test fixtures for external regression executables.
        mock_commands = """python() { return 0; }
node() {
    if [[ "$MUTATE_PATCH" == "1" ]]; then
        printf 'unexpected-after-test\\n' > navigation.js
    fi
}
"""
        command = mock_commands + "\n" + snippet
        check = subprocess.run(["bash", "-n"], input=command,
                               text=True, capture_output=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "navigation.js").write_text("original\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            for mutate, expected in ((False, 0), (True, 1)):
                with self.subTest(mutate=mutate):
                    (root / "navigation.js").write_text("reviewed-ai-patch\n")
                    env = dict(os.environ, MUTATE_PATCH="1" if mutate else "0")
                    result = subprocess.run(["bash", "-c", command], cwd=root,
                                            env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected,
                                     result.stdout + result.stderr)
                    if mutate:
                        self.assertIn("tests modified the AI repair diff", result.stdout)

    def test_staged_changes_rejected_before_ai_publish(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(encoding="utf-8")
        block = workflow.split("      - name: Validate AI report against actual tracked diff\n", 1)[1]
        block = block.split("      - name: Refuse stale main before publishing AI draft\n", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "navigation.js").write_text("original\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            (root / "ai_repair_proposal.json").write_text(json.dumps({
                "status": "no_safe_patch", "changed_files": [],
                "production_change_allowed": False
            }))
            clean = subprocess.run(["bash", "-c", script], cwd=root,
                                   capture_output=True, text=True)
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
            (root / "navigation.js").write_text("staged-unreviewed\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            staged = subprocess.run(["bash", "-c", script], cwd=root,
                                    capture_output=True, text=True)
            self.assertNotEqual(staged.returncode, 0,
                                "Staged changes must not be silently committed")
            self.assertIn("CalledProcessError", staged.stderr)

    def test_stale_main_prevents_ai_draft_publication(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(encoding="utf-8")
        preflight = workflow.split("      - name: Refuse stale main before publishing AI draft\n", 1)[1]
        preflight = preflight.split("      - name: Publish reviewed-by-CI patch as draft PR\n", 1)[0]
        script = preflight.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        self.assertEqual(subprocess.run(["bash", "-n"], input=script,
                                        text=True, capture_output=True).returncode, 0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "navigation.js").write_text("original\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            actual_head = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                  cwd=root, text=True).strip()
            (root / "navigation.js").write_text("changed\n")
            mock_gh = 'gh() { printf "%s\\n" "$LIVE_MAIN"; }\n'
            for current_main, expected in ((actual_head, 0), ("stale-sha", 1), ("", 1)):
                with self.subTest(current_main=current_main):
                    env = dict(os.environ, GITHUB_REPOSITORY="example/repo",
                               LIVE_MAIN=current_main)
                    result = subprocess.run(["bash", "-c", mock_gh + script],
                                            cwd=root, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected,
                                     result.stdout + result.stderr)
            (root / "navigation.js").write_text("original\n")
            env = dict(os.environ, GITHUB_REPOSITORY="example/repo", LIVE_MAIN="stale-sha")
            result = subprocess.run(["bash", "-c", mock_gh + script],
                                    cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_final_ai_commit_tree_matches_original_proposal(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(encoding="utf-8")
        block = workflow.split("      - name: Publish reviewed-by-CI patch as draft PR\n", 1)[1]
        script = block.split("        run: |\n", 1)[1]
        validator = script.split(
            "          # Recheck the actual commit tree, not just the pre-commit index.\n", 1
        )[1].split("          # main can advance after the earlier stale-base check and tests.", 1)[0]
        validator = "\n".join(line[10:] if line.startswith("          ") else line
                              for line in validator.splitlines())
        syntax = subprocess.run(["bash", "-n"], input=validator,
                                text=True, capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "navigation.js").write_bytes(b"old\n")
            (root / "index.html").write_bytes(b"unchanged\n")
            subprocess.run(["git", "add", "navigation.js", "index.html"],
                           cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            dispatch_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            env = dict(os.environ, GITHUB_SHA=dispatch_sha)
            (root / "navigation.js").write_bytes(b"new\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "AI test commit"], cwd=root, check=True)
            good = hashlib.sha256(b"new\n").hexdigest()
            report = root / "ai_repair_proposal.json"
            cases = (
                ("valid", ["navigation.js"], {"navigation.js": good}, True),
                ("tampered-digest", ["navigation.js"], {"navigation.js": "0"*64}, False),
                ("missing-file", ["index.html"], {"index.html": good}, False),
                ("extra-claimed-file", ["navigation.js", "index.html"],
                 {"navigation.js": good, "index.html": good}, False),
            )
            for label, claimed, digests, expected in cases:
                with self.subTest(case=label):
                    report.write_text(json.dumps({
                        "status": "proposed", "changed_files": claimed,
                        "file_sha256": digests, "production_change_allowed": False
                    }))
                    outcome = subprocess.run(["bash", "-c", "set -euo pipefail\n" + validator],
                                             cwd=root, env=env, text=True, capture_output=True)
                    self.assertEqual(outcome.returncode == 0, expected,
                                     label + outcome.stdout + outcome.stderr)
            # A correct patch on a different dispatch base is not acceptable.
            report.write_text(json.dumps({
                "status": "proposed", "changed_files": ["navigation.js"],
                "file_sha256": {"navigation.js": good},
                "production_change_allowed": False
            }))
            bad_env = dict(env, GITHUB_SHA="0" * 40)
            outcome = subprocess.run(["bash", "-c", "set -euo pipefail\n" + validator],
                                     cwd=root, env=bad_env, text=True, capture_output=True)
            self.assertNotEqual(outcome.returncode, 0,
                                "Commit parent must equal dispatch main SHA")
            # A commit containing two files must be rejected even if its report
            # claims only one of them.
            (root / "index.html").write_bytes(b"unexpected\n")
            subprocess.run(["git", "add", "index.html"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "unreviewed extra"], cwd=root, check=True)
            report.write_text(json.dumps({
                "status": "proposed", "changed_files": ["navigation.js"],
                "file_sha256": {"navigation.js": good},
                "production_change_allowed": False
            }))
            outcome = subprocess.run(["bash", "-c", "set -euo pipefail\n" + validator],
                                     cwd=root, env=env, text=True, capture_output=True)
            self.assertNotEqual(outcome.returncode, 0,
                                "Extra committed files must be rejected")

    def test_prepush_staged_ai_content_matches_evidence(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(encoding="utf-8")
        block = workflow.split("      - name: Publish reviewed-by-CI patch as draft PR\n", 1)[1]
        block = block.split("      - name: Archive proposal\n", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        validator = script.split("          # Compare the exact staged bytes to the recorded AI evidence before push.\n", 1)[1]
        validator = validator.split("          git commit -m", 1)[0]
        validator = "\n".join(line[10:] if line.startswith("          ") else line
                              for line in validator.splitlines())
        syntax = subprocess.run(["bash", "-n"], input=validator,
                                text=True, capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            file = root / "navigation.js"
            file.write_bytes(b"before\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            file.write_bytes(b"reviewed\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            report = root / "ai_repair_proposal.json"
            good = hashlib.sha256(b"reviewed\n").hexdigest()
            cases = (
                ("valid", "proposed", {"navigation.js": good}, True),
                ("tampered-content", "proposed", {"navigation.js": "0" * 64}, False),
                ("missing-evidence", "proposed", {}, False),
                ("no-safe-patch", "no_safe_patch", {"navigation.js": good}, False),
            )
            for label, status, digests, expected in cases:
                with self.subTest(case=label):
                    report.write_text(json.dumps({
                        "status": status, "changed_files": ["navigation.js"],
                        "production_change_allowed": False, "file_sha256": digests
                    }))
                    result = subprocess.run(["bash", "-c", "set -euo pipefail\n" + validator],
                                            cwd=root, text=True, capture_output=True)
                    self.assertEqual(result.returncode == 0, expected,
                                     label + result.stdout + result.stderr)
            file.write_bytes(b"post-stage-unreviewed\n")
            report.write_text(json.dumps({
                "status": "proposed", "changed_files": ["navigation.js"],
                "production_change_allowed": False,
                "file_sha256": {"navigation.js": good}
            }))
            result = subprocess.run(["bash", "-c", "set -euo pipefail\n" + validator],
                                    cwd=root, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0,
                                "Working tree changed after staging must be rejected")
            # A benign working-tree copy cannot sanitize a different index
            # blob: git commit writes the index, not the working tree.
            file.write_bytes(b"malicious-index-bytes\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            file.write_bytes(b"reviewed\n")
            result = subprocess.run(["bash", "-c", "set -euo pipefail\n" + validator],
                                    cwd=root, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0,
                                "Index content must be hashed, not just working-tree bytes")
            # Reject mode-only tampering on a file with otherwise correct bytes.
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "update-index", "--chmod=+x", "navigation.js"],
                           cwd=root, check=True)
            result = subprocess.run(["bash", "-c", "set -euo pipefail\n" + validator],
                                    cwd=root, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0,
                                "Unexpected executable mode must be rejected")

    def test_ai_publish_step_shell_syntax(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(encoding="utf-8")
        block = workflow.split("      - name: Publish reviewed-by-CI patch as draft PR\n", 1)[1]
        block = block.split("      - name: Archive proposal\n", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        check = subprocess.run(["bash", "-n"], input=script,
                               text=True, capture_output=True, check=False)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn("gh pr create --draft", script)

    def test_published_ai_evidence_binds_exact_commit_and_parent(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(encoding="utf-8")
        block = workflow.split("      - name: Publish reviewed-by-CI patch as draft PR\n", 1)[1]
        block = block.split("      - name: Archive proposal\n", 1)[0]
        self.assertIn("AI_PUBLISHED_SHA=\"$(git rev-parse HEAD)\"", block)
        self.assertIn("AI_PUBLISHED_BASE=\"$(git rev-parse HEAD^)\"", block)
        code = block.split("          import json, os, re\n", 1)[1].split("          PY\n", 1)[0]
        code = "import json, os, re\n" + "\n".join(
            line[10:] if line.startswith("          ") else line for line in code.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "ai_repair_proposal.json"
            good = {"status": "proposed", "changed_files": ["navigation.js"],
                    "file_sha256": {"navigation.js": "a" * 64}}
            for label, status, branch, head, expected in (
                ("valid", "proposed", "ai/repair-123", "a" * 40, True),
                ("not-proposed", "no_safe_patch", "ai/repair-123", "a" * 40, False),
                ("wrong-branch", "proposed", "ai/repair-other", "a" * 40, False),
                ("wrong-head", "proposed", "ai/repair-123", "not-sha", False),
            ):
                with self.subTest(case=label):
                    report.write_text(json.dumps({**good, "status": status}))
                    env = dict(os.environ, AI_PUBLISHED_BRANCH=branch,
                               AI_PUBLISHED_SHA=head, AI_PUBLISHED_BASE="b" * 40)
                    result = subprocess.run(["python", "-c", code], cwd=root, env=env,
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode == 0, expected,
                                     result.stdout + result.stderr)
                    if expected:
                        saved = json.loads(report.read_text())
                        self.assertEqual(saved["published_branch"], branch)
                        self.assertEqual(saved["published_head_sha"], head)
                        self.assertEqual(saved["published_base_sha"], "b" * 40)

    def test_ai_push_rejects_main_advance_after_commit(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(
            encoding="utf-8")
        publish = workflow.split(
            "      - name: Publish reviewed-by-CI patch as draft PR\n", 1)[1]
        guard = publish.split(
            "          # main can advance after the earlier stale-base check and tests.\n", 1
        )[1].split(
            "          # checkout uses persist-credentials:false", 1
        )[0]
        guard = "\n".join(line[10:] if line.startswith("          ") else line
                          for line in guard.splitlines())
        script = (
            'set -euo pipefail\n'
            'gh() { if [[ "$1" == "api" ]]; then printf "%s\\n" "$MOCK_MAIN"; '
            'else return 2; fi; }\n' + guard
        )
        syntax = subprocess.run(["bash", "-n"], input=script,
                                text=True, capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"],
                           cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"],
                           cwd=root, check=True)
            file = root / "navigation.js"
            file.write_bytes(b"original\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "main"], cwd=root, check=True)
            main_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            file.write_bytes(b"reviewed change\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "proposal"], cwd=root, check=True)
            for label, live, dispatched, expected in (
                ("matches", main_sha, main_sha, True),
                ("main-advanced", "1" * 40, main_sha, False),
                ("wrong-dispatch-base", main_sha, "2" * 40, False),
                ("missing-main", "", main_sha, False),
            ):
                with self.subTest(case=label):
                    env = dict(os.environ, MOCK_MAIN=live,
                               GITHUB_SHA=dispatched,
                               GITHUB_REPOSITORY="example/repo")
                    result = subprocess.run(["bash", "-c", script], cwd=root,
                                            env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode == 0, expected,
                                     label + result.stdout + result.stderr)

    def test_review_artifact_is_required_for_successful_proposal_run(self):
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(
            encoding="utf-8")
        archive = workflow.split("      - name: Archive proposal\n", 1)[1]
        self.assertIn("        if: always()\n", archive)
        self.assertIn("          name: ai-repair-proposal-${{ github.run_id }}\n", archive)
        self.assertIn("          path: ai_repair_proposal.json\n", archive)
        self.assertIn("          if-no-files-found: error\n", archive)
        self.assertNotIn("          if-no-files-found: warn\n", archive)

    def test_full_publish_script_offline_with_local_git_remote(self):
        """Run the REAL publish shell, but stub gh and use a local Git remote."""
        workflow = Path(".github/workflows/ai-repair-proposal.yml").read_text(
            encoding="utf-8")
        block = workflow.split(
            "      - name: Publish reviewed-by-CI patch as draft PR\n", 1
        )[1].split("      - name: Archive proposal\n", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        script = "\n".join(
            line[10:] if line.startswith("          ") else line
            for line in script.splitlines()
        )
        self.assertEqual(
            subprocess.run(["bash", "-n"], input=script,
                           text=True, capture_output=True).returncode, 0
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            remote = base / "remote.git"
            root = base / "candidate"
            root.mkdir()
            subprocess.run(["git", "init", "--bare", "-q", str(remote)],
                           check=True)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"],
                           cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"],
                           cwd=root, check=True)
            subprocess.run(["git", "remote", "add", "origin", str(remote)],
                           cwd=root, check=True)
            for name in ("index.html", "navigation.js", "secondary_navigation.js"):
                (root / name).write_text("original\n", encoding="utf-8")
            subprocess.run(["git", "add", "--", "index.html", "navigation.js",
                            "secondary_navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            original = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            (root / "navigation.js").write_text("reviewed change\n", encoding="utf-8")
            digest = hashlib.sha256(b"reviewed change\n").hexdigest()
            report = root / "ai_repair_proposal.json"
            report.write_text(json.dumps({
                "status": "proposed", "changed_files": ["navigation.js"],
                "file_sha256": {"navigation.js": digest},
                "production_change_allowed": False,
            }), encoding="utf-8")
            bin_dir = base / "bin"
            bin_dir.mkdir()
            fake_gh = bin_dir / "gh"
            fake_gh.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "case \"$1 $2\" in\n"
                "  'api repos/example/repo/git/ref/heads/main')"
                " printf '%s\\n' \"$MOCK_LIVE_MAIN\" ;;\n"
                "  'auth setup-git') exit 0 ;;\n"
                "  'pr create') printf '%s\\n' 'fake draft PR'; exit 0 ;;\n"
                "  *) echo \"unexpected gh invocation: $*\" >&2; exit 9 ;;\n"
                "esac\n"
            )
            fake_gh.chmod(0o755)
            summary = base / "summary"
            env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
                       GITHUB_SHA=original, MOCK_LIVE_MAIN=original,
                       GITHUB_RUN_ID="980123", GITHUB_REPOSITORY="example/repo",
                       GH_TOKEN="offline-fixture", AI_ISSUE="navigation issue",
                       GITHUB_STEP_SUMMARY=str(summary))
            result = subprocess.run(["bash", "-c", script], cwd=root, env=env,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            branch = "ai/repair-980123"
            remote_head = subprocess.check_output(
                ["git", "--git-dir", str(remote), "rev-parse", "refs/heads/" + branch],
                text=True
            ).strip()
            published = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(published["published_branch"], branch)
            self.assertEqual(published["published_head_sha"], remote_head)
            self.assertEqual(published["published_base_sha"], original)
            self.assertFalse(published["production_change_allowed"])
            self.assertEqual(subprocess.check_output(
                ["git", "--git-dir", str(remote), "show", remote_head + ":navigation.js"]
            ), b"reviewed change\n")
            self.assertEqual(subprocess.check_output(
                ["git", "--git-dir", str(remote), "diff-tree", "--no-commit-id",
                 "--name-only", "-r", remote_head], text=True
            ).splitlines(), ["navigation.js"])
            self.assertIn("Review-ready draft PR created", summary.read_text())
            # The published commit must not include the evidence report itself.
            names = subprocess.check_output(
                ["git", "--git-dir", str(remote), "ls-tree", "-r", "--name-only",
                 remote_head], text=True
            ).splitlines()
            self.assertNotIn("ai_repair_proposal.json", names)

    def test_no_api_key_no_network(self):
        with tempfile.TemporaryDirectory() as directory:
            def forbidden(*args,**kwargs):
                raise AssertionError("network unexpectedly called")
            self.assertEqual(propose("fix navigation",directory,None,"test",forbidden)["status"],"disabled")


if __name__ == "__main__":
    unittest.main()
