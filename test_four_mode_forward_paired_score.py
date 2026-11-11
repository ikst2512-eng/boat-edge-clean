"""Fail-closed tests for four-mode forward research gating; no live data changes."""
import copy
import json
import unittest
from itertools import permutations
from four_mode_forward_paired_score import (COUNTS, PROTOCOL, protocol_check, score,
                                       exact_mcnemar_two_sided_reference,
                                       confirmation_holm_reference,
                                       preflight_unregistered_scenario_bridge,
                                       review_upstream_t12_source_pair_handoff,
                                       review_upstream_pre_source_remote_existence)


class FourModeForwardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    def row(self):
        tickets = ["-".join(map(str, p)) for p in permutations(range(1, 7), 3)]
        return {
            "race_code": "202611070101",
            "deadline_jst": "2026-11-07T08:35:00+09:00",
            "model_version": self.policy["model_version"],
            "official_source_received_jst": "2026-11-07T08:09:00+09:00",
            "baseline_generated_jst": "2026-11-07T08:10:00+09:00",
            "baseline_github_observed_jst": "2026-11-07T08:10:02+09:00",
            "candidate_generated_jst": "2026-11-07T08:10:05+09:00",
            "candidate_github_observed_jst": "2026-11-07T08:10:07+09:00",
            "official_beforeinfo_complete_6": True,
            "official_exhibition_complete_6": True,
            "official_odds_complete_120": True,
            "result_based_features_used": False,
            "source_sha256": "a"*64,
            "original_forecast_sha256": "b"*64,
            "candidate_method_sha256": "c"*64,
            "mode_candidate_selector_sha256": {m:"d"*64 for m in COUNTS},
            "baseline": {m:tickets[:n] for m,n in COUNTS.items()},
            "candidate": {m:tickets[:n] for m,n in COUNTS.items()},
            "formal": False,
            "model_improvement_proven": False
        }

    def result(self):
        return {"race_code":"202611070101", "status":"confirmed", "finish_order":[1,2,3],
                "confirmed_at_jst":"2026-11-07T08:50:00+09:00",
                "collected_at_jst":"2026-11-07T08:51:00+09:00",
                "source_url":"https://boatracecsv.github.io/data/results/realtime/2026/11/07.csv",
                "source_sha256":"e"*64}

    def test_protocol_is_locked_and_nov05_cannot_enter(self):
        self.assertEqual(protocol_check(self.policy)["pilot_races"],300)
        changed=copy.deepcopy(self.policy); changed["early_stopping_allowed"]=True
        with self.assertRaisesRegex(ValueError,"changed_forward_protocol"):
            protocol_check(changed)
        row=self.row()
        row["race_code"]="202611050101"
        row["deadline_jst"]="2026-11-05T08:35:00+09:00"
        report=score([row],{},self.policy)
        self.assertEqual(report["eligible_roster_count"],0)
        self.assertIn("date_or_model_version_mismatch",report["excluded_before_result_read"])

    def test_real_reference_result_is_never_formal(self):
        row=self.row()
        report=score([row],{row["race_code"]:self.result()},self.policy)
        self.assertEqual(report["matched_by_phase"],{"pilot":1})
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]["baseline"],1)
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]["candidate"],1)
        self.assertFalse(report["formal"])
        self.assertFalse(report["model_improvement_proven"])
        self.assertFalse(report["independent_first_remote_receipt_verified"])
        self.assertFalse(report["model_promotion_allowed"])

    def test_missing_result_never_becomes_miss(self):
        row=self.row()
        report=score([row],{},self.policy)
        self.assertEqual(report["pending_result_codes"],[row["race_code"]])
        self.assertEqual(report["matched_by_phase"],{})
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]["denominator_reference_only"],0)

    def test_outcome_in_input_and_same_second_are_refused(self):
        row=self.row();row["finish_order"]=[1,2,3]
        self.assertIn("outcome_leak_in_pre_result_roster",
                      score([row],{},self.policy)["excluded_before_result_read"])
        row=self.row();row["candidate_github_observed_jst"]=row["candidate_generated_jst"]
        self.assertIn("late_or_same_second_T12",
                      score([row],{},self.policy)["excluded_before_result_read"])
        row=self.row();row["official_odds_complete_120"]=False
        self.assertIn("incomplete_or_postrace_feature",
                      score([row],{},self.policy)["excluded_before_result_read"])
        for exhibition in (False, None):
            row=self.row()
            if exhibition is None:
                row.pop("official_exhibition_complete_6")
            else:
                row["official_exhibition_complete_6"]=exhibition
            self.assertIn("incomplete_or_postrace_feature",
                          score([row],{},self.policy)["excluded_before_result_read"])

    def test_mixed_invalid_future_roster_refused_without_backfill(self):
        valid = self.row()
        rejected = copy.deepcopy(valid)
        rejected["race_code"] = "202611070102"
        rejected["deadline_jst"] = "2026-11-07T08:40:00+09:00"
        rejected["candidate_github_observed_jst"] = rejected["candidate_generated_jst"]
        # The second row must not be silently omitted and replaced by a
        # later valid candidate in the first fixed 600 forecast slots.
        with self.assertRaisesRegex(ValueError, "incomplete_candidate_roster_no_replacement"):
            score([valid, rejected], {valid["race_code"]: self.result()}, self.policy)
        with self.assertRaisesRegex(ValueError, "incomplete_candidate_roster_no_replacement"):
            score([rejected, valid], {valid["race_code"]: self.result()}, self.policy)

    def test_original_remote_observation_must_precede_candidate(self):
        # A candidate that predates the original GitHub observation is not
        # the reproducible, result-blind post-publication shadow we registered.
        for field, value in (
            ("baseline_github_observed_jst", "2026-11-07T08:10:00.500000+09:00"),
            ("candidate_generated_jst", "2026-11-07T08:10:01+09:00"),
            ("candidate_generated_jst", "2026-11-07T08:10:02.500000+09:00"),
            ("candidate_github_observed_jst", "2026-11-07T08:10:05.500000+09:00"),
        ):
            with self.subTest(field=field, value=value):
                row = self.row()
                row[field] = value
                verdict = score([row], {}, self.policy)
                self.assertEqual(verdict["eligible_roster_count"], 0)
                self.assertIn("late_or_same_second_T12",
                              verdict["excluded_before_result_read"])

    def test_candidate_rank_losses_cannot_be_hidden(self):
        row=self.row()
        original=row["candidate"]["hit"]
        row["candidate"]["hit"]=original[1:]+["6-5-4"]
        report=score([row],{row["race_code"]:self.result()},self.policy)
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]["lost"],1)
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]["candidate"],0)

    def test_candidate_selector_drift_and_duplicate_are_rejected(self):
        a=self.row();b=copy.deepcopy(a)
        b["race_code"]="202611070102"
        b["mode_candidate_selector_sha256"]["hit"]="f"*64
        with self.assertRaisesRegex(ValueError,"selector_changed_across_future_races"):
            score([a,b],{},self.policy)
        with self.assertRaisesRegex(ValueError,"duplicate_candidate"):
            score([a,a],{},self.policy)

    def test_forged_source_or_collection_clock_is_excluded(self):
        row=self.row()
        for field,replacement in (
            ("source_url","https://example.org/confirmed.csv"),
            ("collected_at_jst","2026-11-07T08:00:00+09:00"),
            # Collector's bounded 3-minute skew tolerance must not
            # establish research-grade confirmed-result chronology.
            ("collected_at_jst","2026-11-07T08:49:00+09:00"),
        ):
            with self.subTest(field=field):
                result=self.result()
                result[field]=replacement
                report=score([row],{row["race_code"]:result},self.policy)
                self.assertEqual(report["matched_by_phase"],{})
                self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]
                                 ["denominator_reference_only"],0)
                self.assertIn("untrusted_result_or_time",
                              report["invalid_result_counts"])

    def test_untrusted_result_is_not_scored(self):
        row=self.row();result=self.result()
        result["confirmed_at_jst"]="2026-11-07T08:10:00+09:00"
        report=score([row],{row["race_code"]:result},self.policy)
        self.assertEqual(report["matched_by_phase"],{})
        self.assertIn("untrusted_result_or_time",report["invalid_result_counts"])

    def test_empty_phase_progress_is_unstarted_and_never_certified(self):
        report = score([], {}, self.policy)
        for phase in ("pilot", "confirmation"):
            progress = report["phase_progress"][phase]
            self.assertEqual(progress["reference_status"], "not_started")
            self.assertEqual(progress["reserved_pre_result_slots_reference_only"], 0)
            self.assertEqual(progress["unreserved_slots"], 300)
            self.assertEqual(progress["formally_certified_pairs"], 0)
            self.assertEqual(
                progress["formal_status"],
                "not_started_unverified_first_receipt_and_official_T12")
        self.assertFalse(report["formal"])

    def test_pending_and_invalid_results_reserve_slots_not_losses(self):
        a = self.row()
        b = copy.deepcopy(a)
        b["race_code"] = "202611070102"
        b["deadline_jst"] = "2026-11-07T08:40:00+09:00"
        result = self.result()
        result["race_code"] = b["race_code"]
        result["finish_order"] = [1, 1, 3]  # invalid result is not a miss
        report = score([a, b], {b["race_code"]: result}, self.policy)
        pilot = report["phase_progress"]["pilot"]
        self.assertEqual(pilot["reserved_pre_result_slots_reference_only"], 2)
        self.assertEqual(pilot["pending_result_slots"], 1)
        self.assertEqual(pilot["invalid_result_slots"], 1)
        self.assertEqual(pilot["matched_result_pairs_reference_only"], 0)
        self.assertEqual(pilot["reference_status"], "collecting_reference_only")
        self.assertEqual(pilot["formally_certified_pairs"], 0)
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]["lost"], 0)

    def test_fixed_300_301_boundary_without_result_based_backfill(self):
        # Synthetic pre-result fixtures, not real forecast evidence.
        rows = []
        for i in range(301):
            row = self.row()
            day = "07" if i < 288 else "08"
            index = i if i < 288 else i - 288
            venue = index // 12 + 1
            race = index % 12 + 1
            row["race_code"] = f"202611{day}{venue:02d}{race:02d}"
            if day == "08":
                for key in (
                    "deadline_jst", "official_source_received_jst",
                    "baseline_generated_jst", "baseline_github_observed_jst",
                    "candidate_generated_jst", "candidate_github_observed_jst"):
                    row[key] = row[key].replace("2026-11-07", "2026-11-08")
            rows.append(row)
        report = score(list(reversed(rows)), {}, self.policy)
        pilot = report["phase_progress"]["pilot"]
        confirmation = report["phase_progress"]["confirmation"]
        self.assertEqual((pilot["reserved_pre_result_slots_reference_only"],
                          confirmation["reserved_pre_result_slots_reference_only"]),
                         (300, 1))
        self.assertEqual((pilot["pending_result_slots"],
                          confirmation["pending_result_slots"]), (300, 1))
        self.assertEqual((pilot["unreserved_slots"],
                          confirmation["unreserved_slots"]), (0, 299))
        self.assertEqual(confirmation["reference_status"],
                         "collecting_reference_only")
        self.assertEqual(pilot["formally_certified_pairs"], 0)
        self.assertEqual(confirmation["formally_certified_pairs"], 0)

    def test_full_synthetic_reference_phase_does_not_upgrade_formal(self):
        # This verifies only the reporting vocabulary on test fixtures.
        rows, results = [], {}
        for venue in range(1, 25):
            for race in range(1, 13):
                row = self.row()
                code = f"20261107{venue:02d}{race:02d}"
                row["race_code"] = code
                result = self.result()
                result["race_code"] = code
                results[code] = result
                rows.append(row)
        for race in range(1, 13):
            row = self.row()
            row["race_code"] = f"2026110801{race:02d}"
            for key in (
                "deadline_jst", "official_source_received_jst",
                "baseline_generated_jst", "baseline_github_observed_jst",
                "candidate_generated_jst", "candidate_github_observed_jst"):
                row[key] = row[key].replace("2026-11-07", "2026-11-08")
            result = self.result()
            result["race_code"] = row["race_code"]
            for key in ("confirmed_at_jst", "collected_at_jst"):
                result[key] = result[key].replace("2026-11-07", "2026-11-08")
            result["source_url"] = result["source_url"].replace("/07.csv", "/08.csv")
            results[row["race_code"]] = result
            rows.append(row)
        report = score(rows, results, self.policy)
        pilot = report["phase_progress"]["pilot"]
        self.assertEqual(pilot["reference_status"], "reference_complete_nonformal")
        self.assertEqual(pilot["matched_result_pairs_reference_only"], 300)
        self.assertEqual(pilot["formally_certified_pairs"], 0)
        self.assertEqual(pilot["formal_status"],
                         "not_started_unverified_first_receipt_and_official_T12")
        self.assertFalse(report["model_improvement_proven"])
        self.assertFalse(report["model_promotion_allowed"])

    def test_pre_result_roster_digest_ignores_order_and_result_timing(self):
        a = self.row()
        b = copy.deepcopy(a)
        b["race_code"] = "202611070102"
        b["deadline_jst"] = "2026-11-07T08:40:00+09:00"
        baseline = score([a, b], {}, self.policy)
        after = score([b, a], {a["race_code"]: self.result()}, self.policy)
        digest = baseline["selected_pre_result_roster_sha256_reference_only"]
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(digest,
            after["selected_pre_result_roster_sha256_reference_only"])
        self.assertFalse(after["formal"])
        modified = copy.deepcopy(b)
        modified["candidate"]["hit"][0], modified["candidate"]["hit"][1] = (
            modified["candidate"]["hit"][1], modified["candidate"]["hit"][0])
        altered = score([a, modified], {}, self.policy)
        self.assertNotEqual(digest,
            altered["selected_pre_result_roster_sha256_reference_only"])
        # No remote-first-receipt evidence is created by hashing local input.
        self.assertFalse(altered["independent_first_remote_receipt_verified"])
        self.assertEqual(altered["phase_progress"]["pilot"]["formally_certified_pairs"], 0)

    def test_fixed_600_overflow_is_explicit_and_not_backfilled(self):
        # 601 synthetic pre-result entries across 3 days; none is real data.
        rows = []
        for i in range(601):
            day = 7 + i // 288
            offset = i % 288
            venue, race = offset // 12 + 1, offset % 12 + 1
            row = self.row()
            row["race_code"] = f"202611{day:02d}{venue:02d}{race:02d}"
            for key in (
                "deadline_jst", "official_source_received_jst",
                "baseline_generated_jst", "baseline_github_observed_jst",
                "candidate_generated_jst", "candidate_github_observed_jst"):
                row[key] = row[key].replace("2026-11-07",
                                            f"2026-11-{day:02d}")
            rows.append(row)
        first_600 = score(rows[:600], {}, self.policy)
        with_extra = score(list(reversed(rows)), {}, self.policy)
        self.assertEqual(
            first_600["selected_pre_result_roster_sha256_reference_only"],
            with_extra["selected_pre_result_roster_sha256_reference_only"])
        self.assertEqual(first_600["candidate_records_after_fixed_600_not_scored"], 0)
        self.assertEqual(with_extra["candidate_records_after_fixed_600_not_scored"], 1)
        self.assertEqual(with_extra["valid_pre_result_candidate_records_reference_only"], 601)
        self.assertEqual(with_extra["eligible_roster_count"], 600)
        self.assertEqual(with_extra["phase_progress"]["pilot"]["pending_result_slots"], 300)
        self.assertEqual(with_extra["phase_progress"]["confirmation"]["pending_result_slots"], 300)
        self.assertEqual(with_extra["phase_progress"]["confirmation"]["formally_certified_pairs"], 0)

    def test_reference_digest_changes_if_pre_result_clock_claim_changes(self):
        row = self.row()
        before = score([row], {}, self.policy)
        updated = copy.deepcopy(row)
        # Still valid chronological order, but different claimant-supplied
        # observation time MUST change the local digest.
        updated["candidate_github_observed_jst"] = "2026-11-07T08:10:09+09:00"
        after = score([updated], {}, self.policy)
        self.assertNotEqual(before["selected_pre_result_roster_sha256_reference_only"],
                            after["selected_pre_result_roster_sha256_reference_only"])
        self.assertFalse(after["formal"])
        self.assertFalse(after["independent_first_remote_receipt_verified"])

    def test_topn_paired_reference_rates_show_gains_losses_without_significance(self):
        a = self.row()
        b = copy.deepcopy(a)
        b["race_code"] = "202611070102"
        b["deadline_jst"] = "2026-11-07T08:40:00+09:00"
        c = copy.deepcopy(a)
        c["race_code"] = "202611070103"
        c["deadline_jst"] = "2026-11-07T08:45:00+09:00"
        for row in (a, b):
            row["candidate"]["hit"][0] = "6-5-4"
        gain = self.result()
        gain["finish_order"] = [6, 5, 4]
        loss = self.result()
        loss["race_code"] = b["race_code"]
        report = score([c, b, a], {
            a["race_code"]: gain, b["race_code"]: loss}, self.policy)
        top1 = report["scores"]["pilot"]["hit"]["top1"]
        self.assertEqual(
            tuple(top1[k] for k in ("baseline", "candidate", "gained", "lost")),
            (1, 1, 1, 1))
        self.assertEqual(top1["both_hit_reference_only"], 0)
        self.assertEqual(top1["neither_hit_reference_only"], 0)
        self.assertEqual(top1["paired_discordant_reference_only"], 2)
        self.assertEqual(top1["denominator_reference_only"], 2)
        self.assertEqual(top1["baseline_hit_pct_reference_only"], 50.0)
        self.assertEqual(top1["candidate_hit_pct_reference_only"], 50.0)
        self.assertEqual(top1["net_gain_pp_reference_only"], 0.0)
        self.assertEqual(report["phase_progress"]["pilot"]["pending_result_slots"], 1)
        self.assertIsNone(
            report["scores"]["confirmation"]["hit"]["top10"]
                ["net_gain_pp_reference_only"])
        self.assertFalse(report["formal"])
        self.assertFalse(report["model_improvement_proven"])

    def test_exact_two_sided_paired_discordance_math_and_invalid_cases(self):
        self.assertEqual(exact_mcnemar_two_sided_reference(0, 0), 1.0)
        self.assertEqual(exact_mcnemar_two_sided_reference(1, 0), 1.0)
        self.assertEqual(exact_mcnemar_two_sided_reference(8, 0), 0.0078125)
        self.assertEqual(exact_mcnemar_two_sided_reference(0, 8), 0.0078125)
        self.assertEqual(exact_mcnemar_two_sided_reference(1, 1), 1.0)
        self.assertGreater(exact_mcnemar_two_sided_reference(299, 1), 0.0)
        for gained, lost in ((-1, 0), (301, 0), (True, 0), (3.0, 0)):
            with self.subTest(gained=gained, lost=lost):
                with self.assertRaisesRegex(ValueError, "invalid_paired_discordance"):
                    exact_mcnemar_two_sided_reference(gained, lost)

    def test_holm_reference_requires_full_cohort_five_days_and_four_modes(self):
        policy = self.policy
        data = {"confirmation": {
            m: {"top10": {"gained": 0, "lost": 0}} for m in COUNTS}}
        data["confirmation"]["hit"]["top10"]["gained"] = 8
        data["confirmation"]["balance"]["top10"]["gained"] = 7
        progress = {
            "pilot": {"matched_result_pairs_reference_only": 300},
            "confirmation": {"matched_result_pairs_reference_only": 299}}
        days = {"2026-11-12", "2026-11-13", "2026-11-14",
                "2026-11-15", "2026-11-16"}
        blocked = confirmation_holm_reference(data, progress, days, policy)
        self.assertEqual(blocked["status"],
                         "pilot_or_confirmation_not_fully_scored_reference")
        self.assertIsNone(blocked["p_values_reference_only"])
        progress["confirmation"]["matched_result_pairs_reference_only"] = 300
        only_four_days = confirmation_holm_reference(
            data, progress, sorted(days)[:4], policy)
        self.assertEqual(only_four_days["status"],
                         "insufficient_distinct_confirmation_dates")
        self.assertIsNone(only_four_days["holm_reject_reference_only"])
        ready = confirmation_holm_reference(data, progress, days, policy)
        self.assertEqual(ready["status"],
                         "numerical_holm_reference_only_not_certified")
        self.assertEqual(ready["comparison_count"], 4)
        self.assertTrue(ready["holm_reject_reference_only"]["hit"])
        self.assertTrue(ready["holm_reject_reference_only"]["balance"])
        self.assertFalse(ready["holm_reject_reference_only"]["narrow"])
        self.assertFalse(ready["holm_reject_reference_only"]["hole"])
        self.assertTrue(ready["candidate_positive_and_holm_reference_only"]["hit"])
        self.assertFalse(ready["formal"])
        self.assertFalse(ready["model_improvement_proven"])
        self.assertFalse(ready["model_promotion_allowed"])

    def test_full_synthetic_600_reference_significance_never_admits_formal(self):
        # Synthetic perfectly favorable confirmation results are intentionally
        # unrealistic; they prove a very tiny numerical p never promotes a model.
        rows, outcomes = [], {}
        for day_offset in range(10):
            day = 7 + day_offset
            for i in range(60):
                row = self.row()
                row["race_code"] = f"202611{day:02d}{i//12+1:02d}{i%12+1:02d}"
                for key in ("deadline_jst", "official_source_received_jst",
                            "baseline_generated_jst", "baseline_github_observed_jst",
                            "candidate_generated_jst", "candidate_github_observed_jst"):
                    row[key] = row[key].replace(
                        "2026-11-07", f"2026-11-{day:02d}")
                result = self.result()
                result["race_code"] = row["race_code"]
                for key in ("confirmed_at_jst", "collected_at_jst"):
                    result[key] = result[key].replace(
                        "2026-11-07", f"2026-11-{day:02d}")
                result["source_url"] = result["source_url"].replace(
                    "/07.csv", f"/{day:02d}.csv")
                if day_offset >= 5:
                    row["candidate"]["hit"][-1] = "6-5-4"
                    result["finish_order"] = [6, 5, 4]
                rows.append(row)
                outcomes[row["race_code"]] = result
        result = score(rows, outcomes, self.policy)
        test = result["confirmation_top10_holm_reference_only"]
        self.assertEqual(test["distinct_confirmed_confirmation_dates"], 5)
        self.assertEqual(test["status"],
                         "numerical_holm_reference_only_not_certified")
        self.assertLess(test["p_values_reference_only"]["hit"], 0.0001)
        self.assertTrue(test["candidate_positive_and_holm_reference_only"]["hit"])
        self.assertEqual(result["phase_progress"]["pilot"]["matched_result_pairs_reference_only"], 300)
        self.assertEqual(result["phase_progress"]["confirmation"]["matched_result_pairs_reference_only"], 300)
        self.assertEqual(result["phase_progress"]["confirmation"]["formally_certified_pairs"], 0)
        self.assertFalse(result["formal"])
        self.assertFalse(result["model_improvement_proven"])
        self.assertFalse(result["model_promotion_allowed"])
        outcomes.pop(rows[-1]["race_code"])
        pending = score(rows, outcomes, self.policy)
        self.assertEqual(
            pending["confirmation_top10_holm_reference_only"]["status"],
            "pilot_or_confirmation_not_fully_scored_reference")
        self.assertIsNone(
            pending["confirmation_top10_holm_reference_only"]["p_values_reference_only"])

    def scenario_bridge(self):
        original = self.row()["baseline"]
        return {
            "schema": "ALL_MODE_SCENARIO_BRIDGE_EXPLORATORY_V1",
            "mixed_120_board_sha256": "a" * 64,
            "mode_ticket_budgets": dict(COUNTS),
            "existing_four_mode_selector_on_mixture": {
                mode: {"tickets": [{"combo": combo, "p": 0.5}
                                   for combo in combos]}
                for mode, combos in original.items()
            },
            "source_feature_provenance_independently_verified": False,
            "verified_official_six_exhibition_and_120_odds": False,
            "first_remote_receipt_verified": False,
            "scenario_weights_calibrated": False,
            "probabilities_calibrated": False,
            "confirmed_results_read": False,
            "formal": False,
            "forecast_usable": False,
            "betting_recommendation": False,
            "production_changed": False,
            "model_improvement_proven": False,
            "promotion_allowed": False,
        }

    def test_1710_scenario_preflight_exposes_ticket_changes_not_hits(self):
        original = self.row()["baseline"]
        bridge = self.scenario_bridge()
        hit = bridge["existing_four_mode_selector_on_mixture"]["hit"]["tickets"]
        hit[0]["combo"], hit[1]["combo"] = hit[1]["combo"], hit[0]["combo"]
        result = preflight_unregistered_scenario_bridge(original, bridge)
        self.assertTrue(result["comparison"]["hit"]["top1_exact_combo_changed"])
        self.assertFalse(result["comparison"]["narrow"]["top1_exact_combo_changed"])
        self.assertEqual(
            result["comparison"]["hit"]["topn_exposure_result_blind"]["top1"]
                  ["new_tickets_not_hits"], 1)
        self.assertFalse(
            result["comparison"]["hit"]["topn_exposure_result_blind"]["top3"]
                  ["membership_changed"])
        self.assertTrue(result["requires_new_future_only_preregistration"])
        self.assertFalse(result["confirmed_results_read"])
        self.assertFalse(result["winning_hit_gain_or_loss_computed"])
        self.assertFalse(result["candidate_eligible_for_1693_registered_600"])
        self.assertFalse(result["model_promotion_allowed"])

    def test_1710_scenario_false_formal_and_malformed_ticket_rejected(self):
        original = self.row()["baseline"]
        for key, value in (
            ("formal", True),
            ("confirmed_results_read", True),
            ("source_feature_provenance_independently_verified", True),
            ("first_remote_receipt_verified", True),
            ("promotion_allowed", True),
        ):
            bad = self.scenario_bridge()
            bad[key] = value
            with self.subTest(field=key):
                with self.assertRaisesRegex(
                    ValueError, "outcome_or_forged_scenario_certification"):
                    preflight_unregistered_scenario_bridge(original, bad)
        bad = self.scenario_bridge()
        bad["finish_order"] = [1, 2, 3]
        with self.assertRaisesRegex(ValueError, "outcome_or_forged"):
            preflight_unregistered_scenario_bridge(original, bad)
        bad = self.scenario_bridge()
        bad["existing_four_mode_selector_on_mixture"]["hole"]["tickets"][1]["combo"] = (
            bad["existing_four_mode_selector_on_mixture"]["hole"]["tickets"][0]["combo"])
        with self.assertRaisesRegex(ValueError, "invalid_or_changed_ticket_budget"):
            preflight_unregistered_scenario_bridge(original, bad)
        bad = self.scenario_bridge()
        bad["existing_four_mode_selector_on_mixture"]["hit"]["tickets"][0]["p"] = float("nan")
        with self.assertRaisesRegex(ValueError, "invalid_scenario_mode_ticket"):
            preflight_unregistered_scenario_bridge(original, bad)

    def test_1710_unregistered_metadata_can_never_enter_1693_roster(self):
        row = self.row()
        for field, value in (
            ("scenario_bridge", self.scenario_bridge()),
            ("scenario_candidate_study_id", "new_unregistered_future_model"),
            ("unregistered_scenario_model", True),
        ):
            invalid = copy.deepcopy(row)
            invalid[field] = value
            result = score([invalid], {}, self.policy)
            self.assertEqual(result["eligible_roster_count"], 0)
            self.assertIn("scenario_candidate_requires_separate_future_registration",
                          result["excluded_before_result_read"])
            self.assertFalse(result["formal"])
            self.assertFalse(result["model_promotion_allowed"])

    def test_narrow_nominal_top10_is_effectively_top5(self):
        row = self.row()
        report = score([row], {row["race_code"]: self.result()}, self.policy)
        narrow = report["scores"]["pilot"]["narrow"]
        self.assertEqual(narrow["top10"]["requested_topn"], 10)
        self.assertEqual(narrow["top10"]["effective_ticket_count"], 5)
        self.assertTrue(narrow["top10"]["requested_topn_exceeds_mode_budget"])
        self.assertEqual(narrow["top10"]["baseline"], narrow["top5"]["baseline"])
        self.assertEqual(narrow["top10"]["candidate"], narrow["top5"]["candidate"])
        self.assertEqual(report["scores"]["pilot"]["hit"]["top10"]
                         ["effective_ticket_count"], 10)
        self.assertFalse(report["scores"]["pilot"]["hit"]["top10"]
                         ["requested_topn_exceeds_mode_budget"])
        self.assertEqual(report["scores"]["pilot"]["hole"]["top10"]
                         ["effective_ticket_count"], 10)
        self.assertIsNone(report["topn_regression_diagnostics_reference_only"]
                          ["confirmation"]["any_mode_topn_with_fewer_hits_reference_only"])
        self.assertFalse(report["formal"])

    def test_top10_gain_can_coexist_with_top1_regression(self):
        a = self.row()
        b = copy.deepcopy(a)
        b["race_code"] = "202611070102"
        b["deadline_jst"] = "2026-11-07T08:40:00+09:00"
        old_a = a["candidate"]["hit"]
        a["candidate"]["hit"] = [old_a[1], old_a[0]] + old_a[2:]
        b["candidate"]["hit"] = b["candidate"]["hit"][:-1] + ["6-5-4"]
        r1 = self.result()
        r2 = self.result()
        r2["race_code"] = b["race_code"]
        r2["finish_order"] = [6, 5, 4]
        report = score([b, a], {a["race_code"]: r1, b["race_code"]: r2},
                       self.policy)
        hit = report["scores"]["pilot"]["hit"]
        self.assertEqual(hit["top1"]["baseline"] - hit["top1"]["candidate"], 1)
        self.assertEqual(hit["top10"]["candidate"] - hit["top10"]["baseline"], 1)
        diagnostic = report["topn_regression_diagnostics_reference_only"]["pilot"]
        self.assertEqual(diagnostic["same_race_denominator_reference_only"], 2)
        self.assertEqual(diagnostic["modes"]["hit"]
                         ["topn_with_fewer_hits_reference_only"], ["top1"])
        self.assertEqual(diagnostic["modes"]["hit"]
                         ["top10_primary_net_change_reference_only"], 1)
        self.assertTrue(diagnostic["any_mode_topn_with_fewer_hits_reference_only"])
        self.assertEqual(diagnostic["status"], "descriptive_only_not_a_release_gate")
        self.assertFalse(report["formal"])
        self.assertFalse(report["model_promotion_allowed"])

    def test_1710_preflight_labels_narrow_effective_topn(self):
        result = preflight_unregistered_scenario_bridge(
            self.row()["baseline"], self.scenario_bridge())
        x = result["comparison"]["narrow"]["topn_exposure_result_blind"]["top10"]
        self.assertEqual(x["requested_topn"], 10)
        self.assertEqual(x["effective_ticket_count"], 5)
        self.assertTrue(x["requested_topn_exceeds_mode_budget"])
        self.assertEqual(x["original_ticket_count"], 5)
        self.assertEqual(x["scenario_ticket_count"], 5)
        self.assertFalse(result["candidate_eligible_for_1693_registered_600"])

    def test_hidden_postrace_metadata_cannot_enter_locked_600(self):
        for payload in (
            {"research_note": {"result": [1, 2, 3]}},
            {"captured": [{"status": {"confirmed_at_jst": "2026-11-07T08:52:00+09:00"}}]},
            {"environment": {"post_race_weather": {"wave_cm": 15}}},
        ):
            with self.subTest(payload=payload):
                row = self.row()
                row["optional_metadata"] = payload
                report = score([row], {}, self.policy)
                self.assertEqual(report["eligible_roster_count"], 0)
                self.assertIn("outcome_leak_in_pre_result_roster",
                              report["excluded_before_result_read"])
                self.assertEqual(
                    report["phase_progress"]["pilot"]["formally_certified_pairs"], 0)
                self.assertFalse(report["model_promotion_allowed"])

    def test_scenario_bridge_nested_result_data_rejected_before_exposure(self):
        bridge = self.scenario_bridge()
        bridge["research_attribution"] = [
            {"extra": {"winning_combo": "1-2-3"}}]
        with self.assertRaisesRegex(
                ValueError, "outcome_or_forged_scenario_certification"):
            preflight_unregistered_scenario_bridge(
                self.row()["baseline"], bridge)

    def nov10_official_pair_report_reference_shape(self):
        # Representative STRUCTURE from independently audited upstream #1694.
        # Not downloaded source bytes; the ④ consumer is NOT an origin auditor.
        dates = [
            ("202611101202", True, 6, "15:40:00", "15:38:04"),
            ("202611102211", False, 0, "15:46:00", "15:38:23"),
        ]
        rows = []
        for code, ready, six, limit, last in dates:
            modes = {}
            for label, generation in (
                ("clean", "2026-11-10T07:44:29+09:00"),
                ("v2_four_mode", "2026-11-10T01:39:35+09:00"),
            ):
                modes[label] = {
                    "generated_at_jst": generation,
                    "generated_after_pair_sources": False,
                    "generated_before_t12": True,
                    "first_forecast_git_remote_acceptance_verified": False,
                    "actual_model_official_original_bytes_consumption_verified": False,
                    "formal": False,
                }
            rows.append({
                "race_code": code,
                "source_pair_complete_by_t12": ready,
                "exhibition_time_observed_boats": six,
                "official_odds_120_verified": True,
                "last_original_source_received_jst":
                    f"2026-11-10T{last}+09:00",
                "official_t12_cutoff_jst":
                    f"2026-11-10T{limit}+09:00",
                "independent_source_zip_published_by_t12": True,
                "official_racelist_original_replayed": False,
                "frozen_forecasts": modes,
                "model_consumption_proven": False,
                "first_forecast_git_remote_acceptance_proven": False,
                "formal": False,
            })
        return {
            "schema": "T12_PINNED_SCHEDULED_PAIR_FROZEN_REPLAY_V1",
            "day_jst": "20261110",
            "source_run_id": 42769768447,
            "source_artifact_id": 13740574410,
            "source_original_zip_sha256_from_metadata":
                "cdfdeae53222a5b7852ba5cf5b6b44080247ec074c8d3dbaf53c4a32fe9706dd",
            "pinned_forecast_ref":
                "c4d39245cbc96b6c680585a68c3b9adf6ddeb921",
            "github_server_source_archive_published_at_utc":
                "2026-11-10T06:38:25+00:00",
            "original_zip_directly_rehashed_inside_ci": False,
            "source_originals_individually_replayed": True,
            "original_source_candidate_races": 2,
            "complete_two_original_races": 1,
            "matched_immutable_forecasts": 4,
            "forecasts_generated_after_originals": 0,
            "same_race_complete_official_three_originals": 0,
            "verified_model_original_byte_consumption": 0,
            "verified_first_forecast_remote_acceptances": 0,
            "new_formal_certifications": 0,
            "formal_accuracy_denominator": None,
            "race_rows": rows,
            "formal": False,
            "t12_eligible": False,
            "accuracy_scoring_allowed": False,
        }

    def test_nov10_upstream_real_shape_handoff_reports_per_race_blockers(self):
        x = review_upstream_t12_source_pair_handoff(
            self.nov10_official_pair_report_reference_shape())
        self.assertEqual(x["upstream_race_count"], 2)
        by_code = {r["race_code"]: r for r in x["race_rows"]}
        suminoe = by_code["202611101202"]
        fukuoka = by_code["202611102211"]
        self.assertTrue(suminoe[
            "official_two_source_pair_complete_by_t12_reference_only"])
        self.assertFalse(fukuoka[
            "official_two_source_pair_complete_by_t12_reference_only"])
        self.assertIn("same_race_official_racelist_original_missing",
                      suminoe["blocking_gates"])
        self.assertIn("v2_original_generated_before_official_pair",
                      suminoe["blocking_gates"])
        self.assertIn(
            "beforeinfo_exhibition_six_or_odds120_or_cutoff_incomplete",
            fukuoka["blocking_gates"])
        self.assertEqual(x["blocking_gate_counts"][
            "same_race_official_racelist_original_missing"], 2)
        self.assertEqual(x["formal_candidate_pairs_added"], 0)
        self.assertEqual(x["pilot_added"], 0)
        self.assertEqual(x["confirmation_added"], 0)
        self.assertFalse(x["formal"])
        self.assertFalse(x["model_promotion_allowed"])

    def test_upstream_forged_formal_duplicate_race_and_totals_rejected(self):
        for changed in ("formal", "three", "first", "denominator",
                        "duplicate", "day", "paircount", "aftercount"):
            with self.subTest(changed=changed):
                r = self.nov10_official_pair_report_reference_shape()
                if changed == "formal":
                    r["formal"] = True
                elif changed == "three":
                    r["same_race_complete_official_three_originals"] = 1
                elif changed == "first":
                    r["verified_first_forecast_remote_acceptances"] = 1
                elif changed == "denominator":
                    r["formal_accuracy_denominator"] = 2
                elif changed == "duplicate":
                    r["race_rows"][1]["race_code"] = r["race_rows"][0]["race_code"]
                elif changed == "day":
                    r["race_rows"][0]["race_code"] = "202611111202"
                elif changed == "paircount":
                    r["complete_two_original_races"] = 2
                elif changed == "aftercount":
                    r["forecasts_generated_after_originals"] = 3
                with self.assertRaises(ValueError):
                    review_upstream_t12_source_pair_handoff(r)

    def test_upstream_wrong_generation_clock_and_result_leak_rejected(self):
        for mutation in ("reversed_generation", "fake_after_flag",
                         "concealed_result", "missing_v2"):
            with self.subTest(mutation=mutation):
                r = self.nov10_official_pair_report_reference_shape()
                row = r["race_rows"][0]
                if mutation == "reversed_generation":
                    row["frozen_forecasts"]["v2_four_mode"][
                        "generated_at_jst"] = "2026-11-10T15:50:00+09:00"
                elif mutation == "fake_after_flag":
                    row["frozen_forecasts"]["v2_four_mode"][
                        "generated_after_pair_sources"] = True
                elif mutation == "concealed_result":
                    row["auxiliary"] = [{"post_race_weather": {"mps": 4.5}}]
                elif mutation == "missing_v2":
                    del row["frozen_forecasts"]["v2_four_mode"]
                with self.assertRaises(ValueError):
                    review_upstream_t12_source_pair_handoff(r)

    def test_upstream_report_github_source_archive_clock_recomputed(self):
        base = self.nov10_official_pair_report_reference_shape()
        r = review_upstream_t12_source_pair_handoff(base)
        self.assertEqual(
            r["upstream_source_zip_published_at_utc_reference_only"],
            "2026-11-10T06:38:25+00:00")
        self.assertEqual(
            r["upstream_original_source_zip_sha256_reference_only"],
            base["source_original_zip_sha256_from_metadata"])
        self.assertEqual(
            r["upstream_pinned_forecast_commit_reference_only"],
            base["pinned_forecast_ref"])
        for changed in ("later_zip_publication", "cross_day_zip", "false_zip_by_t12",
                        "naive_zip", "wrong_timezone", "missing_zip_clock"):
            with self.subTest(changed=changed):
                report = self.nov10_official_pair_report_reference_shape()
                if changed == "later_zip_publication":
                    report["github_server_source_archive_published_at_utc"] = (
                        "2026-11-10T06:50:00+00:00")
                elif changed == "cross_day_zip":
                    report["github_server_source_archive_published_at_utc"] = (
                        "2026-11-11T06:38:25+00:00")
                elif changed == "false_zip_by_t12":
                    report["race_rows"][0][
                        "independent_source_zip_published_by_t12"] = False
                elif changed == "naive_zip":
                    report["github_server_source_archive_published_at_utc"] = (
                        "2026-11-10T06:38:25")
                elif changed == "wrong_timezone":
                    report["github_server_source_archive_published_at_utc"] = (
                        "2026-11-10T15:38:25+09:00")
                else:
                    del report["github_server_source_archive_published_at_utc"]
                with self.assertRaises(ValueError):
                    review_upstream_t12_source_pair_handoff(report)

    def test_upstream_report_source_archive_and_original_forecast_identity_rejected(self):
        for field, bad in (
            ("source_run_id", 0),
            ("source_run_id", True),
            ("source_artifact_id", "13740574410"),
            ("source_original_zip_sha256_from_metadata", "a"*64),
            ("source_original_zip_sha256_from_metadata", "not_sha256"),
            ("pinned_forecast_ref", "main"),
            ("pinned_forecast_ref", "0"*64),
            ("original_zip_directly_rehashed_inside_ci", True),
        ):
            with self.subTest(field=field,bad=bad):
                report = self.nov10_official_pair_report_reference_shape()
                report[field] = bad
                # A well-formed alternative source digest is not
                # authenticated here; no claim of matching known original.
                if field == "source_original_zip_sha256_from_metadata" and bad == "a"*64:
                    x = review_upstream_t12_source_pair_handoff(report)
                    self.assertFalse(
                        x["upstream_report_identity_independently_authenticated_here"])
                else:
                    with self.assertRaises(ValueError):
                        review_upstream_t12_source_pair_handoff(report)
        report = self.nov10_official_pair_report_reference_shape()
        report["attached"] = {"confirmed_result": "1-2-3"}
        with self.assertRaises(ValueError):
            review_upstream_t12_source_pair_handoff(report)

    def nov10_added_blob_witness_reference_shape(self):
        rows = []
        for race in ("202611101202", "202611102211"):
            modes = {}
            for mode, commit, run_id, folder, upper in (
                ("clean", "d5ec88ccd7bfec3b8c6844bbc0a3b47e61375eda",
                 42714563095, "prospective_predictions",
                 "2026-11-09T22:44:34+00:00"),
                ("v2_four_mode", "e79a99e5180892330fd3ce0b745893d3c6515ab8",
                 42657194420, "four_mode_forecasts",
                 "2026-11-09T16:40:45+00:00"),
            ):
                modes[mode] = {
                    "added_path": f"{folder}/{race}.json",
                    "added_git_commit": commit,
                    "exact_file_git_blob_sha1_matched": True,
                    "independent_github_run_id": run_id,
                    "github_remote_existed_no_later_utc": upper,
                    "existing_blob_predates_official_source": True,
                    "first_remote_acceptance_instant_proven": False,
                    "actual_original_byte_model_consumption_proven": False,
                    "formal": False,
                }
            upstream = self.nov10_official_pair_report_reference_shape()
            source = next(x for x in upstream["race_rows"]
                          if x["race_code"] == race)
            rows.append({
                "race_code": race,
                "official_t12_cutoff_jst": source["official_t12_cutoff_jst"],
                "last_source_received_jst":
                    source["last_original_source_received_jst"],
                "forecasts": modes,
                "formal": False,
            })
        return {
            "schema": "T12_NOV10_REMOTE_ADDED_BLOB_WITNESS_V1",
            "source_races": 2,
            "immutable_forecast_blobs_witnessed": 4,
            "remote_commit_existed_before_official_sources": 4,
            "exact_first_remote_git_acceptance_instants_verified": 0,
            "forecasts_proven_to_consume_official_originals": 0,
            "full_three_source_forecasts_verified": 0,
            "new_formal_certifications": 0,
            "formal_accuracy_denominator": None,
            "race_rows": rows,
            "formal": False,
            "accuracy_scoring_allowed": False,
        }

    def test_real_nov10_prior_github_remote_existence_not_first_receipt(self):
        source = self.nov10_official_pair_report_reference_shape()
        witness = self.nov10_added_blob_witness_reference_shape()
        x = review_upstream_pre_source_remote_existence(source, witness)
        self.assertEqual(x["old_forecast_commit_existence_upper_bounds"], 4)
        self.assertEqual(x["first_remote_git_acceptance_instants_proven"], 0)
        self.assertEqual(x["new_source_consuming_candidate_forecasts"], 0)
        self.assertEqual(x["pilot_added"], 0)
        self.assertEqual(x["confirmation_added"], 0)
        self.assertEqual(x["formal_candidate_pairs_added"], 0)
        self.assertFalse(x["upstream_witness_archive_independently_authenticated_here"])
        self.assertFalse(x["model_promotion_allowed"])
        self.assertEqual({r["race_code"] for r in x["race_rows"]},
                         {"202611101202", "202611102211"})
        self.assertTrue(all(
            r["existing_forecast_disqualified_from_post_source_study"]
            for r in x["race_rows"]))
        self.assertFalse(x["formal"])

    def test_upstream_remote_witness_same_race_and_commit_integrity(self):
        for change in ("cross_race", "duplicate", "mixed_mode_commit",
                       "wrong_added_path", "missing_mode", "forged_sha_match",
                       "wrong_run", "wrong_count", "changed_official_clock"):
            with self.subTest(change=change):
                source = self.nov10_official_pair_report_reference_shape()
                witness = self.nov10_added_blob_witness_reference_shape()
                row = witness["race_rows"][1]
                second = row["forecasts"]["v2_four_mode"]
                if change == "cross_race":
                    row["race_code"] = "202611100701"
                elif change == "duplicate":
                    row["race_code"] = witness["race_rows"][0]["race_code"]
                elif change == "mixed_mode_commit":
                    second["added_git_commit"] = "0"*40
                elif change == "wrong_added_path":
                    second["added_path"] = "four_mode_forecasts/202611101202.json"
                elif change == "missing_mode":
                    del row["forecasts"]["clean"]
                elif change == "forged_sha_match":
                    second["exact_file_git_blob_sha1_matched"] = False
                elif change == "wrong_run":
                    second["independent_github_run_id"] = 0
                elif change == "wrong_count":
                    witness["immutable_forecast_blobs_witnessed"] = 3
                else:
                    row["last_source_received_jst"] = "2026-11-10T14:01:00+09:00"
                with self.assertRaises(ValueError):
                    review_upstream_pre_source_remote_existence(source, witness)

    def test_upstream_remote_existence_not_first_or_post_source(self):
        for change in ("first_claim", "later_remote", "timezone",
                       "after_model_generation_but_after_source", "model_claim",
                       "false_pre_source", "forged_formal", "payout_leak"):
            with self.subTest(change=change):
                source = self.nov10_official_pair_report_reference_shape()
                witness = self.nov10_added_blob_witness_reference_shape()
                mode = witness["race_rows"][0]["forecasts"]["v2_four_mode"]
                if change == "first_claim":
                    mode["first_remote_acceptance_instant_proven"] = True
                elif change == "later_remote":
                    mode["github_remote_existed_no_later_utc"] = (
                        "2026-11-10T07:00:00+00:00")
                elif change == "timezone":
                    mode["github_remote_existed_no_later_utc"] = (
                        "2026-11-10T01:40:45+09:00")
                elif change == "after_model_generation_but_after_source":
                    mode["github_remote_existed_no_later_utc"] = (
                        "2026-11-10T06:39:00+00:00")
                elif change == "model_claim":
                    mode["actual_original_byte_model_consumption_proven"] = True
                elif change == "false_pre_source":
                    mode["existing_blob_predates_official_source"] = False
                elif change == "forged_formal":
                    witness["new_formal_certifications"] = 1
                else:
                    witness["metadata"] = [{"payout": 1234}]
                with self.assertRaises(ValueError):
                    review_upstream_pre_source_remote_existence(source, witness)


if __name__ == "__main__":
    unittest.main()
