"""Finite outcome coverage, NOT a claim of exhaustively observed tactical paths.

All 120 ordered three-place results are enumerated under an explicitly supplied
exhibition 6-course permutation. A finish alone NEVER identifies the tactical
path, win method, start, walls, slipstream or attack beneficiary. Every causal
link below is an *unverified candidate*, subject to separate pre-race evidence.
"""
from itertools import permutations

MODEL_ID = "EXPLORATORY_ONLY_FULL_120_PATHWAY_CATALOG_V1"
TACTICS_BY_COURSE = {
    1: ("escape", "late_overtake", "fortunate"),
    2: ("sashi", "makuri", "late_overtake", "fortunate"),
    3: ("makuri", "makuri_sashi", "sashi", "late_overtake", "fortunate"),
    4: ("makuri", "makuri_sashi", "sashi", "late_overtake", "fortunate"),
    5: ("makuri_sashi", "makuri", "sashi", "late_overtake", "fortunate"),
    6: ("makuri_sashi", "makuri", "sashi", "late_overtake", "fortunate"),
}
# Non-first-place attacking can include maneuvers not encoded in official
# "winning method". This catalog does not infer these maneuvers as events.
ATTACK_INITIATORS = (2, 3, 4, 5, 6)
RESULT_POSITIONS = ("first", "second", "third")


def complete_pathway_catalog(exhibition_course_by_boat=None):
    """Produce complete 120 results + all five attacker *candidate* branches.

    exhibition_course_by_boat maps each boat 1..6 to exhibition course 1..6.
    It must not be mistaken for unverified final race entry.
    """
    mapping = ({i: i for i in range(1, 7)}
               if exhibition_course_by_boat is None
               else exhibition_course_by_boat)
    if (type(mapping) is not dict or set(mapping) != set(range(1, 7))
            or any(type(c) is not int for c in mapping.values())
            or set(mapping.values()) != set(range(1, 7))):
        raise ValueError("six_unique_exhibition_courses_required")
    boat_by_course = {course: boat for boat, course in mapping.items()}
    rows = []
    for h, s, t in permutations(range(1, 7), 3):
        courses = (mapping[h], mapping[s], mapping[t])
        roles = {}
        hypothetical_attack_beneficiaries = {}
        for course in ATTACK_INITIATORS:
            role = (RESULT_POSITIONS[courses.index(course)]
                    if course in courses else "outside_top3")
            roles[str(course)] = role
            # Enumerate every other boat in the Top3 as a potential beneficiary
            # if this attacker was active. These are not causal observations.
            hypothetical_attack_beneficiaries[str(course)] = [
                {"beneficiary_course": c, "beneficiary_boat": boat_by_course[c],
                 "finish_position": RESULT_POSITIONS[i]}
                for i, c in enumerate(courses) if c != course
            ]
        rows.append({
            "ticket": f"{h}-{s}-{t}",
            "finish_courses": list(courses),
            "first_course": courses[0],
            "first_possible_official_winning_methods":
                list(TACTICS_BY_COURSE[courses[0]]),
            "second_relative_to_first": ("inside" if courses[1] < courses[0] else "outside"),
            "third_relative_to_first": ("inside" if courses[2] < courses[0] else "outside"),
            "initiator_candidate_roles": roles,
            "hypothetical_attack_beneficiaries": hypothetical_attack_beneficiaries,
            "actual_winning_method": None,
            "actual_attack_observed": None,
            "actual_beneficiary_causality_observed": None,
        })
    return {
        "model_id": MODEL_ID,
        "entry_kind": "exhibition_course_only_not_actual_entry",
        "boat_to_exhibition_course": {str(k): mapping[k] for k in range(1, 7)},
        "outcomes": rows,
        "outcome_count": len(rows),
        "attacker_courses_considered": list(ATTACK_INITIATORS),
        "predicted_probabilities": False,
        "source_authenticated": False,
        "results_read": False,
        "trained": False,
        "production_changed": False,
        "promotion_allowed": False,
    }
