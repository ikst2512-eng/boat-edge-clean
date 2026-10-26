import unittest
from clean_source_comparison import compare_race_sources

def records():
    racers = [{"lane": i, "name": f"選手{i}", "registration": str(4000+i)} for i in range(1,7)]
    csv = {"status":"staged_unpublished","race_code":"202610271201","source_url":"https://boatracecsv.github.io/example.csv","racers":[dict(r) for r in racers]}
    official = {"status":"staged_unpublished","race_key":"20261027-12-01","source_url":"https://www.boatrace.jp/owpc/pc/race/racelist?hd=20261027&jcd=12&rno=1","racers":[dict(r) for r in racers]}
    return csv,official

class SourceComparisonTests(unittest.TestCase):
    def test_match_is_not_publication(self):
        c,o=records()
        x=compare_race_sources(c,o)
        self.assertEqual(x["status"],"matched_unpublished")
    def test_identity_mismatch_fails(self):
        c,o=records()
        o["race_key"]="20261027-12-02"
        with self.assertRaises(ValueError):
            compare_race_sources(c,o)
    def test_missing_registration_is_unknown_not_match(self):
        c,o=records()
        o["racers"][0].pop("registration")
        x=compare_race_sources(c,o)
        self.assertEqual(x["status"],"blocked_unpublished")
        self.assertIn("lane1.registration",x["unknown"])
    def test_disagreement_is_blocked(self):
        c,o=records()
        o["racers"][3]["name"]="別選手"
        x=compare_race_sources(c,o)
        self.assertEqual(x["status"],"blocked_unpublished")
        self.assertIn("lane4.name",x["mismatches"])
    def test_duplicate_lane_rejected(self):
        c,o=records()
        o["racers"][5]["lane"]=1
        with self.assertRaises(ValueError):
            compare_race_sources(c,o)
    def test_unstaged_input_rejected(self):
        c,o=records()
        c["status"]="published"
        with self.assertRaises(ValueError):
            compare_race_sources(c,o)

if __name__ == "__main__":
    unittest.main()
