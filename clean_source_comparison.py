"""Fail-closed same-race comparison for isolated untrusted CSV and official records.

Both inputs must already have passed their individual provenance validators.
No upstream fetching, publication, prediction generation or scoring takes place.
"""


def compare_race_sources(csv_stage, official_stage):
    if not isinstance(csv_stage, dict) or not isinstance(official_stage, dict):
        raise ValueError("missing source record")
    if csv_stage.get("status") != "staged_unpublished" or official_stage.get("status") != "staged_unpublished":
        raise ValueError("unstaged input")
    code = csv_stage.get("race_code")
    if not isinstance(code, str) or len(code) != 12 or not code.isascii() or not code.isdigit():
        raise ValueError("invalid race code")
    if official_stage.get("race_key") != f"{code[:8]}-{code[8:10]}-{code[10:12]}":
        raise ValueError("cross-race comparison blocked")
    csv_racers = csv_stage.get("racers")
    official_racers = official_stage.get("racers")
    if not isinstance(csv_racers, list) or not isinstance(official_racers, list):
        raise ValueError("racers unavailable")
    if len(csv_racers) != 6 or len(official_racers) != 6:
        raise ValueError("six racers required")
    c = {x.get("lane"): x for x in csv_racers if isinstance(x, dict)}
    o = {x.get("lane"): x for x in official_racers if isinstance(x, dict)}
    if set(c) != set(range(1, 7)) or set(o) != set(range(1, 7)):
        raise ValueError("invalid lane set")
    mismatches = []
    unknown = []
    for lane in range(1, 7):
        for field in ("name", "registration"):
            left, right = c[lane].get(field), o[lane].get(field)
            if left is None or right is None or str(left).strip() == "" or str(right).strip() == "":
                unknown.append(f"lane{lane}.{field}")
            elif str(left).strip() != str(right).strip():
                mismatches.append(f"lane{lane}.{field}")
    return {
        "race_key": official_stage["race_key"],
        "status": "matched_unpublished" if not mismatches and not unknown else "blocked_unpublished",
        "mismatches": mismatches, "unknown": unknown,
        "sources": {"csv": csv_stage.get("source_url"), "official": official_stage.get("source_url")},
    }
