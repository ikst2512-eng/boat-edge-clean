"""Dry-run CLI never stores candidate bytes or reaches any remote writer."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import scenario_signed_st_future_pre_t12_cli as cli


class SignedFOperatorCLIContractTests(unittest.TestCase):
    def test_nonexistent_or_synthetic_1698_file_rejected(self):
        with self.assertRaisesRegex(ValueError,"exact_unloaded_1698_file"):
            cli.load_reviewed_1698("/does-not-exist/research.py")
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"position_sensitive_conditioned_lab.py"
            f.write_text("def experimental_conditional_board(): return None\n")
            with self.assertRaisesRegex(ValueError,"exact_unloaded_1698_file"):
                cli.load_reviewed_1698(f)

    def test_dryrun_never_emits_candidate_bytes_or_git_writes(self):
        prep={
            "race_code":"202611120711",
            "path":"signed_f_four_mode_research/202611120711.json",
            "bytes":b'{"example":"unpublished"}\n',
            "sha256":hashlib.sha256(b'{"example":"unpublished"}\n').hexdigest(),
            "git_blob_sha1":"1"*40,
            "status":"locally_prepared_unpublished_UNVERIFIED",
        }
        with patch.object(cli,"load_reviewed_1698",return_value=lambda *a:None) as parser:
            with patch.object(cli,"run_one_shot_unpublished",return_value=prep) as runner:
                result=cli.operator_dry_run("card","before","odds","external")
                parser.assert_called_once_with("external")
                self.assertEqual(runner.call_count,1)
                self.assertEqual(runner.call_args.args[:3],("card","before","odds"))
                self.assertEqual(result["status"],"locally_prepared_unpublished_UNVERIFIED")
                self.assertEqual(result["candidate_content_sha256"],prep["sha256"])
                self.assertEqual(result["candidate_length_bytes"],len(prep["bytes"]))
                for key in ("github_put_attempted","candidate_file_written",
                            "candidate_bytes_emitted",
                            "candidate_first_remote_receipt_verified",
                            "eligible_for_future_300_plus_300","formal",
                            "production_changed"):
                    self.assertIs(result[key],False,key)
                self.assertNotIn(prep["bytes"].decode(),json.dumps(result))

    def test_no_user_clock_override_or_publish_switch_in_cli_definition(self):
        source=Path(cli.__file__).read_text(encoding="utf-8")
        self.assertNotIn('add_argument("--publish"',source)
        self.assertNotIn('add_argument("--generated-at"',source)
        self.assertNotIn('add_argument("--frozen-at"',source)
        self.assertIn("datetime.now(JST)",source)
        self.assertNotIn("urllib.request",source)
        self.assertNotIn("github PUT",source)

    def test_real_reviewed_callback_hash_not_a_synthetic_mock(self):
        self.assertEqual(cli.PINNED_1698_SHA1,
                         "0019978a4e27a1235d0b466c11f514bd7105f261")


if __name__=="__main__":
    unittest.main()
