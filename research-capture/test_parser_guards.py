import unittest
from exhibition_parser import extract

RACE = "202610260512"
def fixture(rows, heading="展示タイム", extra=""):
    table = "<table><tr><th>"+heading+"</th></tr>"
    table += "".join("<tr><td>"+str(i)+"</td><td>"+str(v)+"</td></tr>" for i,v in rows)
    return (table+"</table>"+extra).encode("utf-8")

class ExhibitionSafety(unittest.TestCase):
    def parse(self, raw, **kw):
        return extract(raw, race_id=RACE, received_before_cutoff=True, result_free_attested=True, **kw)

    def test_six_unique_boats(self):
        result=self.parse(fixture([(i,f"6.{70+i:02d}") for i in range(1,7)]))
        self.assertEqual(set(result["exhibition_time_by_boat"]), set(range(1,7)))

    def test_missing_boat_rejected(self):
        with self.assertRaises(ValueError):
            self.parse(fixture([(i,"6.80") for i in range(1,6)]))

    def test_duplicate_boat_rejected(self):
        with self.assertRaises(ValueError):
            self.parse(fixture([(1,"6.81"),(1,"6.82"),(2,"6.83"),(3,"6.84"),(4,"6.85"),(5,"6.86")]))

    def test_unlabeled_numbers_rejected(self):
        with self.assertRaises(ValueError):
            self.parse(fixture([(i,"6.80") for i in range(1,7)],heading="水温"))

    def test_result_token_rejected(self):
        with self.assertRaises(ValueError):
            self.parse(fixture([(i,"6.80") for i in range(1,7)],extra="払戻金"))

    def test_time_attestation_required(self):
        with self.assertRaises(ValueError):
            extract(fixture([(i,"6.80") for i in range(1,7)]),race_id=RACE,received_before_cutoff=False,result_free_attested=True)

    def test_result_isolation_required(self):
        with self.assertRaises(ValueError):
            extract(fixture([(i,"6.80") for i in range(1,7)]),race_id=RACE,received_before_cutoff=True,result_free_attested=False)

if __name__=="__main__": unittest.main()
