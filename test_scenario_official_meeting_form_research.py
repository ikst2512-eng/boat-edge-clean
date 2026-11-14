"""Synthetic four-row official-racelist meeting contract (no future race results)."""
import hashlib
import unittest

from scenario_official_meeting_form_research import extract_prior_day_meeting_form

RACE = "202611140712"
IDS = [str(v) for v in range(4983, 4989)]


def original_like_racelist():
    raw = ['<html><table><thead><tr><th>全国</th><th>当地</th>'
           '<th>モーター</th><th>ボート</th></tr></thead><tbody class=" is-fs12">']
    for boat, reg in enumerate(IDS, 1):
        label = "１２３４５６"[boat - 1]
        static = (
            f'<tr><td class="is-boatColor{boat} is-fs14" rowspan="4">{label}</td>'
            f'<td rowspan="4"><a href="/owpc/pc/data/racersearch/profile?toban={reg}">photo</a></td>'
            f'<td rowspan="4"><a href="/owpc/pc/data/racersearch/profile?toban={reg}">racer</a></td>'
            '<td class="is-lineH2" rowspan="4">F0<br>L0<br>0.16</td>'
            '<td class="is-lineH2" rowspan="4">5.30<br>45.00<br>60.00</td>'
            '<td class="is-lineH2" rowspan="4">4.50<br>36.00<br>45.00</td>'
            '<td class=" is-lineH2" rowspan="4">32<br>40.00<br>50.00</td>'
            '<td class="is-lineH2" rowspan="4">12<br>35.00<br>55.00</td>'
            '<td rowspan="4">&nbsp;</td>'
        )
        n = [
            '<td class="is-boatColor5">3</td>',
            '<td class="is-boatColor2">12</td>',
        ] + ['<td class=" ">&nbsp;</td>'] * 12
        static += "".join(n) + '<td rowspan="4"><a href="/owpc/pc/race/racelist"></a></td></tr>'
        courses = '<tr>' + '<td>5</td><td>2</td>' + '<td>&nbsp;</td>' * 12 + '</tr>'
        st = '<tr>' + '<td>.11</td><td>.19</td>' + '<td>&nbsp;</td>' * 12 + '</tr>'
        finish = ('<tr class="is-fBold">'
                  '<td><a href="/owpc/pc/race/raceresult?rno=3&amp;jcd=07&amp;hd=20261113">１</a></td>'
                  '<td><a href="/owpc/pc/race/raceresult?rno=12&amp;jcd=07&amp;hd=20261113">３</a></td>'
                  + '<td><a href="/owpc/pc/race/raceresult"></a></td>' * 12 + '</tr>')
        raw.extend((static, courses, st, finish))
    return ("".join(raw) + "</tbody></table></html>").encode("utf-8")


class PriorDayMeetingTests(unittest.TestCase):
    def test_official_style_four_rows_map_six_racers_and_real_counts(self):
        raw = original_like_racelist()
        result = extract_prior_day_meeting_form(raw, RACE, IDS)
        self.assertEqual(result["racelist_original_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(result["rows"]), 6)
        for boat, entry in enumerate(result["rows"], 1):
            self.assertEqual((entry["boat"],entry["registration_id"]), (boat,IDS[boat - 1]))
            self.assertEqual(entry["prior_day_completed_starts"], 2)
            self.assertEqual(entry["prior_day_top2_count"], 1)
            self.assertEqual(entry["prior_day_2ren_pct"], 50)
            self.assertEqual(entry["prior_day_top3_count"], 2)
            self.assertEqual(entry["prior_day_average_st_s"], .15)
            self.assertEqual([v["actual_course_historical_only"] for v in entry["prior_day_results"]], [5, 2])
            self.assertEqual([v["drawn_boat"] for v in entry["prior_day_results"]], [5, 2])
            self.assertTrue(all(v["race_code"] < RACE for v in entry["prior_day_results"]))
        self.assertFalse(result["source_receipt_independently_attested"])
        self.assertFalse(result["same_race_T12_model_consumption_verified"])
        self.assertFalse(result["comments_source_verified"])
        self.assertFalse(result["formal"])

    def test_wrong_registrations_or_six_row_breakage_rejected(self):
        raw = original_like_racelist()
        with self.assertRaisesRegex(ValueError, "registration_identity"):
            extract_prior_day_meeting_form(raw, RACE, IDS[::-1])
        with self.assertRaises(ValueError):
            extract_prior_day_meeting_form(raw[:-35], RACE, IDS)

    def test_future_race_result_link_and_cross_venue_rejected(self):
        raw = original_like_racelist()
        for future in (b"20261115", b"20261114"):
            # Same-day 3R is prior to target 12R and is intentionally
            # excluded, not a target leakage. Change 12R for the boundary.
            anchor=(b"rno=12&amp;jcd=07&amp;hd=20261113" if future==b"20261114"
                    else b"rno=3&amp;jcd=07&amp;hd=20261113")
            replaced=raw.replace(anchor,anchor.replace(b"20261113",future),1)
            with self.subTest(future=future), self.assertRaisesRegex(ValueError,"future|target"):
                extract_prior_day_meeting_form(replaced,RACE,IDS)
        wrong=raw.replace(b"jcd=07",b"jcd=03",1)
        with self.assertRaisesRegex(ValueError,"cross_venue"):
            extract_prior_day_meeting_form(wrong,RACE,IDS)

    def test_course_is_historical_not_affected_by_drawn_boat(self):
        raw=original_like_racelist()
        changed=raw.replace(b'<td>5</td><td>2</td>',
                            b'<td>3</td><td>2</td>',1)
        initial=extract_prior_day_meeting_form(raw,RACE,IDS)
        altered=extract_prior_day_meeting_form(changed,RACE,IDS)
        self.assertEqual(initial["rows"][0]["prior_day_completed_starts"], 2)
        self.assertEqual(altered["rows"][0]["prior_day_results"][0]["actual_course_historical_only"], 3)
        self.assertEqual(altered["rows"][0]["prior_day_results"][0]["drawn_boat"], 5)

    def test_nonfinish_or_ambiguous_history_is_not_counted(self):
        raw=original_like_racelist()
        changed=raw.replace('>３</a>'.encode(),'>転</a>'.encode(),1)
        result=extract_prior_day_meeting_form(changed,RACE,IDS)
        self.assertEqual(result["rows"][0]["prior_day_completed_starts"],1)
        self.assertEqual(result["rows"][0]["excluded_slots"]["non_numeric_finish_or_start"],1)
        self.assertEqual(result["rows"][0]["prior_day_2ren_pct"],100)
        # The omitted row does not become a zero, nor an inferred third place.
        self.assertEqual(result["rows"][0]["prior_day_top3_count"],1)

    def test_link_race_number_mismatch_and_duplicate_refused(self):
        raw=original_like_racelist()
        changed=raw.replace(b"rno=12&amp;jcd=07",b"rno=9&amp;jcd=07",1)
        with self.assertRaisesRegex(ValueError,"race_number"):
            extract_prior_day_meeting_form(changed,RACE,IDS)
        duplicated=raw.replace(b"rno=12&amp;jcd=07",b"rno=3&amp;jcd=07",1)
        with self.assertRaisesRegex(ValueError,"duplicate_meeting"):
            extract_prior_day_meeting_form(duplicated,RACE,IDS)

    def test_same_day_prior_race_is_conservatively_excluded(self):
        raw=original_like_racelist()
        changed=raw.replace(b"hd=20261113",b"hd=20261114",1)
        result=extract_prior_day_meeting_form(changed,RACE,IDS)
        self.assertEqual(result["rows"][0]["prior_day_completed_starts"], 1)
        self.assertEqual(result["rows"][0]["excluded_slots"]["same_day_not_independently_time_verified"], 1)


if __name__=="__main__":
    unittest.main()
