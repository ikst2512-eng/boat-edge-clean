"""Immutable active V127/V133 strategy guard for all site/data/research PRs.

This is a strategy continuity test, NOT evidence that the model is calibrated,
accurate, or betting-approved. Any authorized future promotion is a separate
user-approved change after prospective independent validation, never a silent
side effect of UI/data cleanup or a new unproven research candidate.
"""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "research" / "active_forecast_lock_20261114.json"

# A second independent code-side anchor prevents changing only the JSON lock.
# Editing both anchors is explicitly forbidden without user approval and the
# promotion evidence documented in AGENTS §P0 and Issue #1708.
BLOBS = {
    "legacy_v133_reference_engine.py": "3eae88e079f4803351324620d69b5a1c266626a8",
    "legacy_scenario_engine.py": "873ecced0e5792b0fdd12367b25e3c9168373225",
    "boat_edge_v254_third_tail.py": "0263ccdd7963b95a13ac759ec72011c321a892eb",
    "capture_v133_policy.py": "86b0c172021ed7ff804adac693d1e8dac162ffa5",
    "clean_four_modes.py": "c143b836e6e833ff1ff6ee0d8f13dca6a8408c7d",
    "research_model.py": "a8d508cb956a37f1e23133db5c15f2fe4270ba5e",
    "clean_four_mode_capture.py": "233fac24e9caf10681b34c32fe17112faa93e9b4",
}
MODEL = "V127_V133_BALANCE12_HOLE15_18_20_REFERENCE_V2"
POLICY = "BALANCE12_WAVE15_18_20_V133_REFERENCE_V2"
MODES = {"narrow": 3, "hit": 10, "balance": 12, "hole_allowed": [15, 18, 20]}
BASELINE = "CLEAN_FOUR_MODES_V2_PROVISIONAL_UNCALIBRATED"


class ActiveForecastLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_exact_engine_git_blob_fingerprints_stay_frozen(self):
        self.assertEqual(self.record["source_git_blobs"], BLOBS)
        for path, pinned in BLOBS.items():
            with self.subTest(path=path):
                raw = (ROOT / path).read_bytes()
                actual = hashlib.sha1(
                    b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
                ).hexdigest()
                self.assertEqual(actual, pinned, path + " changed without user-approved model promotion")

    def test_user_selected_model_identity_point_counts_and_proof_gate(self):
        x = self.record
        self.assertEqual(x["schema"], "BOAT_EDGE_CLEAN_ACTIVE_FORECAST_IMMUTABLE_LOCK_V1")
        self.assertEqual(x["requirements_issue"],
                         "https://github.com/ikst2512-eng/boat-edge-clean/issues/1708")
        model = x["active_user_selected_forecast"]
        self.assertEqual(model["model_version"], MODEL)
        self.assertEqual(model["selection_policy"], POLICY)
        self.assertEqual(model["ticket_counts"], MODES)
        self.assertEqual(model["source_model"], "legacy_v133_reference_engine.py")
        self.assertFalse(model["odds_may_rerank"])
        self.assertEqual(x["separate_comparators"]["national_only_v2"], BASELINE)
        self.assertFalse(x["first_remote_add_verified"])
        self.assertFalse(x["formal_accuracy_proven"])
        self.assertFalse(x["production_purchase_approved"])
        gate = x["unlock_only_after"]
        self.assertEqual(set(gate), {
            "new_independent_challenger_id_and_preregistered_source",
            "independently_authenticated_predeadline_first_remote_preservation",
            "future_pilot_300_and_separate_confirmation_300",
            "paired_top1_top3_top5_top10_and_brier_logloss",
            "no_top5_or_top10_regression",
            "source_audit_and_full_reproducibility",
            "user_explicit_approval_to_switch",
            "human_review_and_live_pages_render_e2e",
        })
        self.assertTrue(all(gate.values()))
        self.assertTrue(x["frozen_files_must_not_change_in_parallel_research"])

    def test_primary_live_api_remains_v133_and_never_switches_models(self):
        api = (ROOT / "server.py").read_text(encoding="utf-8")
        start = api.index("def get_v133_reference_preview(")
        end = api.index("\n# The historical holdout evaluator", start)
        primary = api[start:end]
        self.assertIn("from legacy_v133_reference_engine import v133_reference_preview", primary)
        self.assertIn("output = v133_reference_preview(card_loader(hd, jcd, rno), now=now)", primary)
        self.assertIn('"race_already_closed"', primary)
        self.assertIn('"past_race_not_recomputed"', primary)
        self.assertIn('output.get("production_buy_approved") is not False', primary)
        self.assertIn('elif path == "/api/v133-reference-preview":', api)

        page = (ROOT / "index.html").read_text(encoding="utf-8")
        first = page.index("async function loadOriginalV133Frozen(key,token,status,root){")
        last = page.index("async function loadRestoredScenarioPreview(", first)
        display = page[first:last]
        self.assertNotIn("return false", display, "must not silently fall back to an unrelated model")
        self.assertIn(MODEL, display)
        self.assertIn(POLICY, display)
        self.assertIn("validModes(d.modes,false)", display)
        self.assertIn("validModes(d.modes,true)", display)
        self.assertIn("(oldSaved?[12,15,18]:[15,18,20])", display)
        self.assertIn("validRows(m.balance?.tickets,oldSaved?10:12)", display)
        self.assertIn("別の未検証モデルに自動切替しません", display)
        self.assertIn("if(await loadOriginalV133Frozen(key,token,status,root))return;", page)

    def test_shared_agent_contract_prevents_other_chat_substitution(self):
        contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("## P0. 予想エンジン固定・他トークの無断変更禁止", contract)
        self.assertIn("将来300レースの予備＋別期間300レースの独立確認", contract)
        self.assertIn("ユーザー本人が新方式へ切り替えることを明示承認", contract)
        self.assertIn(MODEL, contract)
        self.assertIn("強制マージに注意", contract)


if __name__ == "__main__":
    unittest.main()
