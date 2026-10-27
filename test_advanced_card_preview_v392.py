"""V392 card-only, no-network prospective fixture regressions."""
from __future__ import annotations
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import advanced_card_preview_v392 as m

KEY = "20261015-14-01"
NOW = datetime(2026, 10, 14, 20, 0, tzinfo=m.JST)


def card(key=KEY, fetched=None):
    fetched = fetched or NOW
    return {
        "race_key": key, "meta": {
            "date": f"{key[:4]}-{key[4:6]}-{key[6:8]}",
            "venue_code": key[9:11], "venue": "鳴門",
            "race_no": int(key[-2:]), "deadline": "08:35",
            "phase": "PRE_RESULT", "results_seen": False,
            "unlock": False, "scoring": False,
        },
        "source_audit": {"race_card": {
            "status": "ok", "fetched_at": fetched.isoformat(), "sha256": "a"*64}},
        "racers": [{
            "lane": i, "registration_no": str(5000+i), "name": "選手",
            "class": "A1" if i == 1 else "B1", "avg_st": 0.14 + i/100,
            "national": {"win_rate": 7.8-i*.5},
            "local": {"win_rate": 5.0},
            "motor": {"quinella_rate": 30+i}, "raw_text": str(i),
        } for i in range(1, 7)]
    }


def save(root, path, obj):
    p = root/path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return p


class FakeResponse:
    status_code = 200
    apparent_encoding = "utf-8"
    encoding = "utf-8"
    def __init__(self, url, content):
        self.url = url
        self.content = content.encode("utf-8")
        self.text = content


def racelist_html():
    clocks = ["08:35", "09:01", "09:27", "09:53", "10:21", "10:52",
              "11:20", "11:49", "12:18", "12:47", "13:16", "13:45"]
    head = "<tr><td>締切予定時刻 " + " ".join(clocks) + "</td></tr>"
    rows = "".join(
        "<tr><td>" + str(i) + " " + str(5000+i) +
        " / A1 <a>選手</a> 山口/山口 27歳/52.0kg F0 L0 0.17 "
        "6.49 44.95 67.89 0.00 0.00 0.00 54 33.67 50.00 28 38.38 50.51"
        "</td></tr>" for i in range(1, 7)
    )
    return "<html><title>出走表</title><table>"+head+rows+"</table></html>"


class FakeSession:
    def get(self, url, timeout, allow_redirects):
        if allow_redirects:
            raise AssertionError("REDIRECTS_FORBIDDEN")
        if "race/index?" in url:
            html = ('<a href="/owpc/pc/race/racelist?hd=20261015&jcd=14&rno=1">'
                    '鳴門</a>')
        elif "race/racelist?" in url:
            html = racelist_html()
        else:
            raise AssertionError("NON_RACELIST_ENDPOINT_" + url)
        return FakeResponse(url, html)


class V392Tests(unittest.TestCase):
    def test_full_120_ranks_and_top_prefixes_without_odds_or_result(self):
        d = card()
        p = m.make_preview(d, NOW)
        self.assertEqual(p["schema"], m.SCHEMA)
        self.assertEqual(p["model_id"], m.MODEL)
        self.assertEqual(p["prediction_kind"], "EARLY_CARD_ONLY_REFERENCE_NOT_FINAL")
        self.assertEqual(len(p["ranked_120"]), 120)
        self.assertEqual(len({x["combo"] for x in p["ranked_120"]}), 120)
        self.assertEqual([x["rank"] for x in p["ranked_120"]], list(range(1, 121)))
        self.assertEqual(p["top3"], p["top10"][:3])
        self.assertEqual(p["top5"], p["top10"][:5])
        self.assertEqual(p["head_candidate"], int(p["top10"][0][0]))
        self.assertEqual(p["racer_inputs_by_lane"][0][1], "5001")
        self.assertFalse(p["score_is_calibrated_probability"])
        self.assertFalse(p["odds_used"])
        self.assertIsNone(p["stake_yen"])
        self.assertFalse(p["guards"]["results_seen"])
        self.assertFalse(p["formal_fresh_claim"])


if __name__ == '__main__':
    unittest.main()
