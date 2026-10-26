import unittest
from unittest.mock import patch
from research_pair_pipeline import run
from datetime import datetime
from research_model import JST
DAY=datetime.now(JST).strftime('%Y%m%d')

class PipelineTests(unittest.TestCase):
    def test_rejects_other_day(self):
        with patch("research_pair_pipeline.collect_and_pair") as collector:
            with self.assertRaisesRegex(ValueError,"current JST date"):
                run("20200101")
            collector.assert_not_called()
    def test_skips_when_no_pairs(self):
        with patch("research_pair_pipeline.collect_and_pair",return_value={"paired":{"frozen":0,"already_frozen":0}}),patch("research_pair_pipeline.prepare") as commit,patch("research_pair_pipeline.push") as remote:
            value=run(DAY)
        self.assertEqual(value["publication"],"skipped_no_pairs")
        commit.assert_not_called()
        remote.assert_not_called()
    def test_dry_run_by_default(self):
        with patch("research_pair_pipeline.collect_and_pair",return_value={"paired":{"frozen":1,"already_frozen":0}}),patch("research_pair_pipeline.prepare",return_value={"commit_created":True}),patch("research_pair_pipeline.push",return_value={"dry_run":True}) as remote:
            value=run(DAY,commit=True)
        remote.assert_called_once_with(DAY,dry_run=True)
        self.assertFalse(value["prospective_verified"])
    def test_default_does_not_commit_or_push(self):
        with patch("research_pair_pipeline.collect_and_pair",return_value={
            "paired":{"frozen":1,"already_frozen":0}}),patch(
            "research_pair_pipeline.prepare") as local,patch(
            "research_pair_pipeline.push") as remote:
            result=run(DAY)
        self.assertEqual(result["publication"],"not_requested")
        local.assert_not_called()
        remote.assert_not_called()
    def test_push_requires_explicit_commit(self):
        with patch("research_pair_pipeline.collect_and_pair") as collect:
            with self.assertRaisesRegex(ValueError,"explicit commit"):
                run(DAY,publish=True)
            collect.assert_not_called()
    def test_failure_blocks_publish(self):
        with patch("research_pair_pipeline.collect_and_pair",side_effect=ValueError("bad baseline")),patch("research_pair_pipeline.push") as remote:
            with self.assertRaises(ValueError):
                run(DAY,True)
        remote.assert_not_called()
if __name__=="__main__":
    unittest.main()
