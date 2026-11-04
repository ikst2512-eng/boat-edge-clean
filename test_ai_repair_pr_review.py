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
            jobs = {"total_count": 2,
                    "jobs": [{"name": "tests", "status": "completed", "conclusion": "success"},
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
                    jobs_file.write_text(json.dumps({
                        "total_count": len(proposed_jobs), "jobs": proposed_jobs
                    }))
                    result = subprocess.run(["python", "-c", validator], env=env,
                                            text=True, capture_output=True)
                    self.assertNotEqual(result.returncode, 0, label)

            # Both producer safety tests and the publish job must succeed.
            # A success-looking run cannot bypass the original test gate.
            for label, test_jobs in (
                ("tests-skipped", [
                    {"name": "tests", "status": "completed", "conclusion": "skipped"},
                    {"name": "propose", "status": "completed", "conclusion": "success"}]),
                ("tests-failed", [
                    {"name": "tests", "status": "completed", "conclusion": "failure"},
                    {"name": "propose", "status": "completed", "conclusion": "success"}]),
                ("tests-missing", [
                    {"name": "propose", "status": "completed", "conclusion": "success"}]),
                ("tests-duplicate", [
                    {"name": "tests", "status": "completed", "conclusion": "success"},
                    {"name": "tests", "status": "completed", "conclusion": "success"},
                    {"name": "propose", "status": "completed", "conclusion": "success"}]),
                ("tests-not-completed", [
                    {"name": "tests", "status": "in_progress", "conclusion": None},
                    {"name": "propose", "status": "completed", "conclusion": "success"}]),
            ):
                with self.subTest(case=label):
                    run_file.write_text(json.dumps(valid))
                    jobs_file.write_text(json.dumps({
                        "total_count": len(test_jobs), "jobs": test_jobs
                    }))
                    result = subprocess.run(["python", "-c", validator], env=env,
                                            text=True, capture_output=True)
                    self.assertNotEqual(result.returncode, 0, label)

            # Missing, short or forged total_count must fail closed; the
            # reviewer only fetches the first API page of origin jobs.
            run_file.write_text(json.dumps(valid))
            for label, payload in (
                ("missing-total", {"jobs": jobs["jobs"]}),
                ("truncated-page", {"total_count": 101, "jobs": jobs["jobs"]}),
                ("invalid-count", {"total_count": "2", "jobs": jobs["jobs"]}),
            ):
                with self.subTest(case=label):
                    jobs_file.write_text(json.dumps(payload))
                    result = subprocess.run(["python", "-c", validator], env=env,
                                            text=True, capture_output=True)
                    self.assertNotEqual(result.returncode, 0, label)

    def test_independent_review_checkout_must_match_exact_candidate_sha(self):
        workflow = self.source()
        block = workflow.split(
            "      - name: Verify checked-out candidate commit is the approved SHA\n", 1
        )[1].split("      - name: Validate changed-file allowlist\n", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        check = subprocess.run(["bash", "-n"], input=script, text=True,
                               capture_output=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"],
                           cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            candidate = root / "navigation.js"
            candidate.write_text("baseline\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            current = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            for label, sha, dirty, expected in (
                ("exact", current, False, True),
                ("wrong-commit", "f" * 40, False, False),
                ("missing-sha", "", False, False),
                ("modified-worktree", current, True, False),
            ):
                with self.subTest(case=label):
                    candidate.write_text("modified\n" if dirty else "baseline\n")
                    env = dict(os.environ, EXPECTED_PR_SHA=sha)
                    result = subprocess.run(["bash", "-c", script],
                                            cwd=root, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode == 0, expected,
                                     label + result.stdout + result.stderr)

    def test_independent_reviewer_rejects_three_modified_files(self):
        workflow = self.source()
        block = workflow.split(
            "      - name: Validate changed-file allowlist\n", 1
        )[1].split(
            "      - name: Match proposed PR to originating AI report artifact\n", 1
        )[0]
        python_code = block.split("          python - <<'PY'\n", 1)[1].split(
            "          PY\n", 1
        )[0]
        python_code = "\n".join(
            line[10:] if line.startswith("          ") else line
            for line in python_code.splitlines()
        )
        python_code = python_code.replace(
            "Path('/tmp/changed.json')", "Path(os.environ['MOCK_CHANGED'])"
        )
        python_code = "import os\n" + python_code
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "changed.json"
            env = dict(os.environ, MOCK_CHANGED=str(file))
            for label, names, allowed in (
                ("one", ["navigation.js"], True),
                ("two", ["navigation.js", "index.html"], True),
                ("three", ["navigation.js", "index.html", "secondary_navigation.js"], False),
            ):
                with self.subTest(case=label):
                    file.write_text(json.dumps([
                        {"filename": name, "status": "modified"} for name in names
                    ]))
                    result = subprocess.run(
                        ["python", "-c", python_code], env=env,
                        capture_output=True, text=True
                    )
                    self.assertEqual(result.returncode == 0, allowed,
                                     label + result.stderr)

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
            (root / "navigation.js").write_bytes(b"original")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "main"], cwd=root, check=True)
            (root / "navigation.js").write_bytes(b"reviewed-ai-change")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "candidate"], cwd=root, check=True)
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
            report_file.write_text(json.dumps(valid_report))
            changed_file.write_text(json.dumps(valid_files))
            # The exact same file bytes must not permit an executable file.
            subprocess.run(["git", "update-index", "--chmod=+x", "navigation.js"],
                           cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "unexpected executable mode"],
                           cwd=root, check=True)
            executable = subprocess.run(["python", "-c", code], cwd=root, env=env,
                                        text=True, capture_output=True)
            self.assertNotEqual(executable.returncode, 0, "Executable mode must fail")
            # A symlink can resolve to the expected bytes; still reject its type.
            (root / "payload").write_bytes(b"reviewed-ai-change")
            (root / "navigation.js").unlink()
            (root / "navigation.js").symlink_to("payload")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "unexpected symlink"],
                           cwd=root, check=True)
            symlink = subprocess.run(["python", "-c", code], cwd=root, env=env,
                                     text=True, capture_output=True)
            self.assertNotEqual(symlink.returncode, 0, "Symlink must fail")

    def test_real_git_candidate_artifact_contract_end_to_end_offline(self):
        """Verify a real candidate commit against its exact local evidence."""
        workflow = self.source()
        block = workflow.split(
            "      - name: Match proposed PR to originating AI report artifact\n", 1
        )[1].split("      - name: Re-run independent UI and navigation tests\n", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        code = script.split("          python - <<'PY'\n", 1)[1].split(
            "          PY\n", 1)[0]
        code = "\n".join(line[10:] if line.startswith("          ") else line
                         for line in code.splitlines())
        code = code.replace(
            "Path('/tmp/ai-source-evidence/ai_repair_proposal.json')",
            "Path(os.environ['MOCK_REPORT'])"
        ).replace(
            "Path('/tmp/changed.json')", "Path(os.environ['MOCK_CHANGED'])"
        ).replace(
            "Path('/tmp/pr.json')", "Path(os.environ['MOCK_PR'])"
        )
        code = "import os\n" + code
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"],
                           cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"],
                           cwd=root, check=True)
            file = root / "navigation.js"
            file.write_bytes(b"original\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "main"], cwd=root, check=True)
            parent = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            file.write_bytes(b"reviewed change\n")
            subprocess.run(["git", "add", "navigation.js"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm",
                            "AI: propose narrow UI repair for review"],
                           cwd=root, check=True)
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            report = root / "proposal.json"
            pr_file = root / "pr.json"
            changed_file = root / "changed.json"
            digest = hashlib.sha256(b"reviewed change\n").hexdigest()
            original_report = {
                "status": "proposed", "changed_files": ["navigation.js"],
                "file_sha256": {"navigation.js": digest},
                "published_branch": "ai/repair-980123",
                "published_head_sha": head, "published_base_sha": parent,
                "production_change_allowed": False,
            }
            pr_file.write_text(json.dumps({
                "head": {"ref": "ai/repair-980123", "sha": head},
                "base": {"ref": "main", "sha": parent},
            }))
            changed_file.write_text(json.dumps([
                {"filename": "navigation.js", "status": "modified"}
            ]))
            env = dict(os.environ, MOCK_REPORT=str(report),
                       MOCK_CHANGED=str(changed_file), MOCK_PR=str(pr_file))
            for label, overrides, expected in (
                ("exact-real-git", {}, True),
                ("wrong-published-head", {"published_head_sha": "0"*40}, False),
                ("wrong-published-parent", {"published_base_sha": "1"*40}, False),
                ("wrong-file-hash", {"file_sha256": {"navigation.js": "2"*64}}, False),
                ("extra-report-path", {"changed_files": ["navigation.js", "index.html"]},
                 False),
            ):
                with self.subTest(case=label):
                    report.write_text(json.dumps({**original_report, **overrides}))
                    response = subprocess.run(["python", "-c", code], cwd=root,
                                              env=env, capture_output=True, text=True)
                    self.assertEqual(response.returncode == 0, expected,
                                     label + response.stdout + response.stderr)
            # The API list only mentions navigation.js. An additional
            # changed file in the actual candidate commit must be rejected.
            (root / "index.html").write_text("hidden committed change\\n")
            subprocess.run(["git", "add", "index.html"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "hidden extra file"],
                           cwd=root, check=True)
            report.write_text(json.dumps(original_report))
            hidden = subprocess.run(["python", "-c", code], cwd=root,
                                    env=env, capture_output=True, text=True)
            self.assertNotEqual(hidden.returncode, 0,
                                "Extra Git commit file not listed by the PR API must fail")

    def test_two_file_candidate_artifact_contract_real_git(self):
        """Two legitimate AI-modified files pass; a bad digest never passes."""
        workflow = self.source()
        block = workflow.split(
            "      - name: Match proposed PR to originating AI report artifact\n", 1
        )[1].split("      - name: Re-run independent UI and navigation tests\n", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        code = script.split("          python - <<'PY'\n", 1)[1].split(
            "          PY\n", 1)[0]
        code = "\n".join(
            line[10:] if line.startswith("          ") else line
            for line in code.splitlines()
        )
        for from_path, to_path in (
            ("/tmp/ai-source-evidence/ai_repair_proposal.json", "MOCK_REPORT"),
            ("/tmp/changed.json", "MOCK_CHANGED"),
            ("/tmp/pr.json", "MOCK_PR"),
        ):
            code = code.replace(
                "Path('" + from_path + "')", "Path(os.environ['" + to_path + "'])"
            )
        code = "import os\n" + code
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"],
                           cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"],
                           cwd=root, check=True)
            names = ("navigation.js", "secondary_navigation.js")
            for name in names:
                (root / name).write_text("original\n", encoding="utf-8")
            subprocess.run(["git", "add", "--", *names], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "main"], cwd=root, check=True)
            parent = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            values = {
                "navigation.js": b"safe navigation update\n",
                "secondary_navigation.js": b"safe secondary update\n",
            }
            for name, data in values.items():
                (root / name).write_bytes(data)
            subprocess.run(["git", "add", "--", *names], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "proposed"], cwd=root, check=True)
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            digests = {
                name: hashlib.sha256(data).hexdigest()
                for name, data in values.items()
            }
            report = root / "proposal.json"
            pr = root / "pr.json"
            changed = root / "changed.json"
            original = {
                "status": "proposed",
                "changed_files": list(names),
                "file_sha256": digests,
                "published_branch": "ai/repair-7777",
                "published_head_sha": head,
                "published_base_sha": parent,
                "production_change_allowed": False,
            }
            pr.write_text(json.dumps({
                "head": {"ref": "ai/repair-7777", "sha": head},
                "base": {"sha": parent},
            }))
            changed.write_text(json.dumps([
                {"filename": name, "status": "modified"} for name in names
            ]))
            env = dict(os.environ, MOCK_REPORT=str(report),
                       MOCK_CHANGED=str(changed), MOCK_PR=str(pr))
            for label, overrides, expected in (
                ("valid-two-files", {}, True),
                ("tampered-second-file", {"file_sha256": {
                    **digests, "secondary_navigation.js": "f" * 64}}, False),
                ("missing-second-hash", {"file_sha256": {
                    "navigation.js": digests["navigation.js"]}}, False),
                ("duplicate-second-file", {"changed_files": [
                    "navigation.js", "navigation.js"]}, False),
            ):
                with self.subTest(case=label):
                    report.write_text(json.dumps({**original, **overrides}))
                    check = subprocess.run(
                        ["python", "-c", code], cwd=root, env=env,
                        text=True, capture_output=True
                    )
                    self.assertEqual(check.returncode == 0, expected,
                                     label + check.stdout + check.stderr)

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
