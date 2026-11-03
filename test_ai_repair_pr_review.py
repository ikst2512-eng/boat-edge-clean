"""Guard regression tests for the independent AI draft PR reviewer.

These tests never call GitHub or request paid AI services.
"""
import os
import json
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
        step = workflow.split("      - name: Verify candidate PR is draft and from local AI branch\\n", 1)[1]
        script = step.split("        run: |\\n", 1)[1].split("      - uses: actions/checkout@v4", 1)[0]
        first = script.split('head_sha="$(python - <<\'PY\'\\n', 1)[1].split("          PY\\n", 1)[0]
        after = script.split("          gh api \\"repos/${GITHUB_REPOSITORY}/git/ref/heads/main\\" > /tmp/main-ref.json\\n", 1)[1]
        second = after.split("          python - <<'PY'\\n", 1)[1].split("          PY\\n", 1)[0]
        first = "\\n".join(line[10:] if line.startswith("          ") else line for line in first.splitlines())
        second = "\\n".join(line[10:] if line.startswith("          ") else line for line in second.splitlines())

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
                ("multi-commit", "main-a", ["main-a"], 2, False, False),
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
                        "sha": "head-a", "parents": [{"sha": v} for v in parents]
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

    def test_final_head_and_main_race_guard(self):
        workflow = self.source()
        block = workflow.split("      - name: Check PR head did not change during validation\n", 1)[1]
        block = block.split("      - name: Review note\n", 1)[0]
        script = block.split("        run: |\n", 1)[1]
        script = "\n".join(line[10:] if line.startswith("          ") else line
                           for line in script.splitlines())
        mock_gh = """gh() {
          case "$*" in
            *"/pulls/"*) printf '%s\\n' "$LIVE_HEAD" ;;
            *"/git/ref/heads/main"*) printf '%s\\n' "$LIVE_MAIN" ;;
            *) return 2 ;;
          esac
        }
        """
        command = mock_gh + "\n" + script
        syntax = subprocess.run(["bash", "-n"], input=command, text=True,
                                capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        for live_head, live_main, expected in (
            ("head-a", "main-a", 0),
            ("head-b", "main-a", 1),
            ("head-a", "main-b", 1),
            ("head-a", "", 1),
        ):
            with self.subTest(live_head=live_head, live_main=live_main):
                env = dict(os.environ, GITHUB_REPOSITORY="example/repo", PR_NUMBER="42",
                           CHECKED_SHA="head-a", CHECKED_MAIN_SHA="main-a",
                           LIVE_HEAD=live_head, LIVE_MAIN=live_main)
                result = subprocess.run(["bash", "-c", command], text=True,
                                        capture_output=True, env=env)
                self.assertEqual(result.returncode, expected,
                                 result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
