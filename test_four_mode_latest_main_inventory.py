"""No synthetic main-tree filename can become a formal scoring denominator."""
import unittest
from four_mode_latest_main_inventory import inspect_main_tree

SHA = "a" * 40
BLOB = "b" * 40


def row(path, mode="100644"):
    return (mode + " blob " + BLOB + "\t" + path + "\0").encode("ascii")


def git_reader(rows, sha=SHA):
    calls = []
    def git(args):
        calls.append(list(args))
        if args[:2] == ["rev-parse", "--verify"]:
            return (sha + "\n").encode()
        if args[:3] == ["ls-tree", "-r", "-z"]:
            return rows
        raise AssertionError("unexpected_git_command")
    return git, calls


class MainTreeInventoryTests(unittest.TestCase):
    def test_separates_main_four_mode_clean_and_confirmed_files(self):
        paths = b"".join([
            row("four_mode_forecasts/202611050101.json"),
            row("four_mode_forecasts/capture_status.json"),
            row("prospective_predictions/202611050102.json"),
            row("confirmed_results/202611050101.json"),
            row("confirmed_results/202611050103.json"),
            row("four_mode_forecasts/202611040101.json"),
            row("confirmed_results/202611030101.json"),
        ])
        git, calls = git_reader(paths)
        out = inspect_main_tree(git=git)
        self.assertEqual(out["main_tree_sha"], SHA)
        self.assertEqual(out["four_mode_file_count"], 1)
        self.assertEqual(out["four_mode_with_result_filename"], 1)
        self.assertEqual(out["confirmed_result_file_count"], 2)
        self.assertEqual(out["clean_separate_file_count"], 1)
        self.assertEqual(out["four_mode_codes"], ["202611050101"])
        self.assertEqual(out["clean_separate_codes"], ["202611050102"])
        self.assertIsNone(out["research_eligible_race_count"])
        self.assertIsNone(out["formal_eligible_race_count"])
        self.assertFalse(out["first_git_add_checked"])
        self.assertFalse(out["result_content_independently_verified"])
        self.assertFalse(out["capture_run_inventory_exhaustive"])
        self.assertFalse(out["formal"])
        self.assertEqual(calls[0][0], "rev-parse")
        self.assertEqual(calls[1][0], "ls-tree")

    def test_empty_main_tree_is_not_a_zero_hit_sample(self):
        git, _calls = git_reader(b"")
        out = inspect_main_tree(git=git)
        self.assertEqual(out["status"], "no_four_mode_files_in_examined_main_tree")
        self.assertEqual(out["four_mode_file_count"], 0)
        self.assertIsNone(out["research_eligible_race_count"])
        self.assertIsNone(out["formal_eligible_race_count"])

    def test_missing_main_ref_fails_closed(self):
        git, _calls = git_reader(b"", sha="bad")
        with self.assertRaisesRegex(ValueError, "untrusted_main_ref"):
            inspect_main_tree(git=git)

    def test_repeated_filename_fails_closed(self):
        git, _calls = git_reader(row("four_mode_forecasts/202611050101.json") * 2)
        with self.assertRaisesRegex(ValueError, "invalid_or_duplicate"):
            inspect_main_tree(git=git)

    def test_symlink_evidence_not_included(self):
        git, _calls = git_reader(row("four_mode_forecasts/202611050101.json", mode="120000"))
        with self.assertRaisesRegex(ValueError, "invalid_or_duplicate"):
            inspect_main_tree(git=git)

    def test_not_in_study_window_excluded(self):
        git, _calls = git_reader(row("four_mode_forecasts/202701010101.json")
                                 + row("four_mode_forecasts/202611040101.json"))
        out = inspect_main_tree(git=git)
        self.assertEqual(out["four_mode_file_count"], 0)

    def test_invalid_race_number_not_counted(self):
        git, _calls = git_reader(row("four_mode_forecasts/202611052501.json")
                                 + row("four_mode_forecasts/202611050113.json"))
        self.assertEqual(inspect_main_tree(git=git)["four_mode_file_count"], 0)


if __name__ == "__main__":
    unittest.main()
