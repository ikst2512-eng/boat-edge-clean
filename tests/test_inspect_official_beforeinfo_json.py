import unittest
from scripts.inspect_official_beforeinfo_json import inspect


class OfficialJsonReadinessTests(unittest.TestCase):
    def sample(self, extimes):
        return {"maindata": {
            "rno": "11", "deadline": "20:06",
            "teiinfolist": [{"teino": str(i+1), "extime": value}
                             for i, value in enumerate(extimes)],
            "sttenjiinfolist": [],
        }}

    def test_six_racers_without_exhibition_is_not_complete(self):
        result = inspect(self.sample([""]*6))
        self.assertEqual(result["racers_listed"], 6)
        self.assertTrue(result["six_unique_boats"])
        self.assertFalse(result["exhibition_time_nonempty_six"])
        self.assertEqual(result["exhibition_time_observed_boats"], 0)
        self.assertEqual(result["tilt_observed_boats"], 0)
        self.assertFalse(result["forecast_usable"])
        self.assertFalse(result["t12_eligible"])

    def test_complete_exhibition_is_still_not_t12_certified(self):
        result = inspect(self.sample(["6.8"]*6))
        self.assertTrue(result["exhibition_time_nonempty_six"])
        self.assertEqual(result["status"], "six_exhibition_values_observed_not_time_certified")
        self.assertFalse(result["forecast_usable"])
        self.assertFalse(result["t12_eligible"])

    def test_duplicate_tear_and_missing_values_fail_closed(self):
        result = self.sample(["6.8"]*6)
        result["maindata"]["teiinfolist"][5]["teino"] = "5"
        self.assertFalse(inspect(result)["six_unique_boats"])
        self.assertFalse(inspect(result)["exhibition_time_nonempty_six"])
        self.assertFalse(inspect(self.sample(["6.8"]*5 + [""]))["exhibition_time_nonempty_six"])

    def test_partial_exhibition_counts_do_not_certify(self):
        payload = self.sample(["6.8", "6.9", "", "", "", ""])
        payload["maindata"]["teiinfolist"][0]["tilt"] = "-0.5"
        result = inspect(payload)
        self.assertEqual(result["exhibition_time_observed_boats"], 2)
        self.assertEqual(result["tilt_observed_boats"], 1)
        self.assertFalse(result["exhibition_time_nonempty_six"])
        self.assertFalse(result["forecast_usable"])
        self.assertFalse(result["t12_eligible"])

    def test_missing_schema_rejected(self):
        with self.assertRaises(ValueError):
            inspect({"maindata": {"teiinfolist": None}})
        with self.assertRaises(ValueError):
            inspect({"maindata": []})


if __name__ == "__main__":
    unittest.main()
