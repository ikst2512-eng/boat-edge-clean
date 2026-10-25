import unittest
from exhibition_parser import extract

RID="202610250512"
def page(rows,head="展示タイム"):
    return ("<table><tr><th>"+head+"</th></tr>"+
            "".join(f"<tr><td>{i}</td><td>{v}</td></tr>" for i,v in rows)+
            "</table>").encode("utf-8")
def valid():
    return page([(i,f"{6.70+i/100:.2f}") for i in range(1,7)])
def run(b,**kw):
    return extract(b,race_id=RID,received_before_cutoff=kw.get("time",True),result_free_attested=kw.get("clean",True))
class ParserSafetyTests(unittest.TestCase):
    def test_valid_six(self):
        got=run(valid());self.assertEqual(set(got["exhibition_time_by_boat"]),set(range(1,7)))
    def test_result_mixed(self):
        with self.assertRaises(ValueError):run(valid()+"払戻金".encode())
    def test_no_time_proof(self):
        with self.assertRaises(ValueError):run(valid(),time=False)
    def test_no_result_proof(self):
        with self.assertRaises(ValueError):run(valid(),clean=False)
    def test_missing_lane(self):
        with self.assertRaises(ValueError):run(page([(i,"6.70") for i in range(1,6)]))
    def test_duplicate_lane(self):
        with self.assertRaises(ValueError):run(page([(i,"6.70") for i in (1,2,3,4,5,5)]))
    def test_ambiguous_tables(self):
        with self.assertRaises(ValueError):run(valid()+valid())
    def test_wrong_head(self):
        with self.assertRaises(ValueError):run(page([(i,"6.70") for i in range(1,7)],head="払戻情報"))
    def test_bad_id(self):
        with self.assertRaises(AssertionError):extract(valid(),race_id="202610250599",received_before_cutoff=True,result_free_attested=True)
if __name__=="__main__":unittest.main()
