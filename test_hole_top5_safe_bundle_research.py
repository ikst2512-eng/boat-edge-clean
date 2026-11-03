import unittest
from hole_top5_safe_bundle_research import proposals,compare
from unittest.mock import patch

def make_archive():
    base=["1-2-3","1-3-4","1-2-4","1-3-5","1-4-2",
          "1-4-3","1-4-5","1-2-5","1-3-2","1-2-6"]
    donor=["1-5-2","1-5-3"]
    return {"modes":{
        "hole":{"tickets":[{"combo":t} for t in base]},
        "hit":{"tickets":[{"combo":t} for t in donor]},
        "balance":{"tickets":[]}}}

class Top5SafeBundleTests(unittest.TestCase):
    def test_preserves_top5_and_all_existing_pairs(self):
        a=make_archive()
        p=proposals(a)
        self.assertEqual(p["bundle_protect_top5"][:5],p["baseline"][:5])
        self.assertEqual(len(p["bundle_protect_top5"]),len(p["baseline"]))
        self.assertEqual(len(set(p["bundle_protect_top5"])),len(p["baseline"]))
        self.assertTrue({"1-5-2","1-5-3"}.issubset(set(p["bundle_protect_top5"])))
        before={tuple(t.split("-")[:2]) for t in p["baseline"]}
        after={tuple(t.split("-")[:2]) for t in p["bundle_protect_top5"]}
        self.assertTrue(before.issubset(after))

    def test_existing_top5_winner_cannot_be_displaced(self):
        a=make_archive()
        with patch("hole_top5_safe_bundle_research.archived_four_modes",return_value=(200,a)),patch(
            "hole_top5_safe_bundle_research.compare_race",
            return_value={"status":"historical_comparison_only","winning_ticket":"1-4-2"}):
            output=compare(["202611031802"],".")
        safe=output["topn"]["bundle_protect_top5"]["top5"]
        self.assertEqual(safe["hits"],1)
        self.assertEqual(safe["lost"],0)

    def test_new_pair_can_gain_top10_without_top5_loss(self):
        a=make_archive()
        with patch("hole_top5_safe_bundle_research.archived_four_modes",return_value=(200,a)),patch(
            "hole_top5_safe_bundle_research.compare_race",
            return_value={"status":"historical_comparison_only","winning_ticket":"1-5-3"}):
            output=compare(["202611031802"],".")
        self.assertEqual(output["topn"]["bundle_protect_top5"]["top10"]["gained"],1)
        self.assertEqual(output["topn"]["bundle_protect_top5"]["top5"]["gained"],0)

    def test_unconfirmed_result_not_counted(self):
        a=make_archive()
        with patch("hole_top5_safe_bundle_research.archived_four_modes",return_value=(200,a)),patch(
            "hole_top5_safe_bundle_research.compare_race",
            return_value={"status":"result_unavailable"}):
            output=compare(["202611031802"],".")
        self.assertEqual(output["compared"],0)
        self.assertEqual(len(output["missing"]),1)

if __name__=="__main__":
    unittest.main()
