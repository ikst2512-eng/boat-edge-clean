"""Synthetic HTML contract for direct six-boat official racelist parsing.

All fixtures in this module are FAKE. Actual archived official XHTML is
rechecked only in the read-only #1710 GitHub evidence workflow.
"""
import hashlib
import re
import unittest

from scenario_official_racelist_rates import extract_six_official_racelist_rates

RATES = [5.3, 5.9, 6.1, 4.6, 6.0, 5.1]
IDS = [str(i) for i in range(4510,4516)]


def synthetic_racelist(ids=None, rates=None):
    ids = IDS if ids is None else ids
    rates = RATES if rates is None else rates
    html = '<html><body><table><tr><th>全国</th><th>当地</th><th>モーター</th><th>ボート</th></tr>'
    for i,(reg,rate) in enumerate(zip(ids,rates),1):
        full = '１２３４５６'[i-1]
        html += (
            f'<tr><td class="is-boatColor{i} is-fs14" rowspan="4">{full}</td>'
            f'<td rowspan="4"><a href="/owpc/pc/data/racersearch/profile?toban={reg}">photo</a></td>'
            f'<td rowspan="4"><a href="/owpc/pc/data/racersearch/profile?toban={reg}">racer</a></td>'
            '<td class="is-lineH2" rowspan="4">F0<br>L0<br>0.16</td>'
            f'<td class="is-lineH2" rowspan="4">{rate:.2f}<br>45.00<br>60.00</td>'
            '<td class="is-lineH2" rowspan="4">4.50<br>36.00<br>45.00</td>'
            '<td class="is-lineH2" rowspan="4">32<br>40.00<br>50.00</td>'
            '<td class="is-lineH2" rowspan="4">12<br>35.00<br>55.00</td>'
            '</tr>'
        )
    return (html+'</table></body></html>').encode()


class OfficialSixWinRatesTests(unittest.TestCase):
    def test_each_synthetic_boat_maps_national_local_and_st(self):
        data=extract_six_official_racelist_rates(synthetic_racelist())
        self.assertEqual(data['national_rates'],RATES)
        self.assertEqual(data['local_rates'],[4.5]*6)
        self.assertEqual(data['average_st'],[0.16]*6)
        self.assertEqual(data["motor_numbers"],[32]*6)
        self.assertEqual(data["motor_2ren_pct"],[40.0]*6)
        self.assertEqual([r["motor_3ren_pct"] for r in data["boats"]],[50.0]*6)
        self.assertEqual(data["racelist_original_bytes_sha256"],
                         hashlib.sha256(synthetic_racelist()).hexdigest())
        self.assertFalse(data["motor_2ren_sample_size_verified"])
        self.assertTrue(all(r["motor_starts"] is None and r["motor_2ren_count"] is None
                            for r in data["boats"]))
        self.assertEqual([x["registration_id"] for x in data["boats"]],IDS)
        self.assertEqual(len(data["boats"]),6)
        self.assertFalse(data['formal'])
        self.assertFalse(data['official_HTTP_origin_attested'])
        self.assertFalse(data['forecast_usable'])

    def test_motor_display_without_denominator_cannot_enter_matrix(self):
        from scenario_attack_benefit_feature_matrix import build_attack_benefit_matrix
        from test_scenario_attack_benefit_feature_matrix import fixture
        parsed=extract_six_official_racelist_rates(synthetic_racelist())
        x=fixture()
        x["racers"][0]["signals"]["motor_2ren_pct"]={
            "value":parsed["boats"][0]["motor_2ren_pct"],
            "source_sha256":parsed["racelist_original_bytes_sha256"],
            "received_at_jst":"2026-11-15T09:45:00+09:00",
            "source_url":"https://www.boatrace.jp/",
            "denominator_kind":"motor_starts",
        }
        with self.assertRaisesRegex(ValueError,"numeric_feature_value_and_denominator"):
            build_attack_benefit_matrix(x)

    def test_invalid_or_shifted_motor_column_is_rejected(self):
        raw=synthetic_racelist()
        for variant in ("0<br>40.00<br>50.00",
                        "32<br>140.00<br>50.00",
                        "32<br>??<br>50.00",
                        "32<br>40.00<br>50.00<br>garbage"):
            changed=raw.replace(b'32<br>40.00<br>50.00',variant.encode(),1)
            with self.subTest(value=variant),self.assertRaises(ValueError):
                extract_six_official_racelist_rates(changed)
        changed=raw.replace(b'<td class="is-lineH2" rowspan="4">32',
                            b'<td class="wrong" rowspan="4">32',1)
        with self.assertRaises(ValueError):
            extract_six_official_racelist_rates(changed)

    def test_header_cannot_be_missing_or_local_before_national(self):
        raw=synthetic_racelist()
        for x in (raw.replace(b'</th><th>',b'</th><th>',1).replace(
                        '全国'.encode(),'全國'.encode()),
                  raw.replace('全国'.encode(),'当地'.encode(),1),
                  raw.replace(b'</table>', b'<tr><th>\xe5\x85\xa8\xe5\x9b\xbd</th><th>\xe5\xbd\x93\xe5\x9c\xb0</th><th>\xe3\x83\xa2\xe3\x83\xbc\xe3\x82\xbf\xe3\x83\xbc</th><th>\xe3\x83\x9c\xe3\x83\xbc\xe3\x83\x88</th></tr></table>')):
            with self.subTest(example=x[:40]), self.assertRaisesRegex(ValueError,"column_headers"):
                extract_six_official_racelist_rates(x)

    def test_numeric_rate_must_not_be_guessed(self):
        raw=synthetic_racelist()
        for value in (b'-.--',b'99.99',b'0.00'):
            altered=raw.replace(b'5.30<br>',value+b'<br>',1)
            with self.subTest(value=value),self.assertRaises(ValueError):
                extract_six_official_racelist_rates(altered)

    def test_duplicate_registration_or_less_than_six_refused(self):
        ids=IDS[:]
        ids[5]=ids[0]
        with self.assertRaises(ValueError):
            extract_six_official_racelist_rates(synthetic_racelist(ids=ids))
        raw=synthetic_racelist()
        last=raw.find(b'<tr><td class="is-boatColor6')
        with self.assertRaises(ValueError):
            extract_six_official_racelist_rates(raw[:last]+b'</table></body></html>')

    def test_row_column_shift_and_registration_mutation_rejected(self):
        raw=synthetic_racelist()
        with self.assertRaisesRegex(ValueError,"columns_drifted"):
            extract_six_official_racelist_rates(
                raw.replace(b'class="is-lineH2" rowspan="4">5.30',
                            b'class="wrong" rowspan="4">5.30'))
        with self.assertRaises(ValueError):
            extract_six_official_racelist_rates(
                raw.replace(b'toban=4510',b'toban=0000',1))

    def test_bounds_and_bytes_only(self):
        for bad in (b'', b'not html', 'not bytes',None):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                extract_six_official_racelist_rates(bad)
        with self.assertRaises(ValueError):
            extract_six_official_racelist_rates(
                synthetic_racelist().replace(b'0.16</td>',b'1.00</td>'))


if __name__=="__main__":
    unittest.main()
