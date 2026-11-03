"""Guard regression tests for the independent AI draft PR reviewer.

These tests never call GitHub or request paid AI services.
"""
import os
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
        self.assertIn('f.write(\'main_sha=\'+main+', workflow)
        self.assertIn('if [[ "${GITHUB_REF}" != "refs/heads/main" ]]', workflow)

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
                env = dict(os.environ, GITHUB_REPOSITORY="example/repo",
                           CHECKED_SHA="head-a", CHECKED_MAIN_SHA="main-a",
                           LIVE_HEAD=live_head, LIVE_MAIN=live_main)
                result = subprocess.run(["bash", "-c", command], text=True,
                                        capture_output=True, env=env)
                self.assertEqual(result.returncode, expected,
                                 result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
