"""Check prediction feed contract without shipping invented predictions."""
import json
from itertools import permutations
import tempfile
from pathlib import Path
from unittest.mock import patch
from server import get_predictions

QUERY = {"hd": ["20261022"], "jcd": ["12"], "rno": ["1"]}
KEY = "20261022-12-1"
TICKETS = ["1-2-3","1-2-4","1-2-5","1-2-6","1-3-2","1-3-4","1-3-5","1-3-6","1-4-2","1-4-3"]

def check():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with patch("server.ROOT", root), patch("server.verify_commit_proof") as verified:
            status, response = get_predictions(QUERY)
            assert status == 200 and response["status"] == "unavailable"
            valid = [f"{a}-{b}-{c}" for a,b,c in permutations(range(1,7),3)]
            probabilities = {ticket: 1/120 for ticket in valid}
            record = {"probabilities": probabilities, "race_code":"202610221201","predictions":[{"ticket": t, "probability": probabilities[t]} for t in TICKETS],
                      "model_version":"regression-fixture", "generated_at":"2026-10-22T00:00:00+09:00",
                      "validated":True, "deadline_at":"2026-10-22T12:00:00+09:00", "freeze_proof": {"commit_sha": "a"*40,
                      "committed_at": "2026-10-22T00:02:00+09:00", "deadline_at": "2026-10-22T12:00:00+09:00"}}
            (root / "predictions.json").write_text(json.dumps({KEY:record}))
            status, response = get_predictions(QUERY)
            assert status == 200 and response["status"] == "available"
            assert response["predictions"] == TICKETS
            assert verified.call_count == 1
            # A selected ticket must reflect the numerical ranking, not an
            # arbitrary ten-ticket list with valid-looking ticket strings.
            record["predictions"][0]["probability"] = 0.5
            (root / "predictions.json").write_text(json.dumps({KEY:record}))
            status, response = get_predictions(QUERY)
            assert status == 503
            record["predictions"][0]["probability"] = probabilities[TICKETS[0]]
            record["probabilities"][TICKETS[0]] = 0.5
            (root / "predictions.json").write_text(json.dumps({KEY:record}))
            status, response = get_predictions(QUERY)
            assert status == 503
            record["probabilities"][TICKETS[0]] = probabilities[TICKETS[0]]

            # A flag alone cannot mark a prediction as Fresh.
            saved_proof = record.pop("freeze_proof")
            (root / "predictions.json").write_text(json.dumps({KEY:record}))
            status, response = get_predictions(QUERY)
            assert status == 503 and not response["ok"]
            record["freeze_proof"] = saved_proof
            record["freeze_proof"]["committed_at"] = "2026-10-22T12:00:00+09:00"
            (root / "predictions.json").write_text(json.dumps({KEY:record}))
            status, response = get_predictions(QUERY)
            assert status == 503 and not response["ok"]
            record["freeze_proof"]["committed_at"] = "2026-10-22T00:02:00+09:00"
            record["predictions"][9] = {"ticket":"1-2-3"}
            (root / "predictions.json").write_text(json.dumps({KEY:record}))
            status, response = get_predictions(QUERY)
            assert status == 503 and not response["ok"]
            record["predictions"][9] = {"ticket":"1-4-3"}
            record["validated"] = False
            (root / "predictions.json").write_text(json.dumps({KEY:record}))
            status, response = get_predictions(QUERY)
            assert status == 503 and not response["ok"]
    print("Prediction API contract tests passed")

if __name__ == "__main__":
    check()
