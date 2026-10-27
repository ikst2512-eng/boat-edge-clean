import datetime as dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import v236_freeze

UTC=dt.timezone.utc
JST=dt.timezone(dt.timedelta(hours=9))


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.now=dt.datetime(2026,10,28,12,50,tzinfo=JST)
        self.p=self.root/"data/site_autopilot/v232_cohort/20261028-01-01.json"
        self.p.parent.mkdir(parents=True)
        self.hit=["1-2-3","1-3-2","2-1-3","2-3-1","3-1-2","3-2-1","1-2-4","1-4-2","4-1-2","4-2-1"]
        self.hole=["5-1-2","5-2-1","6-1-2","6-2-1","1-5-2","2-5-1","3-5-1","4-5-1","5-3-2","6-3-2"]
        self.data={"schema":v236_freeze.SCHEMA,"race_key":self.p.stem,
                   "model_id":"SITE_REFERENCE_V122","scope":"SITE_REFERENCE_UNSEEN_PRE_RESULT_ONLY_NOT_FORMAL_FRESH",
                   "formal_results_seen":False,"formal_gate_unlocked":False,
                   "paper_purchases_authorized":False,"real_purchases_authorized":False,
                   "deadline_jst":"2026-10-28T13:00:00+09:00",
                   "snapshot_saved_at":"2026-10-28T12:45:00+09:00",
                   "evidence_committed_at":"2026-10-28T12:46:00+09:00",
                   "frozen_mode_tickets":{"hit":[{"combo":s} for s in self.hit],
                                          "hole":[{"combo":s} for s in self.hole]},
                   "top10":self.hit}
    def save(self):
        self.p.write_text(json.dumps(self.data),encoding="utf-8")
    def prepare(self):
        self.save()
        with patch.object(v236_freeze,"first_commit",return_value=("f"*40,dt.datetime(2026,10,28,12,47,tzinfo=JST),hashlib.sha256(self.p.read_bytes()).digest())):
            return v236_freeze.prepare(self.root,self.p,self.now)
    def test_exact_fifteen_distinct(self):
        result=self.prepare()
        self.assertEqual(result["tickets"],self.hit+self.hole[:5])
        self.assertEqual(result["race_code"],"202610280101")
        self.assertEqual(result["model"],"V236_coverage15")
    def test_cannot_use_after_deadline(self):
        self.now=dt.datetime(2026,10,28,13,0,tzinfo=JST)
        with self.assertRaisesRegex(ValueError,"outside_predeadline_window"):self.prepare()
    def test_requires_frozen_unseen_data(self):
        self.data["formal_results_seen"]=True
        with self.assertRaisesRegex(ValueError,"result_leakage_guard"):self.prepare()
    def test_not_enough_candidates(self):
        self.data["frozen_mode_tickets"]["hole"]=[{"combo":s} for s in self.hit]
        with self.assertRaises(ValueError):self.prepare()


if __name__=="__main__":unittest.main()
