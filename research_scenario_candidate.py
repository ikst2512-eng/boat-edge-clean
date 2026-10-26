"""Isolated, uncalibrated trifecta candidate for prospective research only.

A course is an actual starting lane, not necessarily the boat number.
The scenario mixture models winner attack (escape, sashi, makuri,
makuri-sashi, other) and downstream finishing order. Coefficients are
hypotheses, never calibrated or considered validated. No odds are used.
"""
import math
from itertools import permutations

TICKETS = tuple(permutations(range(1, 7), 3))
ATTACKS = ("escape", "sashi", "makuri", "makuri_sashi", "other")

def _numeric(x, label, low, high, default=None):
    if x is None:
        if default is not None:
            return default
        raise ValueError(f"missing {label}")
    if type(x) not in (float, int) or not math.isfinite(x) or not low <= x <= high:
        raise ValueError(f"invalid {label}")
    return float(x)

def _softmax(logits):
    pivot = max(logits)
    values = [math.exp(x - pivot) for x in logits]
    denominator = sum(values)
    return [v / denominator for v in values]

def _course_map(entry):
    if not isinstance(entry, (list, tuple)) or len(entry) != 6 or set(entry) != set(range(1, 7)):
        raise ValueError("entry must be ordered boat numbers in actual courses 1..6")
    return {boat: course for course, boat in enumerate(entry, 1)}

def scenario_probabilities(rates, entry=(1, 2, 3, 4, 5, 6), *, motor=None,
                           exhibition=None, st=None, fl=None):
    """Return 120 probabilities, including scenario-specific second/third effects.

    Missing optional measurements have zero adjustment (explicit neutral prior).
    Actual entry must be known before cutoff; do not use post-start entry.
    """
    if not isinstance(rates, (list, tuple)) or len(rates) != 6:
        raise ValueError("six win rates required")
    skills = [_numeric(x, "win rate", 0.01, 19.99) for x in rates]
    course_of = _course_map(entry)
    for label, values in (("motor", motor), ("exhibition", exhibition),
                          ("st", st), ("fl", fl)):
        if values is not None and (not isinstance(values, (list, tuple)) or len(values) != 6):
            raise ValueError(f"{label} requires six boat-indexed values")
    def optional(values, i, name, lo, hi, neutral):
        return neutral if values is None else _numeric(values[i], name, lo, hi, neutral)
    # Do not assume that a past F count and an actual late start are interchangeable.
    boats = {}
    for i in range(6):
        boat = i + 1
        rate = skills[i]
        motor_val = optional(motor, i, "motor rate", 0, 100, 50)
        exhibition_val = optional(exhibition, i, "exhibition time", 5, 10, 6.8)
        st_val = optional(st, i, "historical ST", 0, 0.5, 0.17)
        fl_val = optional(fl, i, "F/L count", 0, 10, 0)
        boats[boat] = (0.26 * (rate - 6) + 0.008 * (motor_val - 50)
                       - 0.65 * (exhibition_val - 6.8)
                       - 1.3 * (st_val - .17) - .04 * fl_val)
    scenarios = []
    for winner in range(1, 7):
        c = course_of[winner]
        # Course 2 makuri is deliberately permitted, not treated as impossible.
        prior = {"escape": (2.0 if c == 1 else -5.0),
                 "sashi": (0.4 if c == 2 else -0.4 if c <= 4 else -1.1),
                 "makuri": (0.35 if c in (2, 3, 4) else -0.7),
                 "makuri_sashi": (0.2 if c in (3, 4, 5) else -0.8),
                 "other": -0.8}
        for attack in ATTACKS:
            scenarios.append((winner, attack, boats[winner] + prior[attack]
                              - .55 * (c - 1)))
    p_scenario = _softmax([score for _, _, score in scenarios])
    distribution = {ticket: 0.0 for ticket in TICKETS}
    for (winner, attack, _), mass in zip(scenarios, p_scenario):
        left = [x for x in range(1, 7) if x != winner]
        # Attack-specific advantage/disadvantage to other boats for 2nd/3rd.
        follow = {}
        for boat in left:
            course = course_of[boat]
            relative = course - course_of[winner]
            pressure = 0.0
            if attack == "escape":
                pressure = 0.17 if course in (2, 3) else -0.07
            elif attack == "sashi":
                pressure = -0.23 if relative < 0 else 0.13
            elif attack == "makuri":
                pressure = -0.38 if relative < 0 else 0.23
            elif attack == "makuri_sashi":
                pressure = 0.15 if relative < 0 else -0.08
            follow[boat] = boats[boat] - .18 * (course - 1) + pressure
        second_p = _softmax([follow[x] for x in left])
        for second, p2 in zip(left, second_p):
            third_boats = [x for x in left if x != second]
            third_p = _softmax([follow[x] for x in third_boats])
            for third, p3 in zip(third_boats, third_p):
                distribution[(winner, second, third)] += mass * p2 * p3
    total = sum(distribution.values())
    result = sorted(((t, p / total) for t, p in distribution.items()),
                    key=lambda item: (-item[1], item[0]))
    if len(result) != 120 or abs(sum(p for _, p in result) - 1) > 1e-10:
        raise ValueError("invalid distribution")
    return result
