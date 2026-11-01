"""Read-only diagnostic of Top-N misses; never rerank stored forecasts.

Classification is sequential coverage, not a causal explanation of a loss.
"""
from collections import Counter


def classify_miss(tickets, finish_order, top_n=10):
    """Return first uncovered prefix of the confirmed trifecta in frozen Top-N."""
    if type(top_n) is not int or not 1 <= top_n <= 10:
        raise ValueError("top_n must be 1..10")
    if (not isinstance(tickets, list) or len(tickets) < top_n
            or any(not isinstance(t, str) for t in tickets[:top_n])):
        raise ValueError("invalid tickets")
    if (not isinstance(finish_order, (list, tuple)) or len(finish_order) < 3
            or any(type(v) is not int or v not in range(1, 7) for v in finish_order[:3])
            or len(set(finish_order[:3])) != 3):
        raise ValueError("invalid finish")
    parsed = []
    for ticket in tickets[:top_n]:
        parts = ticket.split("-")
        if len(parts) != 3 or any(s not in ("1", "2", "3", "4", "5", "6") for s in parts):
            raise ValueError("invalid ticket")
        numbers = tuple(map(int, parts))
        if len(set(numbers)) != 3:
            raise ValueError("invalid ticket")
        parsed.append(numbers)
    if len(set(parsed)) != len(parsed):
        raise ValueError("duplicate tickets")
    actual = tuple(finish_order[:3])
    if actual in parsed:
        return "hit"
    if not any(t[0] == actual[0] for t in parsed):
        return "first_place_uncovered"
    if not any(t[:2] == actual[:2] for t in parsed):
        return "second_place_uncovered_given_first"
    return "third_place_uncovered_given_first_second"


def summarize_misses(rows):
    """rows: iterable of (frozen_top10_tickets, confirmed_finish_order)."""
    rows = list(rows)  # Materialize once: Top3/5/10 must share the same denominator.
    by_n = {}
    for n in (3, 5, 10):
        counts = Counter()
        for tickets, finish in rows:
            counts[classify_miss(tickets, finish, n)] += 1
        total = sum(counts.values())
        by_n["top" + str(n)] = {
            "evaluated": total,
            "hits": counts["hit"],
            "misses": total - counts["hit"],
            "first_place_uncovered": counts["first_place_uncovered"],
            "second_place_uncovered_given_first": counts["second_place_uncovered_given_first"],
            "third_place_uncovered_given_first_second": counts["third_place_uncovered_given_first_second"],
        }
    return by_n
