"""Synthetic-only regressions: a local bulk freeze never publishes or scores."""
from datetime import datetime, timedelta
import hashlib
import json
import unittest

from position_sensitive_candidate_batch_export import (
    MIN_PRET12_UPLOAD_MARGIN_SECONDS, plan_batch,
)
from test_position_sensitive_candidate_delivery_gap import FakeGit, ASOF

JST = "2026-11-09T13:00:00+09:00"


class BatchExporterTests(unittest.TestCase):
    def test_only_future_missing_eligible_originals_are_frozen(self):
        git=FakeGit()
        out=plan_batch(git,"20261109",datetime.fromisoformat(JST))
        self.assertEqual(out["original_exact_replays"],3)
        self.assertEqual(out["previously_saved_candidates"],1)
        self.assertEqual(out["planned_local_only"],1)
        self.assertEqual(len(out["skipped"]),2)
        x=out["candidates"][0]
        self.assertEqual(x["race_code"],"202611090103")
        self.assertEqual(x["path"],"position_sensitive_research/202611090103.json")
        self.assertEqual(x["candidate_sha256"],
                         hashlib.sha256(x["candidate_text"].encode()).hexdigest())
        self.assertEqual(json.loads(x["candidate_text"])["formal"],False)
        self.assertEqual(x["frozen_at_jst"],JST)
        self.assertFalse(out["formal"])
        self.assertEqual(out["candidate_first_remote_receipts_independently_verified"],0)
        self.assertEqual(out["formal_forward_eligible_races"],0)
        self.assertFalse(out["production_changed"])
        self.assertFalse(any("confirmed_results" in str(args) for args in git.calls))

    def test_replay_again_does_not_make_candidate_saved(self):
        git=FakeGit()
        before=dict(git.candidates)
        first=plan_batch(git,"20261109",datetime.fromisoformat(JST))
        second=plan_batch(git,"20261109",datetime.fromisoformat(JST))
        self.assertEqual(first["candidates"],second["candidates"])
        self.assertEqual(git.candidates,before)
        self.assertEqual(first["previously_saved_candidates"],1)

    def test_margin_near_T12_never_exports(self):
        git=FakeGit()
        t=datetime.fromisoformat("2026-11-09T15:19:00+09:00")
        out=plan_batch(git,"20261109",t)
        self.assertEqual(out["planned_local_only"],0)
        self.assertTrue(any(s["reason"]=="insufficient_upload_margin"
                            for s in out["skipped"]))
        self.assertFalse(out["formal"])

    def test_candidate_integrity_change_prevents_entire_batch(self):
        git=FakeGit()
        value=json.loads(git.candidates["202611090101"])
        value["baseline"]["hit"][0]="6-5-4"
        git.candidates["202611090101"]=json.dumps(value).encode()
        with self.assertRaises(ValueError):
            plan_batch(git,"20261109",datetime.fromisoformat(JST))

    def test_unauthorized_day_or_margin_does_not_touch_git(self):
        for date in ("20261108","20270101","../a","2026-11-09"):
            git=FakeGit()
            with self.assertRaises(ValueError):
                plan_batch(git,date,datetime.fromisoformat(JST))
            self.assertEqual(git.calls,[])
        for margin in (0,599,-1,3.2):
            git=FakeGit()
            with self.assertRaises(ValueError):
                plan_batch(git,"20261109",datetime.fromisoformat(JST),
                           min_margin_seconds=margin)
            self.assertEqual(git.calls,[])

    def test_no_saved_originals_produces_no_false_positive(self):
        git=FakeGit()
        git.sources.clear()
        git.candidates.clear()
        out=plan_batch(git,"20261109",datetime.fromisoformat(JST))
        self.assertEqual(out["original_exact_replays"],0)
        self.assertEqual(out["planned_local_only"],0)
        self.assertEqual(out["previously_saved_candidates"],0)
        self.assertFalse(out["model_improvement_proven"])

    def test_even_large_margin_is_fail_closed(self):
        git=FakeGit()
        out=plan_batch(git,"20261109",datetime.fromisoformat(JST),
                       min_margin_seconds=14400)
        self.assertEqual(out["planned_local_only"],0)
        self.assertFalse(out["promotion_allowed"])

    def test_candidate_with_modified_original_source_is_rejected(self):
        git=FakeGit()
        git.sources["202611090103"]=b"{}"
        out=plan_batch(git,"20261109",datetime.fromisoformat(JST))
        self.assertEqual(out["planned_local_only"],0)
        self.assertEqual(len(out["skipped"]),2)
        self.assertEqual(out["candidate_first_remote_receipts_independently_verified"],0)
        self.assertFalse(out["promotion_allowed"])


if __name__=="__main__":
    unittest.main()
