"""Synthetic, result-blind tests of future per-race TopK ticket exposures."""
from copy import deepcopy
import json
import unittest

from test_four_mode_position_sensitive_forward import archive, frozen
from position_sensitive_future_topk_exposure import (
    LEDGER, ORIGINAL, PREFIX, README,
    audit_future_ledger, compare_ticket_sets,
)

CODE = "202611091912"
TIP = "b"*40


def sample():
    s, original = frozen(
        archive(CODE, deadline="2026-11-09T20:38:00+09:00"),
        "2026-11-09T14:25:53+09:00")
    exact = (json.dumps(s, ensure_ascii=False, sort_keys=True)+"\n").encode()
    return s, original, exact


def make_git(exact, original, names=None):
    roster = [README, PREFIX + CODE + ".json"] if names is None else names
    def git(*args):
        if args == ("rev-parse", "--verify", LEDGER+"^{commit}"):
            return TIP.encode()+b"\n"
        if args == ("ls-tree", "-r", "--name-only", TIP, "--", PREFIX):
            return ("\n".join(roster)+"\n").encode()
        if args == ("show", TIP+":"+PREFIX+CODE+".json"):
            return exact
        if args == ("show", ORIGINAL+":four_mode_forecasts/"+CODE+".json"):
            return original
        raise AssertionError("unexpected git operation: "+str(args))
    return git


class ForwardTopKExposureTests(unittest.TestCase):
    def test_replayed_race_topk_counts_and_no_accuracy_claim(self):
        snap, original, exact = sample()
        result = audit_future_ledger(make_git(exact, original))
        self.assertEqual(result["candidate_files"], 1)
        self.assertEqual(result["same_race_pairs_validated"], 1)
        self.assertEqual(result["outcome_files_read"], 0)
        self.assertFalse(result["actual_hit_rates_calculated"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["promotion_allowed"])
        self.assertEqual(result["candidate_first_remote_receipts_independently_verified"], 0)
        for mode, row in result["rows"][0]["by_mode"].items():
            self.assertEqual(row["top1_changed"], row["baseline_top1"] != row["candidate_top1"])
            self.assertEqual(row["top1_changed"],
                             row["topn"]["1"]["ticket_membership_changed"])
            for k in (1, 3, 5, 10):
                metric = row["topn"][str(k)]
                if not metric["applicable"]:
                    self.assertEqual(mode, "narrow")
                    self.assertEqual(k, 10)
                    continue
                self.assertEqual(metric["retained_old_tickets"] +
                                 metric["replaced_ticket_slots"], k)
                self.assertEqual(metric["ticket_membership_changed"],
                                 metric["replaced_ticket_slots"] > 0)
        self.assertIsNone(result["by_mode"]["narrow"]
                          ["topk_membership_changed_races"]["10"])

    def test_top1_identical_is_not_forced_to_change(self):
        snap, original, _ = sample()
        p = compare_ticket_sets(snap, original)
        for mode in ("narrow", "hit", "balance"):
            # This fixture has no forced divergence; same Top1 is allowed.
            self.assertEqual(p["by_mode"][mode]["top1_changed"],
                             p["by_mode"][mode]["baseline_top1"] !=
                             p["by_mode"][mode]["candidate_top1"])
        self.assertEqual(p["race_code"], CODE)

    def test_modified_candidate_ticket_fails_before_metrics(self):
        snap, original, exact = sample()
        forged = deepcopy(snap)
        forged["candidate"]["hit"][0] = "6-5-4"
        with self.assertRaises(ValueError):
            compare_ticket_sets(forged, original)
        with self.assertRaises(ValueError):
            audit_future_ledger(make_git(json.dumps(forged).encode(), original))

    def test_changed_original_source_bytes_rejected(self):
        _, original, exact = sample()
        with self.assertRaises(ValueError):
            audit_future_ledger(make_git(exact, original+b" "))

    def test_empty_branch_and_bad_unapproved_paths_fail_closed(self):
        _, original, exact = sample()
        for names in ([README, README], [README, PREFIX+"202611080101.json"],
                      [README, "confirmed_results/202611091912.json"],
                      [README, PREFIX+"../../main.json"]):
            with self.subTest(names=names), self.assertRaises(ValueError):
                audit_future_ledger(make_git(exact, original, names))

    def test_empty_valid_bootstrap_is_nonformal(self):
        _, original, exact = sample()
        report = audit_future_ledger(make_git(exact, original, [README]))
        self.assertEqual(report["candidate_files"], 0)
        self.assertEqual(report["same_race_pairs_validated"], 0)
        self.assertEqual(report["by_mode"]["hit"]["top1_changed_races"], 0)
        self.assertFalse(report["formal"])

    def test_unknown_refs_are_not_a_backdoor_to_results(self):
        _, original, exact = sample()
        for ref in ("main", "refs/remotes/origin/main", "../result"):
            with self.assertRaisesRegex(ValueError, "unapproved_git_refs"):
                audit_future_ledger(make_git(exact, original), ledger_ref=ref)


if __name__ == "__main__":
    unittest.main()
