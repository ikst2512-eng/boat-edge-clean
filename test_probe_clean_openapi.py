import json
import unittest
from urllib.error import HTTPError
from probe_clean_openapi import check

DAY="20261029"
def fixture():
    racers={str(i):{"entry_number":i,"number":4100+i,"national_win_rate":5.0+i/10} for i in range(1,7)}
    return {"programs":{"stadiums":{"1":{"races":{"1":{"date":"2026-10-29","closed_at":"2026-10-29 12:00:00","racers":racers}}}}}}

class OpenApiProbeTests(unittest.TestCase):
    def test_six_complete_racers(self):
        out=check(DAY,lambda _:json.dumps(fixture()).encode())
        self.assertEqual(out["eligible_six_boat_races"],1)
        self.assertFalse(out["forecast_written"])
    def test_missing_one_racer_is_not_eligible(self):
        data=fixture()
        data["programs"]["stadiums"]["1"]["races"]["1"]["racers"].pop("6")
        out=check(DAY,lambda _:json.dumps(data).encode())
        self.assertEqual(out["eligible_six_boat_races"],0)
        self.assertEqual(out["incomplete_races"],1)
    def test_duplicate_registration_is_not_eligible(self):
        data=fixture()
        data["programs"]["stadiums"]["1"]["races"]["1"]["racers"]["6"]["number"]=4101
        out=check(DAY,lambda _:json.dumps(data).encode())
        self.assertEqual(out["eligible_six_boat_races"],0)
    def test_404_is_not_an_outage(self):
        def missing(url):raise HTTPError(url,404,"Not Found",None,None)
        self.assertEqual(check(DAY,missing)["status"],"not_published")
if __name__=="__main__":unittest.main()
