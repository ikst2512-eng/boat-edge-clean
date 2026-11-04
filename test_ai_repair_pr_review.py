"""Guard regression tests for the independent AI draft PR reviewer.

These tests never call GitHub or request paid AI services.
"""
import os
import json
import hashlib
import tempfile
import subprocess
import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/ai-repair-pr-review.yml")


class AIReviewGuardTests(unittest.TestCase):
    def source(self):
        return WORKFLOW.read_text(encoding="utf-8")

    def test_candidate_must_be_one_commit_based_on_current_main(self):
        workflow = self.source()
        self.assertIn('p[\'commits\']!=1', workflow)
        self.assertIn("len(parents)!=1 or parents[0].get('sha')!=main", workflow)
        self.assertIn("p['base']['sha']!=main", workflow)
        self.assertIn("f.write('main_sha='+main+", workflow)
        self.assertIn('if [[ "${GITHUB_REF}" != "refs/heads/main" ]]', workflow)

    def test_current_main_parent_and_draft_candidate_with_api_fixtures(self):
        """Execute the actual inline validators on mocked GitHub API replies."""
        workflow = self.source()
        step = workflow.split("      - name: Verify candidate PR is draft and from local AI branch\n", 1)[1]
        script = step.split("        run: |\n", 1)[1].split("      - uses: actions/checkout@v4", 1)[0]
        first = script.split('head_sha="$(python - <<\'PY\'\n', 1)[1].split("          PY\n", 1)[0]
        after = script.split('          gh api "repos/${GITHUB_REPOSITORY}/git/ref/heads/main" > /tmp/main-ref.json\n', 1)[1]
        second = after.split("          python - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
        first = "\n".join(line[10:] if line.startswith("          ") else line for line in first.splitlines())
        second = "\n".join(line[10:] if line.startswith("          ") else line for line in second.splitlines())

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pr_path = root / "pr.json"
            commit_path = root / "commit.json"
            main_path = root / "main.json"
            output = root / "output"
            first = first.replace("Path('/tmp/pr.json')", "Path(os.environ['MOCK_PR'])")
            second = (second.replace("Path('/tmp/pr.json')", "Path(os.environ['MOCK_PR'])")
                      .replace("Path('/tmp/head-commit.json')", "Path(os.environ['MOCK_COMMIT'])")
                      .replace("Path('/tmp/main-ref.json')", "Path(os.environ['MOCK_MAIN'])"))
            env = dict(os.environ, GITHUB_REPOSITORY="example/repo",
                       GITHUB_OUTPUT=str(output), MOCK_PR=str(pr_path),
                       MOCK_COMMIT=str(commit_path), MOCK_MAIN=str(main_path))
            cases = (
                ("valid", "main-a", ["main-a"], 1, True, True),
                ("stale-parent", "main-a", ["old-main"], 1, True, False),
                ("stale-base", "old-main", ["main-a"], 1, True, False),
                ("multi-parent", "main-a", ["main-a", "other"], 1, True, False),
                ("multi-commit", "main-a", ["main-a"], 2, True, False),
                ("non-draft", "main-a", ["main-a"], 1, False, False),
            )
            for label, base, parents, count, draft, expected in cases:
                with self.subTest(case=label):
                    output.write_text("")
                    pr_path.write_text(json.dumps({
                        "state": "open", "draft": draft, "commits": count,
                        "head": {"repo": {"full_name": "example/repo"},
                                 "ref": "ai/repair-42", "sha": "head-a"},
                        "base": {"ref": "main", "sha": base}
                    }))
                    commit_path.write_text(json.dumps({
                        "sha": "head-a", "parents": [{"sha": v} for v in parents],
                        "commit": {"message": "AI: propose narrow UI repair for review"},
                        "author": {"login": "github-actions[bot]"},
                        "committer": {"login": "github-actions[bot]"}
                    }))
                    main_path.write_text(json.dumps({"object": {"sha": "main-a"}}))
                    precheck = subprocess.run(["python", "-c", first], env=env,
                                              text=True, capture_output=True)
                    if not expected and (count != 1 or not draft):
                        self.assertNotEqual(precheck.returncode, 0, label)
                        continue
                    self.assertEqual(precheck.returncode, 0, precheck.stderr)
                    decision = subprocess.run(["python", "-c", second], env=env,
                                              text=True, capture_output=True)
                    self.assertEqual(decision.returncode == 0, expected,
                                     label + decision.stdout + decision.stderr)
                    if expected:
                        self.assertIn("sha=head-a", output.read_text())
                        self.assertIn("main_sha=main-a", output.read_text())

            # Valid parent/main alone does not suffice: reject forged provenance.
            for field, replacement in (
                ("author", {"login": "someone-else"}),
                ("committer", {"login": "someone-else"}),
                ("commit", {"message": "unrelated change"}),
            ):
                with self.subTest(provenance=field):
                    output.write_text("")
                    pr_path.write_text(json.dumps({
                        "state": "open", "draft": True, "commits": 1,
                        "head": {"repo": {"full_name": "example/repo"},
                                 "ref": "ai/repair-42", "sha": "head-a"},
                        "base": {"ref": "main", "sha": "main-a"}
                    }))
                    payload = {
                        "sha": "head-a", "parents": [{"sha": "main-a"}],
                        "commit": {"message": "AI: propose narrow UI repair for review"},
                        "author": {"login": "github-actions[bot]"},
                        "committer": {"login": "github-actions[bot]"}
                    }
                    payload[field] = replacement
                    commit_path.write_text(json.dumps(payload))
                    main_path.write_text(json.dumps({"object": {"sha": "main-a"}}))
                    result = subprocess.run(["python", "-c", second], env=env,
                                            text=True, capture_output=True)
                    self.assertNotEqual(result.returncode, 0, field)

    def test_ai_proposal_workflow_run_provenance_fixtures(self):
        workflow = self.source()
        block = workflow.split("      - name: Verify completed AI proposal workflow provenance\n", 1)[1]
        block = block.split("      - uses: actions/checkout@v4", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        snippets = script.split("          python - <<'PY'\n")
        self.assertEqual(len(snippets), 2)
        validator = snippets[1].split("          PY\n", 1)[0]
        validator = "\n".join(line[10:] if line.startswith("          ") else line
                              for line in validator.splitlines())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pr_file, run_file = root / "pr.json", root / "run.json"
            jobs_file = root / "jobs.json"
            validator = validator.replace("Path('/tmp/ai-proposal-run.json')",
                                          "Path(os.environ['MOCK_RUN'])")
            validator = validator.replace("Path('/tmp/ai-proposal-jobs.json')",
                                          "Path(os.environ['MOCK_JOBS'])")
            validator = validator.replace("Path('/tmp/pr.json')",
                                          "Path(os.environ['MOCK_PR'])")
            pr_file.write_text(json.dumps({"head": {"ref": "ai/repair-321"}}))
            env = dict(os.environ, MOCK_PR=str(pr_file), MOCK_RUN=str(run_file),
                       MOCK_JOBS=str(jobs_file), CHECKED_MAIN_SHA="base-a",
                       GITHUB_REPOSITORY="example/repo")
            valid = {"id": 321, "event": "workflow_dispatch",
                     "path": ".github/workflows/ai-repair-proposal.yml",
                     "head_branch": "main", "head_sha": "base-a",
                     "status": "completed", "conclusion": "success",
                     "repository": {"full_name": "example/repo"}}
            cases = (
                ("valid", {}, True),
                ("wrong-run-id", {"id": 322}, False),
                ("pr-trigger", {"event": "pull_request"}, False),
                ("wrong-workflow", {"path": ".github/workflows/other.yml"}, False),
                ("feature-branch", {"head_branch": "other"}, False),
                ("stale-sha", {"head_sha": "old"}, False),
                ("in-progress", {"status": "in_progress"}, False),
                ("failure", {"conclusion": "failure"}, False),
                ("wrong-repository", {"repository": {"full_name": "other/repo"}}, False),
            )
            jobs = {"jobs": [{"name": "tests", "status": "completed", "conclusion": "success"},
                             {"name": "propose", "status": "completed", "conclusion": "success"}]}
            jobs_file.write_text(json.dumps(jobs))
            for label, overrides, expected in cases:
                with self.subTest(case=label):
                    run_file.write_text(json.dumps({**valid, **overrides}))
                    result = subprocess.run(["python", "-c", validator], env=env,
                                            text=True, capture_output=True)
                    self.assertEqual(result.returncode == 0, expected,
                                     label + result.stdout + result.stderr)
            # Workflow run success is insufficient when the publish/propose job
            # was skipped or failed, or its page of jobs is incomplete.
            for label, proposed_jobs in (
                ("propose-skipped", [{"name": "propose", "status": "completed", "conclusion": "skipped"}]),
                ("propose-failed", [{"name": "propose", "status": "completed", "conclusion": "failure"}]),
                ("propose-in-progress", [{"name": "propose", "status": "in_progress", "conclusion": None}]),
                ("propose-missing", [{"name": "tests", "status": "completed", "conclusion": "success"}]),
                ("propose-duplicate", [{"name": "propose", "status": "completed", "conclusion": "success"}] * 2),
            ):
                with self.subTest(case=label):
                    run_file.write_text(json.dumps(valid))
                    jobs_file.write_text(json.dumps({"jobs": proposed_jobs}))
                    result = subprocess.run(["python", "-c", validator], env=env,
                                            text=True, capture_output=True)
                    self.assertNotEqual(result.returncode, 0, label)

    def test_ai_source_artifact_matches_candidate_pr_files(self):
        workflow = self.source()
        block = workflow.split("      - name: Match proposed PR to originating AI report artifact\n", 1)[1]
        block = block.split("      - name: Re-run independent UI and navigation tests\n", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        self.assertIn("gh run download", script)
        self.assertIn("ai-repair-proposal-", script)
        code = script.split("          python - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
        code = "\n".join(line[10:] if line.startswith("          ") else line
                         for line in code.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_file = root / "ai_repair_proposal.json"
            changed_file = root / "changed.json"
            pr_file = root / "pr.json"
            code = code.replace("Path('/tmp/ai-source-evidence/ai_repair_proposal.json')",
                                "Path(os.environ['MOCK_REPORT'])")
            code = code.replace("Path('/tmp/changed.json')",
                                "Path(os.environ['MOCK_CHANGED'])")
            code = code.replace("Path('/tmp/pr.json')",
                                "Path(os.environ['MOCK_PR'])")
            code = "import os\n" + code
            (root / "navigation.js").write_bytes(b"reviewed-ai-change")
            pr_file.write_text(json.dumps({
                "head": {"ref": "ai/repair-321", "sha": "a" * 40},
                "base": {"sha": "b" * 40}
            }))
            env = dict(os.environ, MOCK_REPORT=str(report_file),
                       MOCK_CHANGED=str(changed_file), MOCK_PR=str(pr_file))
            valid_report = {"status": "proposed",
                            "published_branch": "ai/repair-321",
                            "published_head_sha": "a" * 40,
                            "published_base_sha": "b" * 40,
                            "production_change_allowed": False,
                            "changed_files": ["navigation.js"],
                            "file_sha256": {"navigation.js": hashlib.sha256(
                                b"reviewed-ai-change").hexdigest()}}
            valid_files = [{"filename": "navigation.js", "status": "modified"}]
            cases = (
                ("valid", {}, valid_files, True),
                ("no-patch-run", {"status": "no_safe_patch", "changed_files": []},
                 valid_files, False),
                ("disabled", {"status": "disabled"}, valid_files, False),
                ("wrong-file", {"changed_files": ["index.html"]}, valid_files, False),
                ("tampered-file-digest", {"file_sha256": {"navigation.js": "0"*64}},
                 valid_files, False),
                ("missing-digest", {"file_sha256": {}}, valid_files, False),
                ("different-branch", {"published_branch": "ai/repair-322"}, valid_files, False),
                ("different-head", {"published_head_sha": "c" * 40}, valid_files, False),
                ("different-base", {"published_base_sha": "c" * 40}, valid_files, False),
                ("missing-published-sha", {"published_head_sha": None}, valid_files, False),
                ("duplicate-files", {"changed_files": ["navigation.js", "navigation.js"]},
                 valid_files, False),
                ("production-allowed", {"production_change_allowed": True}, valid_files, False),
                ("extra-pr-file", {}, valid_files +
                 [{"filename": "index.html", "status": "modified"}], False),
                ("deleted-pr-file", {}, [{"filename": "navigation.js", "status": "removed"}], False),
            )
            for label, changes, files, expected in cases:
                with self.subTest(case=label):
                    report_file.write_text(json.dumps({**valid_report, **changes}))
                    changed_file.write_text(json.dumps(files))
                    result = subprocess.run(["python", "-c", code], cwd=root, env=env,
                                            text=True, capture_output=True)
                    self.assertEqual(result.returncode == 0, expected,
                                     label + result.stdout + result.stderr)

    def test_independent_tests_reject_tracked_checkout_mutation(self):
        workflow = self.source()
        segment = workflow.split("      - name: Re-run independent UI and navigation tests\n", 1)[1]
        segment = segment.split("      - name: Check PR head did not change during validation\n", 1)[0]
        script = segment.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        mocked_tests = """python() { return 0; }
node() {
  if [[ "$MUTATE" == "1" ]]; then
    printf '%s\\n' 'unreviewed-change' > navigation.js
  fi
}
"""
        script = mocked_tests + script
        check = subprocess.run(["bash", "-n"], input=script,
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"],
                           cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"],
                           cwd=root, check=True)
            (root / "navigation.js").write_text("candidate-source\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "candidate"], cwd=root, check=True)
            for label, mutate, dirty_before, expected in (
                ("clean", False, False, 0),
                ("modified-by-tests", True, False, 1),
                ("preexisting-staged", False, True, 1),
            ):
                with self.subTest(label=label):
                    subprocess.run(["git", "reset", "--hard", "-q", "HEAD"],
                                   cwd=root, check=True)
                    if dirty_before:
                        (root / "navigation.js").write_text("staged-change\n")
                        subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
                    env = dict(os.environ, MUTATE="1" if mutate else "0")
                    result = subprocess.run(["bash", "-c", script], cwd=root, env=env,
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected,
                                     label + result.stdout + result.stderr)

    def test_final_head_main_and_draft_state_race_guard(self):
        workflow = self.source()
        block = workflow.split("      - name: Check PR head did not change during validation\n", 1)[1]
        block = block.split("      - name: Review note\n", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        script = script.replace("'/tmp/final-ai-pr.json'",
                                "os.environ['MOCK_FINAL_PR']")
        mock_gh = """gh() {
          case "$*" in
            *"/pulls/"*) cat "$MOCK_FINAL_PR" ;;
            *"/git/ref/heads/main"*) printf '%s\\n' "$LIVE_MAIN" ;;
            *) return 2 ;;
          esac
        }
        """
        command = mock_gh + "\n" + script
        syntax = subprocess.run(["bash", "-n"], input=command, text=True,
                                capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        cases = (
            ("valid", "head-a", "main-a", "open", True, "main-a", 1, 0),
            ("changed-head", "head-b", "main-a", "open", True, "main-a", 1, 1),
            ("changed-main", "head-a", "main-b", "open", True, "main-a", 1, 1),
            ("missing-main", "head-a", "", "open", True, "main-a", 1, 1),
            ("closed", "head-a", "main-a", "closed", True, "main-a", 1, 1),
            ("ready", "head-a", "main-a", "open", False, "main-a", 1, 1),
            ("changed-base", "head-a", "main-a", "open", True, "main-b", 1, 1),
            ("multiple-commits", "head-a", "main-a", "open", True, "main-a", 2, 1),
            ("invalid-run-branch", "head-a", "main-a", "open", True, "main-a", 1, 1),
        )
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "final-pr.json"
            for label, head, main, state, draft, base, count, expected in cases:
                with self.subTest(case=label):
                    fixture.write_text(json.dumps({
                        "state": state, "draft": draft, "commits": count,
                        "head": {"sha": head, "ref": "ai/repair-not-a-run" if label == "invalid-run-branch" else "ai/repair-42",
                                 "repo": {"full_name": "example/repo"}},
                        "base": {"ref": "main", "sha": base}
                    }))
                    env = dict(os.environ, GITHUB_REPOSITORY="example/repo",
                               PR_NUMBER="42", CHECKED_SHA="head-a",
                               CHECKED_MAIN_SHA="main-a", LIVE_MAIN=main,
                               MOCK_FINAL_PR=str(fixture))
                    result = subprocess.run(["bash", "-c", command], text=True,
                                            capture_output=True, env=env)
                    self.assertEqual(result.returncode, expected,
                                     label + result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
