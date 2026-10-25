"""Offline defensive tests: a valid synthetic card is accepted; unsafe cards are rejected."""
import unittest
from exhibition_parser import extract

RID="202610260512"
def page(rows, heading="展示タイム", extra=""):
    return ('<html><table><tr><th>'+heading+'</th></tr>'+''.join(
        '<tr><td>'+str(i)+'</td><td>'+v+'</td></tr>' for i,v in rows
    )+'</table>'+extra+'</html>').encode("utf-8")

VALID=[(i, f"{6.70+i/100:.2f}") for i in range(1,7)]
def parse(payload, **kw):
    return extract(payload,race_id=RID,received_before_cutoff=kw.get("time",True),result_free_attested=kw.get("clean",True))

class TestFailClosed(unittest.TestCase):
    def test_synthetic_six_boats(self):
        self.assertEqual(len(parse(page(VALID))["exhibition_time_by_boat"]),6)
    def test_malformed_missing_boat(self):
        with self.assertRaises(ValueError):parse(page(VALID[:-1]))
    def test_duplicate_boat(self):
        with self.assertRaises(ValueError):parse(page(VALID[:-1]+VALID[:1]))
    def test_missing_heading(self):
        with self.assertRaises(ValueError):parse(page(VALID,"Other"))
    def test_result_token(self):
        with self.assertRaises(ValueError):parse(page(VALID,extra="払戻金"))
    def test_time_gate(self):
        with self.assertRaises(ValueError):parse(page(VALID),time=False)
    def test_result_isolation_gate(self):
        with self.assertRaises(ValueError):parse(page(VALID),clean=False)
    def test_two_candidate_tables(self):
        with self.assertRaises(ValueError):parse(page(VALID)+page(VALID))
    def test_invalid_race_id(self):
        with self.assertRaises(AssertionError):
            extract(page(VALID),race_id="bogus",received_before_cutoff=True,result_free_attested=True)

if __name__=="__main__":unittest.main()
