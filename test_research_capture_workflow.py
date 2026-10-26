"""Offline integration tests for the daily persistence shell block."""
import pathlib
import json
import hashlib
import subprocess
import tempfile
import unittest

def valid_record(code):
    title="a"*64
    cards="b"*64
    return json.dumps({"race_code":code,"status":"research","validated":False,
      "source_title_sha256":title,"source_cards_sha256":cards,
      "input_sha256":hashlib.sha256((title+":"+cards).encode("ascii")).hexdigest(),
      "input_hash_scope":"source_csv_byte_hashes_ordered_title_cards",
      "model_source_sha256":"c"*64,"model_git_sha":"d"*40,
      "source_title_received_jst":"2026-10-27T10:00:00+09:00",
      "source_cards_received_jst":"2026-10-27T10:01:00+09:00",
      "generated_at":"2026-10-27T10:02:00+09:00",
      "cutoff_jst":"2026-10-27T12:00:00+09:00",
      "source_deadline_jst":"2026-10-27T12:12:00+09:00"})

WORKFLOW = pathlib.Path(__file__).parent / ".github/workflows/daily-research-forecast.yml"

def run(*args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)

def persistence_script():
    data = WORKFLOW.read_text()
    section = data.split("      - name: Persist research-only snapshots to Git\n", 1)[1].split("      - name: Preserve collection evidence\n", 1)[0]
    body = section.split("        run: |\n", 1)[1]
    return "\n".join(line[10:] if line.startswith("          ") else line for line in body.splitlines()) + "\n"

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        for cmd in (["git", "init", "-q"], ["git", "config", "user.email", "test@example.invalid"],
                    ["git", "config", "user.name", "CI Test"]):
            r = run(*cmd, cwd=self.root)
            self.assertEqual(r.returncode, 0, r.stderr)
        (self.root / "research_snapshots").mkdir()
        (self.root / "capture-evidence").mkdir()
        (self.root / "README").write_text("initial")
        run("git", "add", ".", cwd=self.root)
        self.assertEqual(run("git", "commit", "-qm", "initial", cwd=self.root).returncode, 0)
        self.script = persistence_script()
        self.assertEqual(run("bash", "-n", "-c", self.script).returncode, 0)

    def execute(self):
        # Prevent remote operations: simulated git push is not required to test guards.
        return run("bash", "-c", self.script, cwd=self.root,
                   env={"PATH": "/usr/bin:/bin", "GITHUB_RUN_ID": "1", "GITHUB_SHA": "testsha"})

    def test_no_new_snapshot(self):
        r = self.execute()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("No new cutoff-eligible", r.stdout)

    def test_reject_modified_snapshot(self):
        p = self.root / "research_snapshots/202610270101.json"
        p.write_text("{}")
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "baseline snapshot", cwd=self.root)
        p.write_text('{"changed":true}')
        r = self.execute()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("existing research snapshot changed", r.stdout)

    def test_reject_deleted_snapshot(self):
        p = self.root / "research_snapshots/202610270101.json"
        p.write_text("{}")
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "baseline snapshot", cwd=self.root)
        p.unlink()
        r = self.execute()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("existing research snapshot changed", r.stdout)

    def test_reject_missing_tracked_directory(self):
        p = self.root / "research_snapshots/202610270101.json"
        p.write_text("{}")
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "baseline snapshot", cwd=self.root)
        p.unlink()
        (self.root / "research_snapshots").rmdir()
        r = self.execute()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("tracked research snapshots directory missing", r.stdout)

    def test_reject_invalid_added_filename(self):
        (self.root / "research_snapshots/invalid.json").write_text("{}")
        r = self.execute()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invalid research snapshot path", r.stdout)

    def test_successful_push_to_local_bare_remote(self):
        remote = self.root / "remote.git"
        self.assertEqual(run("git", "init", "-q", "--bare", str(remote)).returncode, 0)
        self.assertEqual(run("git", "remote", "add", "origin", str(remote), cwd=self.root).returncode, 0)
        self.assertEqual(run("git", "push", "-u", "origin", "HEAD", cwd=self.root).returncode, 0)
        p = self.root / "research_snapshots/202610270102.json"
        p.write_text(valid_record("202610270102"))
        r = self.execute()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.root / "capture-evidence/new-snapshots/202610270102.json").exists())
        self.assertIn("202610270102.json", (self.root / "capture-evidence/snapshot-sha256.txt").read_text())
        self.assertIn("202610270102.json", run("git", "ls-tree", "-r", "--name-only", "HEAD", cwd=self.root).stdout)

    def test_new_snapshot_generates_evidence_before_push(self):
        p = self.root / "research_snapshots/202610270101.json"
        p.write_text(valid_record("202610270101"))
        r = self.execute()
        # Push has no remote in this temporary repository and must fail.
        self.assertNotEqual(r.returncode, 0)
        evidence = self.root / "capture-evidence/new-snapshots/202610270101.json"
        self.assertEqual(evidence.read_bytes(), p.read_bytes())
        hashes = (self.root / "capture-evidence/snapshot-sha256.txt").read_text()
        import hashlib
        self.assertIn(hashlib.sha256(p.read_bytes()).hexdigest(), hashes)
        self.assertIn("202610270101.json", hashes)
        self.assertIn("No configured push destination", r.stdout)
        self.assertIn("fatal:", (self.root / "capture-evidence/persistence.log").read_text())

if __name__ == "__main__":
    unittest.main()
