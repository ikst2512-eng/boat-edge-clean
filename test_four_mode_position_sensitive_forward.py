"""Forward-only, frozen-selector, result-last research contract (not formal)."""
from datetime import datetime
import hashlib
import json
from unittest.mock import patch
import unittest

from research_model import probabilities
from clean_four_modes import rank_modes
from four_mode_position_sensitive_forward import (
    PROTOCOL_BLOB_SHA1, _blob_sha1, compare_reference,
    freeze_candidate, protocol
)
from four_mode_position_sensitive_shadow import VERSION

RATES = [5.01, 5.89, 6.28, 2.64, 6.09, 6.15]


def archive(code="202611090101", deadline="2026-11-09T12:40:00+09:00",
            rates=None):
    v = list(rates if rates is not None else RATES)
    return {
        "schema": "CLEAN_FOUR_MODES_PREDEADLINE_V1",
        "race_code": code, "validated": False,
        "status": "provisional",
        "target_rates_not_proven": True,
        "model_version": "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED",
        "generated_at_jst": "2026-11-09T10:00:00+09:00",
        "deadline_jst": deadline,
        "source_title_received_jst": "2026-11-09T09:58:00+09:00",
        "source_cards_received_jst": "2026-11-09T09:59:00+09:00",
        "input_national_win_rates": v,
        "modes": rank_modes(probabilities(v)),
    }


def frozen(a=None, freeze="2026-11-09T10:05:00+09:00"):
    a = a or archive()
    data = json.dumps(a, ensure_ascii=False, sort_keys=True).encode()
    return freeze_candidate(data, freeze), data


def result(code="202611090101", finish=(1, 2, 3),
           confirmed="2026-11-09T12:45:00+09:00",
           collected="2026-11-09T13:01:00+09:00"):
    return {
        "race_code": code, "status": "confirmed",
        "finish_order": list(finish),
        "confirmed_at_jst": confirmed,
        "collected_at_jst": collected,
        "source_sha256": "a" * 64,
        "source_url": "https://boatracecsv.github.io/data/results/realtime/2026/11/09.csv",
    }


class ExplodingResults(dict):
    def get(self, *args):
        raise AssertionError("Outcome accessed before validation")


class ForwardSafetyTests(unittest.TestCase):
    def test_preregistration_and_pinned_selector_dependencies(self):
        p = protocol()
        self.assertEqual(p["candidate_model"], VERSION)
        self.assertEqual(p["pilot_races"], 300)
        self.assertEqual(p["confirmation_races"], 300)
        self.assertEqual(len(PROTOCOL_BLOB_SHA1), 40)
        self.assertFalse(p["promotion_allowed"])

    def test_snapshot_is_deterministic_result_blind_and_not_remote_attested(self):
        snap, original = frozen()
        same = freeze_candidate(original, "2026-11-09T10:05:00+09:00")
        self.assertEqual(snap, same)
        self.assertEqual(snap["baseline"]["hit"][0], "1-2-4")
        self.assertEqual(snap["candidate"]["hit"][0], "1-2-3")
        self.assertFalse(snap["formal"])
        self.assertFalse(snap["candidate_first_remote_receipt_verified"])
        self.assertFalse(snap["production_forecast_changed"])
        self.assertEqual(snap["original_forecast_sha256"], hashlib.sha256(original).hexdigest())

    def test_reject_registration_day_and_late_or_same_second(self):
        a = archive(code="202611080101", deadline="2026-11-08T12:40:00+09:00")
        a["generated_at_jst"] = "2026-11-08T10:00:00+09:00"
        a["source_title_received_jst"] = "2026-11-08T09:58:00+09:00"
        a["source_cards_received_jst"] = "2026-11-08T09:59:00+09:00"
        with self.assertRaises(ValueError):
            frozen(a, "2026-11-08T10:05:00+09:00")
        with self.assertRaises(ValueError):
            frozen(freeze="2026-11-09T12:28:00+09:00")
        with self.assertRaises(ValueError):
            frozen(freeze="2026-11-09T10:00:00+09:00")
        with self.assertRaises(ValueError):
            frozen(freeze="2026-11-09T10:01:00Z")

    def test_reject_postrace_leak_or_forged_original(self):
        a = archive()
        a["finish_order"] = [1, 2, 3]
        with self.assertRaises(ValueError):
            frozen(a)
        b = archive()
        b["modes"]["hit"]["tickets"][0]["p"] += 0.01
        with self.assertRaises(ValueError):
            frozen(b)
        c = archive()
        c["input_national_win_rates"][0] = float("nan")
        with self.assertRaises(ValueError):
            frozen(c)

    def test_invalid_candidate_rejected_before_any_result_access(self):
        snap, original = frozen()
        changed = json.loads(json.dumps(snap))
        changed["candidate"]["hit"][0] = changed["candidate"]["hit"][1]
        with self.assertRaises(ValueError):
            compare_reference([changed], {snap["race_code"]: original}, ExplodingResults())
        with self.assertRaises(ValueError):
            compare_reference([snap], {snap["race_code"]: original + b" "}, ExplodingResults())
        changed = json.loads(json.dumps(snap))
        changed["candidate_locally_frozen_at_jst"] = "2026-11-09T12:28:00+09:00"
        with self.assertRaises(ValueError):
            compare_reference([changed], {snap["race_code"]: original}, ExplodingResults())

    def test_result_last_paired_gains_losses_and_topn(self):
        snap, original = frozen()
        out = compare_reference([snap], {snap["race_code"]: original},
                                {snap["race_code"]: result(finish=(1,2,3))})
        self.assertFalse(out["formal"])
        self.assertFalse(out["model_improvement_proven"])
        self.assertEqual(out["eligible_frozen_candidate_slots"], 1)
        self.assertEqual(out["confirmed_result_counts"]["pilot"], 1)
        metric = out["by_phase_mode_topn"]["pilot"]["hit"]["1"]
        self.assertEqual(metric["baseline"], 0)
        self.assertEqual(metric["candidate"], 1)
        self.assertEqual(metric["gained"], 1)
        self.assertEqual(metric["lost"], 0)
        self.assertEqual(metric["reference_denominator"], 1)
        with self.assertRaises(ValueError):
            compare_reference([snap,snap], {snap["race_code"]: original}, {})

    def test_missing_result_keeps_its_slot_and_later_results_not_replacements(self):
        snap_a, original_a = frozen()
        b = archive("202611090102", deadline="2026-11-09T13:40:00+09:00")
        snap_b, original_b = frozen(b, "2026-11-09T10:06:00+09:00")
        out = compare_reference([snap_b, snap_a],
                                {snap_a["race_code"]: original_a,
                                 snap_b["race_code"]: original_b},
                                {snap_b["race_code"]: result("202611090102",
                                                              finish=(1,2,4),
                                                              confirmed="2026-11-09T13:45:00+09:00",
                                                              collected="2026-11-09T14:10:00+09:00")})
        self.assertEqual(out["pilot_reserved_slots"], 2)
        self.assertEqual(out["confirmed_result_counts"]["pilot"], 1)
        self.assertEqual(out["pending_race_codes"], ["202611090101"])

    def test_untrusted_results_excluded_from_denominator(self):
        snap, original = frozen()
        wrong = result(confirmed="2026-11-09T12:39:00+09:00")
        out = compare_reference([snap], {snap["race_code"]: original}, {snap["race_code"]: wrong})
        self.assertEqual(out["confirmed_result_counts"], {})
        self.assertEqual(out["invalid_result_race_codes"], ["202611090101"])
        self.assertIsNone(out.get("win_rate_improvement"))

    def test_preregistration_change_produces_hard_failure(self):
        with patch("four_mode_position_sensitive_forward.PROTOCOL_BLOB_SHA1", "0"*40):
            with self.assertRaises(ValueError):
                protocol()

    def test_empty_cohort_is_not_fabricated_prospective_success(self):
        out = compare_reference([], {}, {})
        self.assertEqual(out["eligible_frozen_candidate_slots"], 0)
        self.assertFalse(out["promotion_allowed"])
        self.assertFalse(out["candidate_first_remote_receipt_verified"])


if __name__ == "__main__":
    unittest.main()
