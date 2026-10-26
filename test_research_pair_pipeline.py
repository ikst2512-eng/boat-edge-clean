import unittest
from unittest.mock import patch
from research_pair_pipeline import run

class PipelineTests(unittest.TestCase):
    def test_skips_when_no_pairs(self):
        with patch("research_pair_pipeline.collect_and_pair",return_value={"paired":{"frozen":0,"already_frozen":0}}),patch("research_pair_pipeline.prepare") as commit,patch("research_pair_pipeline.push") as remote:
            value=run("20261028")
        self.assertEqual(value["publication"],"skipped_no_pairs")
        commit.assert_not_called()
        remote.assert_not_called()
    def test_dry_run_by_default(self):
        with patch("research_pair_pipeline.collect_and_pair",return_value={"paired":{"frozen":1,"already_frozen":0}}),patch("research_pair_pipeline.prepare",return_value={"commit_created":True}),patch("research_pair_pipeline.push",return_value={"dry_run":True}) as remote:
            value=run("20261028")
        remote.assert_called_once_with("20261028",dry_run=True)
        self.assertFalse(value["prospective_verified"])
    def test_failure_blocks_publish(self):
        with patch("research_pair_pipeline.collect_and_pair",side_effect=ValueError("bad baseline")),patch("research_pair_pipeline.push") as remote:
            with self.assertRaises(ValueError):
                run("20261028",True)
        remote.assert_not_called()
if __name__=="__main__":
    unittest.main()
