"""Source-port reference tests. No historical backfill or formal adoption."""
import copy
import unittest
from datetime import datetime
from itertools import permutations
from legacy_v133_reference_engine import SOURCE_BLOB, v133_reference_preview, modes_from_tickets
from server import get_v133_reference_preview
from legacy_scenario_engine import JST
from test_legacy_scenario_engine import current_card, NOW


class LegacyV133ReferenceTests(unittest.TestCase):
    def test_original_v133_mode_counts_and_source_identity(self):
        record = v133_reference_preview(current_card(), NOW)
        self.assertEqual(record["model_version"], "V127_V133_BALANCE12_HOLE15_18_20_REFERENCE_V2")
        self.assertEqual(record["race_code"], "202611120501")
        self.assertEqual(len(SOURCE_BLOB), 40)
        self.assertEqual(record["source_model_git_blob"], SOURCE_BLOB)
        self.assertEqual({mode: len(info["tickets"]) for mode, info in record["modes"].items() if mode not in ("hole", "tail")},
                         {"narrow": 3, "hit": 10, "balance": 12})
        self.assertIn("tail", record["modes"])
        self.assertEqual(len(record["modes"]["tail"]["tickets"]), 10)
        self.assertIn(len(record["modes"]["hole"]["tickets"]), (15, 18, 20))
        self.assertFalse(record["formal"])
        self.assertFalse(record["calibrated"])
        self.assertFalse(record["production_buy_approved"])
        self.assertFalse(record["accuracy_improvement_proven"])
        self.assertFalse(record["first_remote_add_verified"])
        self.assertIn("old_site_three_month_course_stats_not_imported", record["missing_or_unverified"])
        self.assertEqual(v133_reference_preview(current_card(), NOW)["modes"], record["modes"])

    def test_new_selection_policy_is_identified_and_not_formal(self):
        record = v133_reference_preview(current_card(), NOW)
        self.assertEqual(record["selection_policy"], "BALANCE12_WAVE15_18_20_V133_REFERENCE_V2")
        self.assertFalse(record["formal"])
        self.assertFalse(record["production_buy_approved"])

    def test_hole_points_follow_actual_head_scenario_spread(self):
        combos = ["-".join(map(str, xs)) for xs in permutations(range(1, 7), 3)]
        for weights, wanted in [
            ([100, .1, .1, .1, .1, .1], 15),
            ([10, 6, 4, .01, .01, .01], 18),
            ([1, 1, 1, 1, 1, 1], 20),
        ]:
            rows = [{"combo": combo, "p": weights[int(combo[0]) - 1]}
                    for combo in combos]
            mode = modes_from_tickets(rows, {}, rows, adopt_tail=False)
            with self.subTest(wanted=wanted):
                self.assertEqual({k: len(v) for k, v in mode.items()},
                                 {"hit": 10, "balance": 12,
                                  "hole": wanted, "narrow": 3})
                self.assertEqual([t["combo"] for t in mode["hit"]],
                                 [t["combo"] for t in rows[:10]])
                self.assertEqual([t["combo"] for t in mode["narrow"]],
                                 [t["combo"] for t in rows[:3]])
                self.assertEqual([t["combo"] for t in mode["balance"][:7]],
                                 [t["combo"] for t in rows[:7]])
                for name, tickets in mode.items():
                    self.assertEqual(len({t["combo"] for t in tickets}), len(tickets), name)

    def test_existing_guard_prevents_results_and_after_deadline(self):
        card = current_card()
        with self.assertRaises(ValueError):
            v133_reference_preview(card, datetime(2026, 11, 12, 12, 1, tzinfo=JST))
        card["meta"]["results_seen"] = True
        with self.assertRaises(ValueError):
            v133_reference_preview(card, NOW)

    def test_source_missing_not_fabricated(self):
        card = current_card()
        del card["racers"][2]["national"]["win_rate"]
        with self.assertRaises(ValueError):
            v133_reference_preview(card, NOW)
        card = current_card(with_before=False)
        with self.assertRaises(ValueError):
            v133_reference_preview(card, NOW)

    def test_non_inner_exhibition_course_refuses_old_boat_one_escape(self):
        card = current_card()
        card["beforeinfo"]["start_exhibition"][0]["course"] = 4.0
        card["beforeinfo"]["start_exhibition"][3]["course"] = 1.0
        with self.assertRaisesRegex(ValueError, "legacy_escape_world_requires_boat1_exhibition_course1"):
            v133_reference_preview(card, NOW)

    def test_server_route_reads_current_one_race_only(self):
        calls = []
        def source(hd,jcd,rno):
            calls.append((hd,jcd,rno))
            return current_card()
        status, payload = get_v133_reference_preview(
            {"hd":["20261112"],"jcd":["05"],"rno":["1"]},card_loader=source,now=NOW)
        self.assertEqual(status,200)
        self.assertTrue(payload["ok"])
        self.assertEqual(calls,[("20261112","05","1")])
        bad, _ = get_v133_reference_preview(
            {"hd":["20261112"],"jcd":["05"],"rno":["1"]},card_loader=source,
            now=datetime(2026,11,12,12,1,tzinfo=JST))
        self.assertEqual(bad,422)


if __name__ == "__main__":
    unittest.main()
