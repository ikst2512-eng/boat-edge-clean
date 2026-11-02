import json
import tempfile
import unittest
from pathlib import Path
from scripts.audit_new_v2_staged import audit, VERSION, MODES, COUNTS

class NewV2GateTests(unittest.TestCase):
    def test_good_and_bad_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"202611030101.json"
            good={"race_code":p.stem,"model_version":VERSION,"modes":{
                name:{"count_policy":"provisional_new_generation_v2",
                      "tickets":[{"combo":str(i)} for i in range(count)]}
                for name,count in zip(MODES,COUNTS)}}
            p.write_text(json.dumps(good))
            self.assertEqual(audit([p]),1)
            for bad in [dict(good,model_version="CLEAN_FOUR_MODES_V1_UNCALIBRATED"),
                        dict(good,race_code="202611030102")]:
                p.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):audit([p])
            good["modes"]["hole"]["tickets"].pop()
            p.write_text(json.dumps(good))
            with self.assertRaises(ValueError):audit([p])
