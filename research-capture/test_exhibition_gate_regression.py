"""Offline regression tests: no live race, no result records, no network."""
import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location("exhibition_parser", pathlib.Path(__file__).with_name("exhibition_parser.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

RID = "202610260512"
def html(rows, heading="展示タイム"):
    body = "<table><tr><th>"+heading+"</th></tr>"
    body += "".join(f"<tr><td>{lane}</td><td>{value}</td></tr>" for lane,value in rows)
    return (body+"</table>").encode("utf-8")
def parse(data, **kw):
    args=dict(race_id=RID, received_before_cutoff=True, result_free_attested=True)
    args.update(kw)
    return mod.extract(data, **args)

class FailClosedExhibitionTests(unittest.TestCase):
    def test_six_verified_lanes(self):
        data=html([(i,f"{6.70+i/100:.2f}") for i in range(1,7)])
        got=parse(data)
        self.assertEqual(set(got["exhibition_time_by_boat"]),set(range(1,7)))
    def test_missing_lane(self):
        with self.assertRaises(ValueError):parse(html([(i,"6.75") for i in range(1,6)]))
    def test_duplicate_lane(self):
        with self.assertRaises(ValueError):parse(html([(i,"6.75") for i in [1,2,3,4,5,5]]))
    def test_result_indicator(self):
        with self.assertRaises(ValueError):parse(html([(i,"6.75") for i in range(1,7)])+"払戻金".encode())
    def test_no_cutoff_proof(self):
        with self.assertRaises(ValueError):parse(html([(i,"6.75") for i in range(1,7)]),received_before_cutoff=False)
    def test_no_result_free_proof(self):
        with self.assertRaises(ValueError):parse(html([(i,"6.75") for i in range(1,7)]),result_free_attested=False)
    def test_wrong_header(self):
        with self.assertRaises(ValueError):parse(html([(i,"6.75") for i in range(1,7)],"前走タイム"))
    def test_two_ambiguous_tables(self):
        h=html([(i,"6.75") for i in range(1,7)])
        with self.assertRaises(ValueError):parse(h+h)
    def test_out_of_range_lane(self):
        with self.assertRaises(ValueError):parse(html([(i,"6.75") for i in range(2,8)]))

if __name__=="__main__":unittest.main()
