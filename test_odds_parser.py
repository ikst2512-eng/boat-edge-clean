"""Offline regression test for the six-column, 120-combination official odds layout."""
from itertools import permutations
from html import escape
from server import parse_official_odds_table

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

if __name__ == "__main__":
    test_complete_120()
    test_missing_cell_rejected()
    print("Odds parser regression tests passed")
