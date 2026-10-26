import unittest
from clean_official_racelist_candidates import extract_six_candidates

URL = "https://www.boatrace.jp/owpc/pc/race/racelist?hd=20261026&jcd=21&rno=1"
KEY = "20261026-21-01"


def sample():
    rows = "".join(
        f'<tr><td class="is-boatColor{i}">{i}</td><td><a href="/owpc/pc/data/racersearch/profile?toban={4000+i}">選手{i}</a></td></tr>'
        for i in range(1, 7)
    )
    return ('<html><body><a href="/?toban=9000">関連選手</a><table>' + rows + '</table></body></html>').encode()


class RacelistCandidateTests(unittest.TestCase):
    def test_six_scoped_candidates_not_official_verification(self):
        result = extract_six_candidates(sample(), URL, KEY)
        self.assertEqual(len(result["racers"]), 6)
        self.assertEqual([x["lane"] for x in result["racers"]], list(range(1, 7)))
        self.assertFalse(result["official_provenance_verified"])
        self.assertEqual(result["status"], "html_candidates_unverified")

    def test_wrong_race_is_blocked(self):
        with self.assertRaises(ValueError):
            extract_six_candidates(sample(), URL, "20261026-22-01")

    def test_missing_lane_is_blocked(self):
        with self.assertRaises(ValueError):
            extract_six_candidates(sample().replace(b"is-boatColor6", b"no-lane"), URL, KEY)

    def test_duplicate_registration_is_blocked(self):
        with self.assertRaises(ValueError):
            extract_six_candidates(sample().replace(b"toban=4006", b"toban=4005"), URL, KEY)

    def test_nonofficial_domain_is_blocked(self):
        with self.assertRaises(ValueError):
            extract_six_candidates(sample(), URL.replace("www.boatrace.jp", "boatrace.jp.evil.test"), KEY)

    def test_ambiguous_row_is_blocked(self):
        with self.assertRaises(ValueError):
            extract_six_candidates(sample().replace(b"is-boatColor1", b"is-boatColor1 is-boatColor2"), URL, KEY)


if __name__ == "__main__":
    unittest.main()
