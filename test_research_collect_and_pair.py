import unittest
from unittest.mock import patch
from research_collect_and_pair import run

class CombinedCollectorTests(unittest.TestCase):
    def test_valid_capture(self):
        counts={"saved":1,"already_saved":0,"not_ready":0,"missing":0,"invalid":0}
        with patch("research_collect_and_pair.collect",return_value=counts), patch(
            "research_collect_and_pair.capture",return_value={
                "frozen":1,"already_frozen":0,"ineligible":0}) as paired:
            output=run("20261028")
        paired.assert_called_once()
        self.assertFalse(output["prospective_verified"])
        self.assertTrue(output["requires_git_publication_before_cutoff"])

    def test_invalid_collector_does_not_capture(self):
        counts={"saved":0,"already_saved":0,"not_ready":0,"missing":8,"invalid":0}
        with patch("research_collect_and_pair.collect",return_value=counts), patch(
            "research_collect_and_pair.capture") as paired:
            with self.assertRaises(ValueError):
                run("20261028")
        paired.assert_not_called()

    def test_pair_failure_propagates(self):
        counts={"saved":1,"already_saved":0,"not_ready":0,"missing":0,"invalid":0}
        with patch("research_collect_and_pair.collect",return_value=counts), patch(
            "research_collect_and_pair.capture",side_effect=ValueError("bad model")):
            with self.assertRaisesRegex(ValueError,"bad model"):
                run("20261028")
if __name__=="__main__":
    unittest.main()
