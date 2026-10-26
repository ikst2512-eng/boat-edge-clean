import json
import tempfile
import unittest
from datetime import datetime,timedelta
from pathlib import Path
from itertools import permutations

TICKETS=['-'.join(map(str,p)) for p in permutations(range(1,7),3)]
from research_model import JST
from research_pair_publish_guard import eligible_paths

class PublishGuardTests(unittest.TestCase):
    def test_accepts_only_before_cutoff(self):
        now=datetime(2026,10,28,9,0,tzinfo=JST)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"202610281201.json"
            row={"race_code":"202610281201",
                 "cutoff_jst":(now+timedelta(minutes=2)).isoformat(),
                 "frozen_at_jst":now.isoformat(),
                 "source_snapshot_generated_at":now.isoformat(),
                 "status":"research_unvalidated","prospective_verified":False,
                 "baseline":{k:1/120 for k in TICKETS},
                 "candidate":{k:1/120 for k in TICKETS}}
            path.write_text(json.dumps(row),encoding="utf-8")
            self.assertEqual(eligible_paths(root,"20261028",now),[path.as_posix()])
            with self.assertRaisesRegex(ValueError,"cutoff"):
                eligible_paths(root,"20261028",now+timedelta(minutes=2))
            row["prospective_verified"]=True
            path.write_text(json.dumps(row),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"unvalidated"):
                eligible_paths(root,"20261028",now)
    def test_rejects_source_after_freeze(self):
        now=datetime(2026,10,28,9,0,tzinfo=JST)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"202610281201.json"
            row={"race_code":path.stem,
                 "cutoff_jst":(now+timedelta(minutes=10)).isoformat(),
                 "frozen_at_jst":now.isoformat(),
                 "source_snapshot_generated_at":(now+timedelta(seconds=1)).isoformat(),
                 "status":"research_unvalidated","prospective_verified":False,
                 "baseline":{k:1/120 for k in TICKETS},
                 "candidate":{k:1/120 for k in TICKETS}}
            path.write_text(json.dumps(row),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"source generated after"):
                eligible_paths(root,"20261028",now)
    def test_rejects_future_freeze(self):
        now=datetime(2026,10,28,9,0,tzinfo=JST)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"202610281201.json"
            row={"race_code":path.stem,
                 "cutoff_jst":(now+timedelta(minutes=10)).isoformat(),
                 "frozen_at_jst":(now+timedelta(minutes=1)).isoformat(),
                 "source_snapshot_generated_at":now.isoformat(),
                 "status":"research_unvalidated","prospective_verified":False,
                 "baseline":{k:1/120 for k in TICKETS},
                 "candidate":{k:1/120 for k in TICKETS}}
            path.write_text(json.dumps(row),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"future"):
                eligible_paths(root,"20261028",now)
    def test_rejects_wrong_120_keys(self):
        now=datetime(2026,10,28,9,0,tzinfo=JST)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"202610281201.json"
            row={"race_code":path.stem,
                 "cutoff_jst":(now+timedelta(minutes=5)).isoformat(),
                 "frozen_at_jst":now.isoformat(),
                 "source_snapshot_generated_at":now.isoformat(),
                 "status":"research_unvalidated","prospective_verified":False,
                 "baseline":{str(i):1/120 for i in range(120)},
                 "candidate":{k:1/120 for k in TICKETS}}
            path.write_text(json.dumps(row),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"trifecta combination keys"):
                eligible_paths(root,"20261028",now)
    def test_rejects_invalid_probability_total(self):
        now=datetime(2026,10,28,9,0,tzinfo=JST)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"202610281201.json"
            row={"race_code":path.stem,"cutoff_jst":(now+timedelta(minutes=5)).isoformat(),
                 "frozen_at_jst":now.isoformat(),"source_snapshot_generated_at":now.isoformat(),
                 "status":"research_unvalidated","prospective_verified":False,
                 "baseline":{k:1/120 for k in TICKETS},
                 "candidate":{k:0.01 for k in TICKETS}}
            path.write_text(json.dumps(row),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"probability"):
                eligible_paths(root,"20261028",now)

if __name__=="__main__":
    unittest.main()
