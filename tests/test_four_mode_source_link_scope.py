import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.report_four_mode_source_links import report


class SourceLinkScopeTests(unittest.TestCase):
    NOW = datetime(2026, 11, 3, 5, tzinfo=timezone.utc)
    SHA = "a" * 40

    @staticmethod
    def publication(root, outcome, **extra):
        p = root / "four-mode-evidence/publication.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"outcome": outcome, **extra}), encoding="utf-8")

    def test_no_publication_has_no_old_archive_false_negatives(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "four_mode_forecasts").mkdir()
            (root / "four_mode_forecasts/202611030101.json").write_text("{}")
            result = report(root, now=self.NOW, link=lambda *_: self.fail("unexpected link"))
            self.assertEqual(result["checked"], 0)
            self.assertEqual(result["hashes_present"], 0)
            self.assertEqual(result["publication_scope_status"], "no_publication_evidence")

    def test_no_new_candidates_skips_existing_archives(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.publication(root, "no_eligible_candidates")
            result = report(root, now=self.NOW, link=lambda *_: self.fail("unexpected link"))
            self.assertEqual(result["checked"], 0)
            self.assertEqual(result["publication_scope_status"], "no_new_publication")

    def test_pushed_additions_are_only_files_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.publication(root, "pushed_to_main", commit_sha=self.SHA, added_forecasts=2)
            paths = ["four_mode_forecasts/202611030101.json", "four_mode_forecasts/202611030102.json"]
            def git(args):
                return self.SHA if args[:2] == ["rev-parse", "HEAD"] else "\n".join(paths)
            checked = []
            def link(code, *_):
                checked.append(code)
                return {"status": "both_hashes_present" if code.endswith("01") else "incomplete_source_link"}
            result = report(root, now=self.NOW, git=git, link=link)
            self.assertEqual(checked, ["202611030101", "202611030102"])
            self.assertEqual(result["checked"], 2)
            self.assertEqual(result["hashes_present"], 1)
            self.assertFalse(result["formal"])

    def test_mismatch_does_not_report_zero_as_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.publication(root, "pushed_to_main", commit_sha=self.SHA, added_forecasts=1)
            result = report(root, now=self.NOW, git=lambda args: "b" * 40)
            self.assertEqual(result["publication_scope_status"], "invalid_publication_evidence")
            self.assertIsNone(result["checked"])
            self.assertIsNone(result["hashes_present"])

    def test_missing_or_stale_publication_count_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.publication(root, "pushed_to_main", commit_sha=self.SHA, added_forecasts=0)
            result = report(root, now=self.NOW)
            self.assertIsNone(result["checked"])

    def test_failed_publication_is_not_falsely_linked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.publication(root, "failed", stage="push_main")
            result = report(root, now=self.NOW)
            self.assertEqual(result["checked"], 0)
            self.assertEqual(result["publication_scope_status"], "no_new_publication")

    def test_real_cli_module_invocation_handles_noop_capture(self):
        # Regression for 2026-11-03 15:01 JST production failure:
        # calling scripts/report_four_mode_source_links.py directly did not
        # include the repository root in sys.path.
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.publication(root, "no_eligible_candidates")
            env = dict(os.environ)
            env["PYTHONPATH"] = str(repo_root)
            proc = subprocess.run(
                [sys.executable, "-m", "scripts.report_four_mode_source_links"],
                cwd=root, env=env, text=True, capture_output=True, timeout=15)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads((root / "four-mode-evidence/source-links.json").read_text())
            self.assertEqual(data["checked"], 0)
            self.assertEqual(data["hashes_present"], 0)
            self.assertEqual(data["publication_scope_status"], "no_new_publication")


if __name__ == "__main__":
    unittest.main()
