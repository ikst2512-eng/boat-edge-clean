import json
import tempfile
import unittest
from datetime import datetime,timedelta
from pathlib import Path
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
                 "baseline":{str(i):1/120 for i in range(120)},
                 "candidate":{str(i):1/120 for i in range(120)}}
            path.write_text(json.dumps(row),encoding="utf-8")
            self.assertEqual(eligible_paths(root,"20261028",now),[path.as_posix()])
            with self.assertRaisesRegex(ValueError,"cutoff"):
                eligible_paths(root,"20261028",now+timedelta(minutes=2))
            row["prospective_verified"]=True
            path.write_text(json.dumps(row),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"unvalidated"):
                eligible_paths(root,"20261028",now)
    def test_rejects_invalid_probability_total(self):
        now=datetime(2026,10,28,9,0,tzinfo=JST)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"202610281201.json"
            row={"race_code":path.stem,"cutoff_jst":(now+timedelta(minutes=5)).isoformat(),
                 "frozen_at_jst":now.isoformat(),"source_snapshot_generated_at":now.isoformat(),
                 "status":"research_unvalidated","prospective_verified":False,
                 "baseline":{str(i):1/120 for i in range(120)},
                 "candidate":{str(i):0.01 for i in range(120)}}
            path.write_text(json.dumps(row),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"probability"):
                eligible_paths(root,"20261028",now)

if __name__=="__main__":
    unittest.main()
