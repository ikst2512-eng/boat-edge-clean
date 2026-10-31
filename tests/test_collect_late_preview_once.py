import csv, io, tempfile, unittest
from datetime import datetime
from pathlib import Path
from research_model import JST
from collect_late_preview_once import collect

class Integration(unittest.TestCase):
    def test_fetch_to_append_only_evidence(self):
        def fetch(url):
            b=io.StringIO()
            w=csv.DictWriter(b,fieldnames=["レースコード","締切時刻","取得日時","艇1_コース"])
            w.writeheader()
            w.writerow({"レースコード":"202610310111","締切時刻":"19:00","取得日時":"2026-10-31T18:54:00+09:00","艇1_コース":"1"})
            return b.getvalue().encode()
        now=lambda:datetime(2026,10,31,18,55,tzinfo=JST)
        with tempfile.TemporaryDirectory() as folder:
            outcome=collect(day="20261031",root=folder,fetch=fetch,clock=now)
            self.assertEqual(outcome["kinds"]["stt"]["saved"],1)
            self.assertTrue((Path(folder)/"20261031"/"stt"/"202610310111.json").is_file())
            second=collect(day="20261031",root=folder,fetch=fetch,clock=now)
            self.assertEqual(second["kinds"]["stt"]["error"],"FileExistsError")
    def test_late_race_not_written(self):
        now=lambda:datetime(2026,10,31,18,59,tzinfo=JST)
        with tempfile.TemporaryDirectory() as folder:
            outcome=collect(day="20261031",root=folder,fetch=lambda u:b"\xef\xbb\xbf\xe3\x83\xac\xe3\x83\xbc\xe3\x82\xb9\xe3\x82\xb3\xe3\x83\xbc\xe3\x83\x89\n",clock=now)
            self.assertEqual(outcome["kinds"]["stt"]["saved"],0)
if __name__=="__main__":unittest.main()
