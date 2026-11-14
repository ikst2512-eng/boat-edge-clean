"""Synthetic HTML contract for direct six-boat official racelist parsing.

All fixtures in this module are FAKE. Actual archived official XHTML is
rechecked only in the read-only #1710 GitHub evidence workflow.
"""
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
        self.assertEqual([x["registration_id"] for x in data["boats"]],IDS)
        self.assertEqual(len(data["boats"]),6)
        self.assertFalse(data['formal'])
        self.assertFalse(data['official_HTTP_origin_attested'])
        self.assertFalse(data['forecast_usable'])

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

    def test_genuine_local_zero_rate_is_not_missing_or_imputed(self):
        # Three independently archived 2026-11-14 real pre-T12 racecards
        # contained a local rate 0.00 with valid nonzero national rates.
        original=synthetic_racelist()
        zero_local=original.replace(
            b'4.50<br>36.00<br>45.00',
            b'0.00<br>0.00<br>0.00',1)
        parsed=extract_six_official_racelist_rates(zero_local)
        self.assertEqual(parsed["local_rates"][0],0.0)
        self.assertEqual(parsed["national_rates"][0],5.3)
        self.assertEqual(parsed["boats"][0]["local_2ren_pct"],0.0)
        self.assertEqual(parsed["boats"][0]["local_3ren_pct"],0.0)
        self.assertEqual(parsed["boats"][1]["local_win_rate"],4.5)
        self.assertIs(parsed["rates_extracted_from_original_html_not_csv"],True)
        self.assertIs(parsed["forecast_usable"],False)
        self.assertIs(parsed["formal"],False)
        # Still reject malformed/over-limit local rate and missing nationwide
        # model rate. No fallback to a venue mean or another racer is allowed.
        invalid_local=original.replace(
            b'4.50<br>36.00<br>45.00',
            b'10.01<br>36.00<br>45.00',1)
        with self.assertRaisesRegex(ValueError,"out_of_bounds"):
            extract_six_official_racelist_rates(invalid_local)
        invalid_national=original.replace(b'5.30<br>',b'0.00<br>',1)
        with self.assertRaisesRegex(ValueError,"out_of_bounds"):
            extract_six_official_racelist_rates(invalid_national)

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
