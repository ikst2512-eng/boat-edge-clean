"""Fail-closed fixture tests for CLEAN's *actual* independent CSV/TSV parsers."""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
import clean_racecard
from clean_direct_sources import parse_card
from research_model import JST

def tsv(registrations=None, truncate=False):
    registrations=registrations or [str(4101+i) for i in range(6)]
    rows=[]
    for reg in registrations:
        c=[""]*25
        c[0]=reg;c[1]="選手";c[5]="A1";c[9]="0.15";c[10]="5.50"
        c[11]="40";c[12]="60";c[13]="5.0";c[14]="35";c[15]="50"
        c[17]="12";c[18]="30";c[19]="45";c[21]="15";c[22]="28";c[23]="42"
        rows.append("\t".join(c))
    if truncate:rows=rows[:5]
    return ("data=\n1\t6\n"+"\n".join(rows)).encode()

class CleanSixBoatFixtures(unittest.TestCase):
    def test_independent_tsv_six_unique(self):
        result=parse_card(tsv(),"202610290101")
        self.assertEqual(len({result[f"艇{i}_登録番号"] for i in range(1,7)}),6)

    def test_independent_tsv_five_of_six_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_card(tsv(truncate=True),"202610290101")

    def test_independent_tsv_duplicate_registration_fails_closed(self):
        regs=["4101","4102","4103","4104","4105","4105"]
        with self.assertRaisesRegex(ValueError,"duplicate_or_missing_registration"):
            parse_card(tsv(regs),"202610290101")

    def test_independent_tsv_missing_cell_fails_closed(self):
        lines=tsv().decode().splitlines()
        lines[2]="\t".join(lines[2].split("\t")[:10])
        with self.assertRaisesRegex(ValueError,"incomplete_race_card"):
            parse_card("\n".join(lines).encode(),"202610290101")

    def test_clean_racecard_duplicate_registration_fails_closed(self):
        hd=(datetime.now(JST)+timedelta(days=1)).strftime("%Y%m%d")
        key=hd+"0101"
        fields={"レースコード":key}
        for i in range(1,7):
            fields[f"艇{i}_登録番号"]=str(4200+i if i<6 else 4205)
        title=[{"レースコード":key,"電話投票締切予定":"23:59"}]
        def read(url):
            return (title if "/title/" in url else [fields],datetime.now(JST),"a"*64)
        with patch.object(clean_racecard,"read_rows",side_effect=read):
            with self.assertRaisesRegex(ValueError,"duplicate_registration"):
                clean_racecard.racecard(hd,"1","1")

if __name__=="__main__":
    unittest.main()
