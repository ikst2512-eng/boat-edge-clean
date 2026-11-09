"""Real parsers on explicitly synthetic official-shaped bytes, never live evidence."""
import base64
import copy
import hashlib
import json
import unittest

from four_mode_official_future_lineage_preflight import _canonical, preflight
from four_mode_official_raw_semantic_replay import replay
from test_four_mode_official_future_lineage_preflight import fixture

IDS = ["4180","5112","4786","4159","4663","5087"]
FULL = "１２３４５６"


def odds_table(odds_value="12.3"):
    rows=[]
    for i in range(20):
        cells=[]
        for first in range(1,7):
            remaining=[j for j in range(1,7) if j != first]
            second=remaining[i//4]
            third=[j for j in remaining if j != second][i%4]
            if i%4==0:
                cells.extend([str(second),str(third),odds_value])
            else:
                cells.extend([str(third),odds_value])
        rows.append("<tr>"+"".join("<td>"+v+"</td>" for v in cells)+"</tr>")
    return ("<html><body><table>"+"".join(rows)+"</table></body></html>").encode()


def official_shaped_fixture():
    source,candidate=fixture()
    code=source["race_code"]
    src=source["originals"]
    rows="".join(
        '<tr><td class="is-boatColor%d is-fs14" rowspan="4">%s</td>'
        '<td><a href="/owpc/pc/data/racersearch/profile?toban=%s">Racer</a></td></tr>' %
        (i,FULL[i-1],IDS[i-1]) for i in range(1,7))
    card=('<?xml version="1.0"?><html><body>'+rows+'</body></html>').encode()
    before={"maindata":{
        "hd":code[:8], "jcd":code[8:10], "rno":str(int(code[10:])),
        "deadline":"14:40",
        "teiinfolist":[
            {"teino":str(i), "racerno":IDS[i-1],
             "extime":str(source["normalized_source_claim"]["exhibition_times"][i-1]),
             "tilt":str(source["normalized_source_claim"]["exhibition_tilts"][i-1])}
            for i in range(1,7)],
        "sttenjiinfolist":[
            {"teino":str(i), "cs":str(i),
             "st":"%.2f"%source["normalized_source_claim"]["exhibition_st"][i-1]}
            for i in range(1,7)],
    }}
    raw_before=json.dumps(before).encode()
    raw_odds=odds_table()
    src["racelist"]["source_url"] = (
        "https://www.boatrace.jp/owpc/pc/race/racelist?hd=20261110&jcd=01&rno=1")
    src["beforeinfo"]["source_url"] = (
        "https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&hd=20261110&jcd=01&rno=1")
    src["odds120"]["source_url"] = (
        "https://www.boatrace.jp/owpc/pc/race/odds3t?hd=20261110&jcd=01&rno=1")
    for kind,raw in (("racelist",card),("beforeinfo",raw_before),("odds120",raw_odds)):
        replace_original(source,candidate,kind,raw)
    n=source["normalized_source_claim"]
    n["racelist_registration_ids"]=list(IDS)
    n["beforeinfo_registration_ids"]=list(IDS)
    n["odds_3t"]={k:12.3 for k in n["odds_3t"]}
    candidate["consumed_normalized_claim_sha256"]=hashlib.sha256(_canonical(n)).hexdigest()
    return source,candidate


def replace_original(source,candidate,kind,raw):
    record=source["originals"][kind]
    digest=hashlib.sha256(raw).hexdigest()
    record["raw_base64"]=base64.b64encode(raw).decode("ascii")
    record["sha256"]=digest
    source["normalized_source_claim"]["source_sha256"][kind]=digest
    candidate["consumed_source_sha256"][kind]=digest
    candidate["consumed_normalized_claim_sha256"]=hashlib.sha256(
        _canonical(source["normalized_source_claim"])).hexdigest()


class RawOfficialSemanticReplayTests(unittest.TestCase):
    def test_synthetic_html_and_beforeinfo_are_really_reparsed(self):
        source,candidate=official_shaped_fixture()
        result=replay(source,candidate)
        self.assertEqual(len(result["verified_stages"]),5)
        self.assertTrue(result["preflight_still_nonformal"])
        self.assertFalse(result["raw_official_provenance_independently_attested"])
        self.assertFalse(result["actual_model_output_independently_replayed"])
        self.assertFalse(result["formal"])
        self.assertFalse(result["prospective_candidate_admitted"])

    def test_old_dummy_raw_bytes_are_rejected_by_real_parsers(self):
        source,candidate=fixture()
        # All declared SHA and source clocks are internally consistent.
        self.assertFalse(preflight(source,candidate)["formal"])
        with self.assertRaises(ValueError):
            replay(source,candidate)

    def test_racecard_forged_claim_fails_even_with_all_digest_claims_updated(self):
        source,candidate=official_shaped_fixture()
        card=base64.b64decode(source["originals"]["racelist"]["raw_base64"])
        change=card.replace(b"toban=4180",b"toban=9999")
        replace_original(source,candidate,"racelist",change)
        self.assertFalse(preflight(source,candidate)["formal"])
        with self.assertRaisesRegex(ValueError,"racelist_registration_ids"):
            replay(source,candidate)

    def test_beforeinfo_forged_exhibition_fails_with_consistent_hashes(self):
        source,candidate=official_shaped_fixture()
        raw=base64.b64decode(source["originals"]["beforeinfo"]["raw_base64"])
        data=json.loads(raw)
        data["maindata"]["teiinfolist"][0]["extime"]="7.77"
        replace_original(source,candidate,"beforeinfo",json.dumps(data).encode())
        self.assertFalse(preflight(source,candidate)["formal"])
        with self.assertRaisesRegex(ValueError,"normalized_exhibition_times"):
            replay(source,candidate)

    def test_odds_forged_claim_fails_with_consistent_hashes(self):
        source,candidate=official_shaped_fixture()
        raw=base64.b64decode(source["originals"]["odds120"]["raw_base64"])
        replace_original(source,candidate,"odds120",raw.replace(b"12.3",b"13.4",1))
        self.assertFalse(preflight(source,candidate)["formal"])
        with self.assertRaisesRegex(ValueError,"odds_claim"):
            replay(source,candidate)

    def test_wrong_race_official_host_endpoint_is_rejected(self):
        source,candidate=official_shaped_fixture()
        source["originals"]["beforeinfo"]["source_url"] = (
            "https://www.boatrace.jp/owsp/sp/spdata?type=beforeinfo&hd=20261110&jcd=01&rno=2")
        self.assertFalse(preflight(source,candidate)["formal"])
        with self.assertRaisesRegex(ValueError,"exact_official_race_source_url"):
            replay(source,candidate)

    def test_not_ready_six_exhibition_rejected_by_real_parser(self):
        source,candidate=official_shaped_fixture()
        raw=base64.b64decode(source["originals"]["beforeinfo"]["raw_base64"])
        data=json.loads(raw)
        data["maindata"]["teiinfolist"][0]["tilt"]=""
        replace_original(source,candidate,"beforeinfo",json.dumps(data).encode())
        with self.assertRaisesRegex(ValueError,"raw_exhibition_incomplete"):
            replay(source,candidate)

    def test_flagged_st_explicitly_requires_separate_semantics(self):
        source,candidate=official_shaped_fixture()
        raw=base64.b64decode(source["originals"]["beforeinfo"]["raw_base64"])
        data=json.loads(raw)
        data["maindata"]["sttenjiinfolist"][0]["st"]="F.01"
        replace_original(source,candidate,"beforeinfo",json.dumps(data).encode())
        with self.assertRaisesRegex(ValueError,"flagged_or_ambiguous"):
            replay(source,candidate)

    def test_unrecognized_normalized_fields_and_result_leak_rejected(self):
        source,candidate=official_shaped_fixture()
        source["normalized_source_claim"]["precomputed_predictor"]="secret"
        candidate["consumed_normalized_claim_sha256"]=hashlib.sha256(
            _canonical(source["normalized_source_claim"])).hexdigest()
        with self.assertRaisesRegex(ValueError,"unrecognized_normalized"):
            replay(source,candidate)
        source,candidate=official_shaped_fixture()
        source["normalized_source_claim"]["winning_ticket"]="1-2-3"
        with self.assertRaisesRegex(ValueError,"outcome_leak"):
            replay(source,candidate)

    def test_swapped_exhibition_course_detected_without_consulting_results(self):
        source,candidate=official_shaped_fixture()
        raw=base64.b64decode(source["originals"]["beforeinfo"]["raw_base64"])
        data=json.loads(raw)
        data["maindata"]["sttenjiinfolist"][0]["cs"]="2"
        data["maindata"]["sttenjiinfolist"][1]["cs"]="1"
        replace_original(source,candidate,"beforeinfo",json.dumps(data).encode())
        self.assertFalse(preflight(source,candidate)["formal"])
        with self.assertRaisesRegex(ValueError,"normalized_exhibition_courses"):
            replay(source,candidate)

    def test_candidate_clock_and_source_integrity_still_fail_closed(self):
        source,candidate=official_shaped_fixture()
        candidate["generated_at_jst"]="2026-11-10T14:28:00+09:00"
        with self.assertRaisesRegex(ValueError,"source_to_candidate_time_order"):
            replay(source,candidate)
        source,candidate=official_shaped_fixture()
        source["originals"]["odds120"]["raw_base64"]="cHJvYmU="
        with self.assertRaisesRegex(ValueError,"original_byte_hash"):
            replay(source,candidate)


if __name__=="__main__":
    unittest.main()
