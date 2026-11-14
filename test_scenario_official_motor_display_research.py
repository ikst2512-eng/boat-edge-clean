"""Synthetic-only checks: motor display != denominator-backed feature."""
from hashlib import sha256
import unittest

from scenario_official_motor_display_research import extract_motor_display_unqualified
from test_scenario_official_racelist_rates import synthetic_racelist


class IsolatedOfficialMotorDisplayTests(unittest.TestCase):
    def test_six_motor_display_rows_and_sha(self):
        raw = synthetic_racelist()
        out = extract_motor_display_unqualified(raw)
        self.assertEqual(out["source_sha256"], sha256(raw).hexdigest())
        self.assertEqual(len(out["rows"]), 6)
        self.assertEqual([r["boat"] for r in out["rows"]], list(range(1, 7)))
        self.assertEqual([r["registration_id"] for r in out["rows"]],
                         [str(i) for i in range(4510, 4516)])
        self.assertEqual([r["motor_number"] for r in out["rows"]], [32] * 6)
        self.assertEqual([r["displayed_motor_2ren_pct"] for r in out["rows"]],
                         [40.0] * 6)
        self.assertEqual([r["displayed_motor_3ren_pct"] for r in out["rows"]],
                         [50.0] * 6)
        self.assertTrue(all(r["motor_starts"] is None and
                            r["motor_2ren_successes"] is None
                            for r in out["rows"]))
        for blocked in ("sample_denominator_verified", "same_race_http_receipt_verified",
                        "pre_T12_receipt_verified", "input_to_matrix_allowed",
                        "formal", "production_changed"):
            self.assertIs(out[blocked], False, blocked)

    def test_missing_bad_or_nonprobability_motors_fail_closed(self):
        raw = synthetic_racelist()
        target = b"32<br>40.00<br>50.00"
        for mutation in (b"0<br>40.00<br>50.00",
                         b"32<br>140.00<br>50.00",
                         b"32<br>70.00<br>50.00",
                         b"32<br>??<br>50.00",
                         b"32<br>40.00<br>50.00<br>extra"):
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):
                    extract_motor_display_unqualified(raw.replace(target, mutation, 1))

    def test_wrong_motor_column_and_truncated_six_rows_fail(self):
        raw = synthetic_racelist()
        corrupted = raw.replace(
            b'<td class="is-lineH2" rowspan="4">32',
            b'<td class="wrong" rowspan="4">32', 1)
        with self.assertRaises(ValueError):
            extract_motor_display_unqualified(corrupted)
        cut = raw.find(b'<tr><td class="is-boatColor6')
        with self.assertRaises(ValueError):
            extract_motor_display_unqualified(raw[:cut] + b"</table></body></html>")

    def test_original_bytes_tamper_changes_digest_not_frozen_study(self):
        raw = synthetic_racelist()
        altered = raw.replace(b"32<br>40.00<br>50.00",
                              b"33<br>40.00<br>50.00", 1)
        first = extract_motor_display_unqualified(raw)
        second = extract_motor_display_unqualified(altered)
        self.assertNotEqual(first["source_sha256"], second["source_sha256"])
        self.assertEqual(second["rows"][0]["motor_number"], 33)
        self.assertFalse(second["input_to_matrix_allowed"])


if __name__ == "__main__":
    unittest.main()
