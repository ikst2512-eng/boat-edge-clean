import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from exhibition_parser import extract

class ParserBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.rid="202610250512"
        self.table='<table><tr><th>展示タイム</th></tr>'+''.join(f'<tr><td>{i}</td><td>{6.70+i/100:.2f}</td></tr>' for i in range(1,7))+'</table>'
    def parse(self,s,**kw):
        p=dict(race_id=self.rid,received_before_cutoff=True,result_free_attested=True)
        p.update(kw)
        return extract(s.encode(),**p)
    def test_valid_six(self):
        self.assertEqual(len(self.parse(self.table)['exhibition_time_by_boat']),6)
    def test_result_token_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.table+'払戻金')
    def test_missing_receipt_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.table,received_before_cutoff=False)
    def test_missing_attestation_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.table,result_free_attested=False)
    def test_duplicate_table_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.table+self.table)
    def test_unlabeled_table_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.table.replace('展示タイム','出走表'))
    def test_duplicate_boat_rejected(self):
        with self.assertRaises(ValueError):self.parse(self.table.replace('<td>6</td>','<td>5</td>'))
    def test_invalid_race_id_rejected(self):
        with self.assertRaises(AssertionError):self.parse(self.table,race_id='202610259912')
if __name__=='__main__':unittest.main()
