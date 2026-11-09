"""One-day, research-only fallback must not be mistaken for an external timer."""
import unittest
from pathlib import Path

PATH = "tests/fixtures/retired_workflows/t12-kiryu12-upstream-recovery-20261103.yml"
ACTIVE_WORKFLOW_PATH = ".github/workflows/t12-kiryu12-upstream-recovery-20261103.yml"


class KiryuResearchUpstreamRecoveryContract(unittest.TestCase):
    def test_only_actual_successful_upstream_schedule_writes_research_evidence(self):
        self.assertFalse(Path(ACTIVE_WORKFLOW_PATH).exists(), "expired event-driven workflow must remain retired")
        workflow = Path(PATH).read_text()
        self.assertIn("workflow_run:", workflow)
        self.assertIn("types: [completed]", workflow)
        self.assertIn("Four-mode prospective capture (research only)", workflow)
        self.assertIn("CLEAN prospective pre-cutoff capture", workflow)
        self.assertIn("concurrency:", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("workflow_run.event == 'schedule'", workflow)
        self.assertIn("workflow_run.conclusion == 'success'", workflow)
        self.assertIn("workflow_run.conclusion == 'failure'", workflow)
        self.assertNotIn("workflow_run.conclusion == 'cancelled'", workflow)
        self.assertIn("workflow_run.event == 'schedule'", workflow)
        self.assertIn("workflow_run.head_branch == 'main'", workflow)
        self.assertNotIn("\n  schedule:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertIn("202611030112", workflow)
        self.assertIn("scripts.gate_kiryu12_upstream_recovery import check_window", workflow)
        self.assertIn("check_window(datetime.now(timezone.utc)", workflow)
        self.assertIn("UPSTREAM_STARTED_AT", workflow)
        self.assertIn("research-t12-external-evidence", workflow)
        self.assertIn("scripts.run_external_three_t12", workflow)
        self.assertIn("does not prove T12 reliability", workflow)
        self.assertNotIn("git push", workflow)
        self.assertIn("scripts.gate_kiryu12_upstream_recovery import check_window", workflow)
        self.assertIn("python -m scripts.run_external_three_t12", workflow)



class RetiredOneDateWorkflowReferences(unittest.TestCase):
    """Prevent expired Nov 2-3 experiments from being reactivated indirectly."""

    RETIRED = {
        "official-json-t12-oneoff-20261102.yml": "One-date official JSON predeadline evidence (research only)",
        "official-shimonoseki10-joint-oneoff-20261102.yml": "One-date Shimonoseki 10R joint official T12 evidence",
        "t12-kiryu12-upstream-recovery-20261103.yml": "T12 Kiryu12 upstream completion recovery (research only, Nov 3)",
        "official-three-original-t12-reinspect.yml": "Re-audit Toda/Kiryu T12 scheduled original archives (research only)",
    }

    def test_no_expired_job_exists_in_active_workflows(self):
        root = Path(__file__).resolve().parents[1]
        folder = root / ".github" / "workflows"
        self.assertTrue(folder.is_dir())
        for name in self.RETIRED:
            self.assertFalse((folder / name).exists(), name)

    def test_no_other_live_source_or_test_reads_removed_workflow_paths(self):
        # Scan code and tests, not only workflow YAML. Ignore documentation and
        # the frozen historical fixture; those may legitimately name old jobs.
        root = Path(__file__).resolve().parents[1]
        suffixes = {".py", ".js", ".cjs", ".mjs", ".yml", ".yaml"}
        references = []
        for folder in (root, root / "scripts", root / "tests", root / "cloudflare", root / "research"):
            if folder == root:
                files = (p for p in folder.iterdir() if p.is_file())
            elif folder.exists():
                files = folder.rglob("*")
            else:
                continue
            for path in files:
                if not path.is_file() or path.suffix not in suffixes or path == Path(__file__).resolve():
                    continue
                if "fixtures" in path.parts or "__pycache__" in path.parts:
                    continue
                source = path.read_text(encoding="utf-8")
                for basename in self.RETIRED:
                    # Historical tests may read an inert fixture, not an active workflow.
                    if basename in source.replace("tests/fixtures/retired_workflows/" + basename, ""):
                        references.append((str(path.relative_to(root)), basename))
        self.assertEqual([], references, "source still hardcodes retired active workflow")

    def test_no_active_workflow_dispatches_or_triggers_retired_jobs(self):
        root = Path(__file__).resolve().parents[1]
        paths = sorted((root / ".github" / "workflows").glob("*.yml"))
        self.assertGreater(len(paths), 80)
        references = []
        for path in paths:
            body = path.read_text(encoding="utf-8")
            for basename, workflow_name in self.RETIRED.items():
                if basename in body or workflow_name in body:
                    references.append((path.name, basename))
        self.assertEqual([], references, "active workflows must not depend on retired entries")


if __name__ == "__main__":
    unittest.main()
