import json
import tempfile
import unittest
from pathlib import Path
from research_hit_ticket_position_diagnostics import analyze

class LostCoverageTests(unittest.TestCase):
    def test_10_ticket_loss_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"four_mode_forecasts").mkdir()
            code="202610280101"
            picks=[{"combo":f"1-2-{x}"} for x in (3,4,5,6)]
            picks += [{"combo":f"2-1-{x}"} for x in (3,4,5,6)]
            picks += [{"combo":"3-1-2"},{"combo":"3-2-1"},{"combo":"4-1-2"}]
            (root/"four_mode_forecasts"/(code+".json")).write_text(json.dumps({
                "race_code":code,"schema":"CLEAN_FOUR_MODES_PREDEADLINE_V1",
                "modes":{"hit":{"tickets":picks}}}))
            history={"schema":"CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1","races":[{
                "race_code":code,"finish":"4-1-2","modes":{"hit":{"hit":True}}}]}
            result=analyze(history,root)
            self.assertEqual(result["wins_in_saved_positions_11_plus"],1)
            self.assertEqual(result["hits_in_first_10_saved_tickets"],0)
            self.assertEqual(result["excluded_winner_first_boats"],{"4":1})
            history["races"][0]["modes"]["hit"]["hit"]=False
            with self.assertRaisesRegex(ValueError,"verified_history_disagrees"):
                analyze(history,root)

if __name__=="__main__": unittest.main()
