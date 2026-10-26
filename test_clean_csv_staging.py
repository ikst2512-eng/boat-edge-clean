import unittest
from clean_csv_staging import map_race_card

CODE = "202610271201"
URL = "https://boatracecsv.github.io/data/programs/race_cards/2026/10/27.csv"
FETCHED = "2026-10-27T09:00:00+09:00"
FIELDS = ["レースコード","レース日","レース場コード","レース回"] + [f"艇{i}_{field}" for i in range(1,7) for field in ("選手名","登録番号")]

def fixture(code=CODE):
    values = [code,"2026-10-27","12","1R"] + [v for i in range(1,7) for v in (f"選手{i}",str(4000+i))]
    return ",".join(FIELDS) + "\n" + ",".join(values) + "\n"

class CsvStagingTest(unittest.TestCase):
    def test_documented_column_mapping(self):
        result=map_race_card(fixture(),CODE,URL,FETCHED)
        self.assertEqual(len(result["racers"]),6)
        self.assertEqual(result["racers"][0]["registration"],"4001")
        self.assertEqual(result["status"],"staged_unpublished")
        self.assertEqual(result["source_kind"],"third_party_csv_unverified")
    def test_missing_or_duplicate_rows_rejected(self):
        for data in (fixture("202610271202"),fixture()+fixture().split("\n")[1]+"\n"):
            with self.subTest(data=data[:20]),self.assertRaises(ValueError):
                map_race_card(data,CODE,URL,FETCHED)
    def test_missing_racer_rejected(self):
        with self.assertRaises(ValueError):
            map_race_card(fixture().replace("選手6",""),CODE,URL,FETCHED)
    def test_cross_date_url_rejected(self):
        with self.assertRaises(ValueError):
            map_race_card(fixture(),CODE,URL.replace("10/27","10/26"),FETCHED)
    def test_wrong_venue_rejected(self):
        with self.assertRaises(ValueError):
            map_race_card(fixture().replace(",12,1R,",",11,1R,"),CODE,URL,FETCHED)
    def test_incorrect_date_rejected(self):
        with self.assertRaises(ValueError):
            map_race_card(fixture().replace("2026-10-27","2026-10-26"),CODE,URL,FETCHED)
    def test_invalid_race_label_rejected(self):
        with self.assertRaises(ValueError):
            map_race_card(fixture().replace(",1R,",",1,"),CODE,URL,FETCHED)
    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            map_race_card(fixture(),CODE,URL,"2026-10-27T09:00:00")

if __name__ == "__main__":
    unittest.main()
