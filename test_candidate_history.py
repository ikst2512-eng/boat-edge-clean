"""Daily candidate retention/settlement tests (no network, no reforecast)."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from candidate_history import daily_candidate_history

ROOT = Path(__file__).resolve().parent
DAY = "20261108"


def prediction(code, minute=21):
    return {
        "race_code": code,
        "status": "prospective_candidate",
        "formal": False,
        "scoring": False,
        "validated": False,
        "generated_at": "2026-11-08T10:12:31+09:00",
        "source_title_received_jst": "2026-11-08T10:12:30+09:00",
        "source_cards_received_jst": "2026-11-08T10:12:30+09:00",
        "cutoff_jst": f"2026-11-08T15:{minute - 12:02d}:00+09:00",
        "source_deadline_jst": f"2026-11-08T15:{minute:02d}:00+09:00",
        "predictions": ["1-2-3", "1-3-2", "2-1-3"],
        "model_version": "research-only-test",
    }


def confirmed(code):
    return {
        "race_code": code,
        "status": "confirmed",
        "finish_order": [1, 2, 3],
        "source_url": "https://boatracecsv.github.io/data/results/realtime/2026/11/08.csv",
        "confirmed_at_jst": "2026-11-08T15:40:00+09:00",
        "collected_at_jst": "2026-11-08T16:01:00+09:00",
    }


class CandidateHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "prospective_predictions").mkdir()
        (self.root / "confirmed_results").mkdir()
        (self.root / "payout_evidence").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, folder, code, obj):
        path = self.root / folder / (code + ".json")
        path.write_text(json.dumps(obj), encoding="utf-8")
        return path

    def test_all_eight_candidates_survive_deadline_without_six_item_limit(self):
        for n in range(1, 9):
            code = DAY + "01" + f"{n:02d}"
            self.write("prospective_predictions", code, prediction(code, 20 + n))
        self.write("confirmed_results", DAY + "0101", confirmed(DAY + "0101"))
        status, data = daily_candidate_history(DAY, self.root)
        self.assertEqual(status, 200)
        self.assertEqual(data["candidate_count"], 8)
        self.assertEqual(data["research_forecast_count"], 8)
        self.assertEqual(data["confirmed_result_count"], 1)
        self.assertEqual(len(data["races"]), 8)
        self.assertEqual(data["races"][0]["race_code"], DAY + "0101")
        self.assertEqual(data["races"][0]["finish"], "1-2-3")
        self.assertEqual(data["races"][0]["tickets"], ["1-2-3", "1-3-2", "2-1-3"])
        self.assertTrue(all(row["forecast_status"] == "saved_research_unattested" for row in data["races"]))
        self.assertTrue(all(row["result_status"] == "pending" for row in data["races"][1:]))
        self.assertFalse(data["production_forecast"])
        self.assertFalse(data["first_git_add_verified"])

    def test_research_candidates_never_claim_a_certified_buy_and_show_source_gaps(self):
        code = DAY + "0101"
        record = prediction(code)
        record["national_win_rates"] = [6.34, 3.02, 3.93, 3.08, 4.53, 5.43]
        record["model_version"] = "clean-prospective-national-beta0.4-v1"
        record["input_source_kind"] = "public_pre_race_csv"
        self.write("prospective_predictions", code, record)
        _, d = daily_candidate_history(DAY, self.root)
        self.assertEqual(d["purchase_review_schema"], "candidate_evidence_hold_v1")
        self.assertEqual(d["purchase_review_approved_count"], 0)
        row = d["races"][0]
        self.assertEqual(row["selection_status"], "research_70_pass")
        self.assertEqual(row["purchase_review_status"], "hold_evidence_not_attested")
        self.assertEqual(len(row["purchase_review_missing"]), 6)
        self.assertIn("start_exhibition_entry_st", row["purchase_review_missing"])
        self.assertIn("course_2_wall_escape", row["purchase_review_missing"])
        self.assertIn("wind_waves_water", row["purchase_review_missing"])
        self.assertEqual(row["research_input_received_jst"], "2026-11-08T10:12:30+09:00")
        # Confirmed result does not retroactively certify an earlier buy decision.
        self.write("confirmed_results", code, confirmed(code))
        _, after = daily_candidate_history(DAY, self.root)
        self.assertEqual(after["races"][0]["purchase_review_status"], "hold_evidence_not_attested")
        self.assertEqual(after["purchase_review_approved_count"], 0)

    def test_invalid_candidate_cannot_claim_buy_readiness(self):
        code = DAY + "0101"
        invalid = prediction(code)
        invalid["generated_at"] = "2026-11-08T15:09:00+09:00"
        invalid["purchase_review_status"] = "approved"
        invalid["official_exhibition"] = {"certified": True}
        self.write("prospective_predictions", code, invalid)
        _, d = daily_candidate_history(DAY, self.root)
        row = d["races"][0]
        self.assertEqual(row["purchase_review_status"], "unassessed")
        self.assertEqual(row["forecast_status"], "unverified")
        self.assertIsNone(row["research_input_received_jst"])
        self.assertEqual(d["purchase_review_approved_count"], 0)

    def test_only_independently_verified_payout_is_shown(self):
        code = DAY + "0101"
        self.write("prospective_predictions", code, prediction(code))
        result = confirmed(code)
        result["source_sha256"] = "a" * 64
        self.write("confirmed_results", code, result)
        payout = {
            "schema": "CLEAN_TRIFECTA_PAYOUT_EVIDENCE_V1",
            "race_code": code,
            "winning_ticket": "1-2-3",
            "payout_yen_per_100": 8910,
            "source_url": "https://boatracecsv.github.io/data/results/payouts/2026/11/08.csv",
            "source_sha256": "b" * 64,
            "confirmed_result_source_sha256": "a" * 64,
            "verified_against_confirmed_finish": True,
            "formal": False,
        }
        source = self.write("payout_evidence", code, payout)
        _, data = daily_candidate_history(DAY, self.root)
        row = data["races"][0]
        self.assertEqual(row["payout_status"], "verified_independent")
        self.assertEqual(row["payout_yen_per_100"], 8910)
        self.assertEqual(data["payout_verified_count"], 1)
        self.assertEqual(row["finish"], "1-2-3")
        self.assertEqual(row["result_status"], "confirmed_archive")

        for bad in [dict(payout, winning_ticket="1-3-2"),
                    dict(payout, confirmed_result_source_sha256="c" * 64),
                    dict(payout, payout_yen_per_100=0),
                    dict(payout, verified_against_confirmed_finish=False)]:
            with self.subTest(payout=bad):
                source.write_text(json.dumps(bad), encoding="utf-8")
                _, response = daily_candidate_history(DAY, self.root)
                row = response["races"][0]
                self.assertEqual(row["payout_status"], "unverified")
                self.assertIsNone(row["payout_yen_per_100"])
                self.assertEqual(response["payout_verified_count"], 0)
                self.assertEqual(row["finish"], "1-2-3")
        source.unlink()
        _, response = daily_candidate_history(DAY, self.root)
        self.assertEqual(response["races"][0]["payout_status"], "unverified")
        self.assertIsNone(response["races"][0]["payout_yen_per_100"])

    def test_result_must_be_verified_before_any_payout(self):
        code = DAY + "0101"
        self.write("prospective_predictions", code, prediction(code))
        self.write("payout_evidence", code, {
            "race_code": code,
            "winning_ticket": "1-2-3",
            "payout_yen_per_100": 800,
        })
        _, response = daily_candidate_history(DAY, self.root)
        row = response["races"][0]
        self.assertEqual(row["result_status"], "pending")
        self.assertEqual(row["payout_status"], "unverified")
        self.assertIsNone(row["payout_yen_per_100"])

    def test_broken_prediction_remains_listed_but_never_shows_bad_tickets(self):
        code = DAY + "0101"
        record = prediction(code)
        record["generated_at"] = "2026-11-08T15:10:00+09:00"
        path = self.write("prospective_predictions", code, record)
        status, data = daily_candidate_history(DAY, self.root)
        self.assertEqual((status, data["candidate_count"]), (200, 1))
        self.assertEqual(data["races"][0]["forecast_status"], "unverified")
        self.assertEqual(data["races"][0]["tickets"], [])
        self.assertEqual(json.loads(path.read_text()), record)

    def test_confirmed_result_never_creates_a_missing_prediction(self):
        code = DAY + "0101"
        self.write("confirmed_results", code, confirmed(code))
        status, data = daily_candidate_history(DAY, self.root)
        self.assertEqual((status, data["candidate_count"]), (200, 0))
        self.write("prospective_predictions", code, prediction(code))
        status, data = daily_candidate_history(DAY, self.root)
        self.assertEqual(data["races"][0]["finish"], "1-2-3")
        self.assertTrue(data["races"][0]["tickets"])

    def test_invalid_result_never_claims_confirmed(self):
        code = DAY + "0101"
        self.write("prospective_predictions", code, prediction(code))
        result = confirmed(code)
        result["finish_order"] = [1, 1, 3]
        self.write("confirmed_results", code, result)
        _, data = daily_candidate_history(DAY, self.root)
        self.assertEqual(data["races"][0]["result_status"], "unverified")
        self.assertIsNone(data["races"][0]["finish"])

    def test_symlink_and_corrupt_file_preserve_key_not_false_predictions(self):
        code = DAY + "0101"
        actual = self.root / "other.json"
        actual.write_text(json.dumps(prediction(code)), encoding="utf-8")
        (self.root / "prospective_predictions" / (code + ".json")).symlink_to(actual)
        _, data = daily_candidate_history(DAY, self.root)
        self.assertEqual(data["candidate_count"], 1)
        self.assertEqual(data["races"][0]["forecast_status"], "unverified")

    def test_date_validation_and_empty_day(self):
        for bad in ("../etc", "20260230", "2026-11-08", DAY + "x", ""):
            with self.subTest(bad=bad):
                self.assertEqual(daily_candidate_history(bad, self.root)[0], 400)
        self.assertEqual(daily_candidate_history(DAY, self.root)[1]["candidate_count"], 0)

    def test_shipped_november_eight_archive_is_not_capped(self):
        # Live archive sizes may grow. Validate the checked-in dataset itself.
        status, data = daily_candidate_history(DAY, ROOT)
        self.assertEqual(status, 200)
        sources = list((ROOT / "prospective_predictions").glob(DAY + "????.json"))
        self.assertGreater(len(sources), 6)
        self.assertEqual(data["candidate_count"], len(sources))
        self.assertEqual(len({r["race_code"] for r in data["races"]}), len(sources))

    def test_selection_html_is_all_day_and_links_to_immutable_archive(self):
        page = (ROOT / "selection.html").read_text(encoding="utf-8")
        controller = (ROOT / "candidate_history.js").read_text(encoding="utf-8")
        server = (ROOT / "server.py").read_text(encoding="utf-8")
        self.assertIn('src="/candidate_history.js"', page)
        self.assertNotIn("showTodayCandidates()", page)
        self.assertIn("CLEAN_CANDIDATE_HISTORY_V1", controller)
        self.assertIn("candidate_count!==d.races.length", controller)
        self.assertIn("showRace(race)", controller)
        self.assertIn("result_status", controller)
        self.assertIn("/api/four-mode-archive?code=", controller)
        self.assertIn('"/api/candidate-history"', server)
        self.assertIn('"/candidate_history.js"', server)
        pages = (ROOT / "candidates.html").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "deploy-pages.yml").read_text(encoding="utf-8")
        nav = (ROOT / "navigation.js").read_text(encoding="utf-8")
        self.assertIn('id="candidateCards"', pages)
        self.assertIn('src="candidate_history.js"', pages)
        self.assertIn("candidate_history/'+day+'.json", controller)
        self.assertIn("public/candidate_history", workflow)
        self.assertIn("'prospective_predictions/**'", workflow)
        self.assertIn("selection.href='/boat-edge-clean/candidates.html'", nav)


if __name__ == "__main__":
    unittest.main()
