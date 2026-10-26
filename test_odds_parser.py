"""Offline regression test for the six-column, 120-combination official odds layout."""
from itertools import permutations
from html import escape
from server import parse_official_odds_table
import server
import time

def make_fixture():
    rows = []
    for second_index in range(5):
        for third_index in range(4):
            cells = []
            for first in range(1, 7):
                others = [n for n in range(1, 7) if n != first]
                second = others[second_index]
                third = [n for n in others if n != second][third_index]
                odds = f"{first * 100 + second * 10 + third}.0"
                if third_index == 0:
                    cells += [str(second), str(third), odds]
                else:
                    cells += [str(third), odds]
            rows.append("<tr>" + "".join(f"<td>{escape(x)}</td>" for x in cells) + "</tr>")
    return "<html><table><tr><th>head</th></tr>" + "".join(rows) + "</table></html>"

def test_complete_120():
    result = parse_official_odds_table(make_fixture())
    expected = {f"{a}-{b}-{c}" for a, b, c in permutations(range(1, 7), 3)}
    assert set(result) == expected, f"Expected 120 tickets, got {len(result)}"
    assert result["1-2-3"] == 123.0
    assert result["6-5-4"] == 654.0

def test_missing_cell_rejected():
    html = make_fixture().replace("<td>123.0</td>", "", 1)
    try:
        parse_official_odds_table(html)
    except ValueError:
        return
    raise AssertionError("Incomplete odds table must be rejected")

def must_reject(html, reason):
    try:
        parse_official_odds_table(html)
    except ValueError:
        return
    raise AssertionError(reason)

def test_duplicate_combination_rejected():
    html = make_fixture().replace("<td>2</td><td>3</td><td>123.0</td>", "<td>3</td><td>2</td><td>123.0</td>", 1)
    must_reject(html, "Duplicate ticket or incomplete ticket set must be rejected")

def test_zero_odds_rejected():
    html = make_fixture().replace("<td>123.0</td>", "<td>0</td>", 1)
    must_reject(html, "Zero odds must be rejected")

def test_extreme_odds_rejected():
    html = make_fixture().replace("<td>123.0</td>", "<td>1000001</td>", 1)
    must_reject(html, "Unreasonably high odds must be rejected")

def test_same_lane_rejected():
    html = make_fixture().replace("<td>2</td><td>3</td><td>123.0</td>", "<td>1</td><td>3</td><td>123.0</td>", 1)
    must_reject(html, "Repeated boat number in a ticket must be rejected")


def test_cached_odds_remain_available_during_refresh():
    """A stored verified response must not turn into 202 during an in-flight refresh."""
    key = ("20261027", "12", "1")
    params = {"hd": [key[0]], "jcd": [key[1]], "rno": [key[2]]}
    saved = {"ok": True, "odds": {"1-2-3": 123.0}, "fetched_at": "2026-10-27T00:00:00+00:00"}
    with server.LOCK:
        previous = server.CACHE.get(key)
        was_inflight = key in server.INFLIGHT
        server.CACHE[key] = (time.monotonic(), 200, saved)
        server.INFLIGHT.add(key)
    try:
        status, payload = server.get_odds(params)
        assert status == 200 and payload is saved, "Verified cached odds must take priority over in-flight status"
    finally:
        with server.LOCK:
            if previous is None:
                server.CACHE.pop(key, None)
            else:
                server.CACHE[key] = previous
            if not was_inflight:
                server.INFLIGHT.discard(key)

if __name__ == "__main__":
    test_complete_120()
    test_missing_cell_rejected()
    test_duplicate_combination_rejected()
    test_zero_odds_rejected()
    test_extreme_odds_rejected()
    test_same_lane_rejected()
    test_cached_odds_remain_available_during_refresh()
    print("Odds parser regression tests passed")
