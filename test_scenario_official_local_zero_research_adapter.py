"""Synthetic-only guard for a separate local-0.00 research parsing adapter."""
import unittest

from scenario_official_local_zero_research_adapter import (
    STUDY_ID, extract_six_with_local_zero_research,
)
from scenario_official_racelist_rates import extract_six_official_racelist_rates
from test_scenario_official_racelist_rates import synthetic_racelist

LOCAL = b"4.50<br>36.00<br>45.00"


class OriginalVenueZeroResearchTests(unittest.TestCase):
    def test_local_zero_preserved_exactly_and_national_inputs_unchanged(self):
        raw = synthetic_racelist()
        changed = raw.replace(LOCAL, b"0.00<br>0.00<br>0.00", 1)
        self.assertNotEqual(raw, changed)
        with self.assertRaisesRegex(ValueError, "official_rate_or_start_out_of_bounds"):
            extract_six_official_racelist_rates(changed)
        parsed = extract_six_with_local_zero_research(changed)
        control = extract_six_official_racelist_rates(raw)
        self.assertEqual(parsed["study_id"], STUDY_ID)
        self.assertEqual(parsed["national_rates"], control["national_rates"])
        self.assertEqual(parsed["average_st"], control["average_st"])
        self.assertEqual(parsed["local_rates"], [0.0] + [4.5] * 5)
        self.assertEqual(parsed["local_zero_boats"], [1])
        self.assertIs(parsed["local_zero_research_fallback_used"], True)
        for flag in ("method_preregistered", "model_consumed",
                     "forecast_usable", "formal", "official_HTTP_origin_attested",
                     "official_T_minus_12_source_certified"):
            self.assertIs(parsed[flag], False, flag)

    def test_nonzero_html_is_identical_to_immutable_frozen_parser(self):
        raw = synthetic_racelist()
        original = extract_six_official_racelist_rates(raw)
        result = extract_six_with_local_zero_research(raw)
        for key, value in original.items():
            self.assertEqual(result[key], value)
        self.assertIs(result["local_zero_research_fallback_used"], False)
        self.assertEqual(result["local_zero_boats"], [])

    def test_wrong_national_zero_or_over_limit_local_never_substituted(self):
        raw = synthetic_racelist()
        for bad in (
            raw.replace(LOCAL, b"10.01<br>36.00<br>45.00", 1),
            raw.replace(b"5.30<br>", b"0.00<br>", 1),
            raw.replace(b"5.30<br>", b"99.99<br>", 1),
            raw.replace(LOCAL, b"0.00<br>0.00<br>0.00", 1
                       ).replace(b"5.30<br>", b"0.00<br>", 1),
            raw.replace(LOCAL, b"0.00<br>0.00<br>0.00", 1
                       ).replace(b"0.16</td>", b"1.00</td>", 1),
        ):
            with self.subTest(bad=bad[:70]), self.assertRaises(ValueError):
                extract_six_with_local_zero_research(bad)

    def test_original_source_identity_and_columns_stay_fail_closed(self):
        raw=synthetic_racelist().replace(LOCAL,b"0.00<br>0.00<br>0.00",1)
        for bad in (
            raw.replace(b"toban=4510",b"toban=0000",1),
            raw.replace("全国".encode(),"全国不明".encode(),1),
            raw.replace(b'class="is-lineH2" rowspan="4">0.00',
                        b'class="bad" rowspan="4">0.00',1),
            raw.replace(b'<tr><td class="is-boatColor6',
                        b'<notrow><td class="is-boatColor6',1),
            b"",
        ):
            with self.subTest(bad=bad[:80]),self.assertRaises(ValueError):
                extract_six_with_local_zero_research(bad)


if __name__ == "__main__":
    unittest.main()
