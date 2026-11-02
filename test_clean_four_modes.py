import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import clean_four_modes as model
from research_model import probabilities


class CleanFourModeTests(unittest.TestCase):
    def test_independent_modes_and_targets(self):
        p=probabilities([6.2,5.1,4.2,4.5,3.1,2.9])
        result=model.rank_modes(p)
        self.assertEqual(set(result),{"hit","balance","hole","narrow"})
        self.assertEqual([result[n]["target_hit_rate_pct"] for n in ("hit","balance","hole","narrow")],[60,50,12.5,40])
        for mode in result.values():
            combos=[x["combo"] for x in mode["tickets"]]
            self.assertEqual(len(combos),len(set(combos)))
            self.assertTrue(all(len(x.split("-"))==3 for x in combos))
            self.assertIsNone(mode["actual_hit_rate_pct"])
        self.assertNotEqual(result["hit"]["tickets"],result["hole"]["tickets"])
        self.assertLessEqual(len(result["narrow"]["tickets"]),5)

    def test_agreed_ticket_count_order_is_reported_not_fabricated(self):
        modes={"narrow":{"tickets":[1,2,3]},
               "hit":{"tickets":[1,2,3,4]},
               "balance":{"tickets":[1,2,3,4,5]},
               "hole":{"tickets":[1,2,3,4,5,6]}}
        self.assertEqual(model.ticket_order_audit(modes)["status"],"pass")
        modes["hit"]["tickets"] = list(range(30))
        self.assertEqual(model.ticket_order_audit(modes)["status"],"mismatch")
        self.assertEqual(model.ticket_order_audit({"narrow":{}})["status"],"unknown")

    def test_current_generated_mode_must_not_be_claimed_compliant(self):
        p=probabilities([6.2,5.1,4.2,4.5,3.1,2.9])
        result=model.rank_modes(p)
        audit=model.ticket_order_audit(result)
        self.assertEqual(audit["status"],"mismatch")

    def test_frontend_four_mode_display_contract(self):
        from pathlib import Path
        html=(Path(__file__).resolve().parent/"index.html").read_text(encoding="utf-8")
        self.assertIn("const modes=[['narrow','絞り'],['hit','本命'],['balance','バランス'],['hole','穴']]",html)
        self.assertIn("status.dataset.orderWarning=orderValid?'false':'true'",html)
        self.assertIn('#fourModeForecastStatus[data-order-warning="true"]{display:block',html)
        self.assertIn("overflow-wrap:anywhere",html)
        self.assertIn("オッズ未取得（検証可能なデータなし）",html)
        self.assertIn("結果未取得（的中・不的中は未判定）",html)
        self.assertIn("result.source_url!==source",html)
        self.assertIn("stamp<confirmed",html)

    def test_retired_live_api_generator_not_available(self):
        self.assertFalse(hasattr(model,"forecast"))

    def test_archived_reader_preserved_and_missing_archive_not_regenerated(self):
        self.assertTrue(callable(model.load_archived))
        with patch.object(model.Path,"is_file",return_value=False), patch.object(
            model,"urlopen",side_effect=HTTPError("archive",404,"Not Found",None,None)
        ):
            self.assertIsNone(model.load_archived("202610300101"))


if __name__=="__main__":
    unittest.main()
