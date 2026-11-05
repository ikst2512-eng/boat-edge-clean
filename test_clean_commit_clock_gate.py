"""Incident-based tests for CLEAN's real whole-second Git commit gate."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from scripts.clean_commit_clock_gate import (
    JST, after_generation_second, ensure_safe_commit_time, load_records, prepare,
)

BASE = datetime(2026, 11, 5, 11, 4, 24, 496897, tzinfo=JST)
CUTOFF = datetime(2026, 11, 5, 11, 6, 0, tzinfo=JST)
RECORDS = [("202611050803", BASE, CUTOFF)]


class CommitClockTests(unittest.TestCase):
    def test_incident_same_second_commit_does_not_establish_order(self):
        with self.assertRaisesRegex(ValueError, "not strictly after"):
            ensure_safe_commit_time(
                RECORDS, datetime(2026, 11, 5, 11, 4, 24, tzinfo=JST))
        self.assertEqual(after_generation_second(RECORDS),
                         datetime(2026, 11, 5, 11, 4, 25, tzinfo=JST))

    def test_genuinely_later_committer_second_passes_without_remote_promotion(self):
        self.assertTrue(ensure_safe_commit_time(
            RECORDS, datetime(2026, 11, 5, 11, 4, 25, tzinfo=JST)))
        with self.assertRaisesRegex(ValueError, "not strictly after"):
            ensure_safe_commit_time(
                RECORDS, datetime(2026, 11, 5, 11, 4, 23, tzinfo=JST))

    def test_cutoff_and_naive_clocks_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "not before T-12"):
            ensure_safe_commit_time(RECORDS, CUTOFF)
        with self.assertRaisesRegex(ValueError, "untrusted"):
            ensure_safe_commit_time(RECORDS, BASE.replace(tzinfo=None))

    def test_wait_for_actual_next_second_not_backdated_git_metadata(self):
        moments = iter((
            BASE.astimezone(timezone.utc),
            datetime(2026, 11, 5, 11, 4, 25, 60000, tzinfo=JST)
        ))
        slept = []
        checked = prepare(RECORDS, clock=lambda: next(moments), pause=slept.append)
        self.assertEqual(checked.second, 25)
        self.assertEqual(len(slept), 1)
        self.assertGreaterEqual(slept[0], 0.5)
        self.assertLess(slept[0], 0.7)

    def test_clock_not_advanced_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not yet observable"):
            prepare(RECORDS, clock=lambda: BASE, pause=lambda _: None)

    def test_clock_skew_over_two_seconds_is_rejected(self):
        early = BASE - timedelta(seconds=5)
        with self.assertRaisesRegex(ValueError, "clock skew"):
            prepare(RECORDS, clock=lambda: early, pause=lambda _: None)

    def test_receipt_buffer_still_enforced_after_pause(self):
        close = datetime(2026, 11, 5, 11, 4, 31, tzinfo=JST)
        with self.assertRaisesRegex(ValueError, "buffer expired"):
            prepare(RECORDS, clock=lambda: close, pause=lambda _: None)

    def test_post_cutoff_generation_or_wrong_file_identity_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "prospective_predictions/202611050803.json"
            path.parent.mkdir()
            record = {"race_code": "202611050803",
                      "generated_at": BASE.isoformat(),
                      "cutoff_jst": CUTOFF.isoformat()}
            path.write_text(json.dumps(record), encoding="utf-8")
            self.assertEqual(load_records(
                ["prospective_predictions/202611050803.json"], root), RECORDS)
            record["race_code"] = "202611050804"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                load_records(["prospective_predictions/202611050803.json"], root)
            record["race_code"] = "202611050803"
            record["generated_at"] = CUTOFF.isoformat()
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "timestamp invalid"):
                load_records(["prospective_predictions/202611050803.json"], root)

    def test_collector_workflow_keeps_real_time_gate_and_immutable_push(self):
        content = (Path(__file__).resolve().parent /
                   ".github/workflows/clean-prospective.yml").read_text()
        gate_pre = "python scripts/clean_commit_clock_gate.py precommit"
        gate_post = "python scripts/clean_commit_clock_gate.py postcommit"
        git_commit = "git commit -m 'data: freeze prospective pre-cutoff candidates (not yet formal)'"
        self.assertLess(content.index(gate_pre), content.index(git_commit))
        self.assertLess(content.index(git_commit), content.index(gate_post))
        self.assertLess(content.index(gate_post), content.index("git push origin HEAD:main"))
        self.assertIn("git -c rebase.autoStash=true rebase origin/main", content)
        self.assertIn("test_clean_commit_clock_gate", content)


if __name__ == "__main__":
    unittest.main()
