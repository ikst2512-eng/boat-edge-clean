"""K92 method denominator and future exhibition-only join fail-closed tests.

A fake in-memory 92-day archive checks the wiring contract, not authenticity.
The existing PR-only CI independently replays the REAL pinned primary ZIP.
"""
from datetime import date,timedelta
from collections import Counter
from hashlib import sha256
from unittest.mock import patch
import json
import sys
import types
import unittest

import scenario_official_K_athlete_attack_rates as study


ROSTER=[
    {"boat":i,"registration":f"{4000+i}","exhibition_course":i}
    for i in range(1,7)
]
RACE="202611140712"


def fake_race(day):
    i=(date.fromisoformat(day[:4]+"-"+day[4:6]+"-"+day[6:8])-
       date(2026,8,1)).days
    winner=3 if i%3==0 else (4 if i%3==1 else 1)
    method=("まくり" if winner==3 else
            "まくり差し" if winner==4 else "逃げ")
    positions={winner:1}
    for rank,c in enumerate((c for c in range(1,7) if c!=winner),2):
        positions[c]=rank
    return {
        "unsettled":False,"method":method,
        "venue":"07","code":day+"0712",
        "entries":[{"course":c,"boat":c,"athlete_registration":f"{4000+c}",
                    "status":f"{positions[c]:02d}"}
                   for c in range(1,7)],
    }


class FakeZip:
    def __init__(self):
        self.days=[(date(2026,8,1)+timedelta(days=i)).strftime("%Y%m%d")
                   for i in range(92)]
        self.manifest={"study_period":"2026-08-01/2026-10-31","results":[{
            "day":d,"official_K_sha256":sha256(d.encode()).hexdigest(),
            "decoded_sha256":sha256(b"x").hexdigest(),
            "official_K_races":1,
        } for d in self.days]}

    def __enter__(self):
        return self

    def __exit__(self,*unused):
        return False

    def testzip(self):
        return None

    def namelist(self):
        return ["official_k_full_92day_reconciliation.json"]+[
            "official_k_full_92_raw/k"+d[2:]+".lzh" for d in self.days]

    def read(self,path):
        if path=="official_k_full_92day_reconciliation.json":
            return json.dumps(self.manifest).encode()
        day="20"+path.rsplit("/",1)[-1][1:-4]
        return day.encode()


class RateTests(unittest.TestCase):
    def test_zero_denominator_stays_null_and_no_ghost_wins(self):
        a=study._safe_summary(Counter(),"method_","eligible")
        self.assertIsNone(a["まくり"]["rate_pct"])
        self.assertEqual(a["まくり"]["wins"],0)
        self.assertEqual(a["まくり差し"]["wins"],0)

    def test_invalid_target_roster_rejected_before_historical_file(self):
        candidates=[
            (RACE,ROSTER[:5]),
            ("202610311912",ROSTER),
            ("bad",ROSTER),
            (RACE,[*ROSTER[:-1],ROSTER[0]]),
            (RACE,[*ROSTER[:-1],dict(ROSTER[-1],exhibition_course=3)]),
            (RACE,[dict(ROSTER[0],registration="not-reg"),*ROSTER[1:]]),
            (RACE,[dict(ROSTER[0],exhibition_course=0),*ROSTER[1:]]),
        ]
        for race,rows in candidates:
            with self.subTest(race=race,rows=rows),self.assertRaises(ValueError):
                study.analyze_k_method_athlete("/not/a/zip",race,rows)

    def test_training_versus_october_verified_denominators_and_racer_identity(self):
        from scenario_official_K_attack_benefit_holdout import _record
        c2=types.ModuleType("research_official_k_c2_escape_conditional_92day")
        c2.verify_original_zip=lambda unused:study.ORIGINAL_K_SHA
        c2.race_outcome=lambda race: {
            "c1_escapement":int(race["method"]=="逃げ"),
        }
        k=types.ModuleType("research_official_k_one_day_compare")
        k.RACE=__import__("re").compile("x")
        k.unpack_lha=lambda unused,day:b"x"
        k.parse_k=lambda text,day,expected_races,allow_unsettled: {
            day+"0712":fake_race(day)
        }
        with (patch.dict(sys.modules,{
                "research_official_k_c2_escape_conditional_92day":c2,
                "research_official_k_one_day_compare":k,
              }),
              patch.object(study,"ZipFile",return_value=FakeZip()),
              patch.object(study,"EXPECTED",(92,92,92,61,31,61,31))):
            s=study.analyze_k_method_athlete("/fake",RACE,ROSTER)
        self.assertEqual(s["verified_92_original_K_days"],92)
        self.assertEqual((s["raw_races"],s["eligible_C1_C2_pair_races"],
                          s["complete_six_numeric_finishers"]),(92,92,92))
        self.assertEqual(s["joined_real_exhibition_course2"][
            "aug_sep_training"]["eligible_C2_pair_starts"],61)
        self.assertEqual(s["joined_real_exhibition_course2"][
            "october_historical_holdout"]["eligible_C2_pair_starts"],31)
        c3=s["joined_real_exhibition_course3_4"]["3"]["aug_sep_training"]
        c4=s["joined_real_exhibition_course3_4"]["4"]["aug_sep_training"]
        self.assertEqual(c3["eligible_starts"],61)
        self.assertEqual(c4["eligible_starts"],61)
        self.assertEqual(c3["まくり"]["wins"],21)
        self.assertEqual(c3["まくり差し"]["wins"],0)
        self.assertEqual(c4["まくり"]["wins"],0)
        self.assertEqual(c4["まくり差し"]["wins"],20)
        self.assertTrue(s["not_all_course_starts_denominator"])
        self.assertFalse(s["use_as_predeadline_model_rate_allowed"])
        self.assertFalse(s["production_changed"])
        self.assertFalse(s["model_predictions_generated"])
        self.assertFalse(s["formal"])

    def test_modified_manifest_digest_rejected(self):
        bad=FakeZip()
        bad.manifest["results"][0]["official_K_sha256"]="f"*64
        c2=types.ModuleType("research_official_k_c2_escape_conditional_92day")
        c2.verify_original_zip=lambda unused:study.ORIGINAL_K_SHA
        c2.race_outcome=lambda race:{"c1_escapement":0}
        k=types.ModuleType("research_official_k_one_day_compare")
        k.RACE=__import__("re").compile("x")
        k.unpack_lha=lambda unused,day:b"x"
        k.parse_k=lambda text,day,expected_races,allow_unsettled:{day:fake_race(day)}
        with (patch.dict(sys.modules,{
                "research_official_k_c2_escape_conditional_92day":c2,
                "research_official_k_one_day_compare":k}),
              patch.object(study,"ZipFile",return_value=bad)):
            with self.assertRaisesRegex(ValueError,"daily_original_sha_drift"):
                study.analyze_k_method_athlete("/fake",RACE,ROSTER)


if __name__=="__main__":
    unittest.main()
