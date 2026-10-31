import json
from urllib.request import urlopen

BASE = "https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/"
RACES = ("202610310201", "202610310202")

def read(path):
    with urlopen(BASE + path, timeout=25) as response:
        return json.load(response)

records = []
for code in RACES:
    prediction = read("prospective_predictions/" + code + ".json")
    result = read("confirmed_results/" + code + ".json")
    assert prediction["race_code"] == result["race_code"] == code
    assert prediction["formal"] is False and prediction["scoring"] is False
    assert result["status"] == "confirmed"
    tickets = prediction["predictions"]
    assert len(tickets) == len(set(tickets)) == 10
    finish = "-".join(map(str, result["finish_order"]))
    records.append((code, tickets, finish))

for limit in (3, 5, 10):
    hits = sum(finish in tickets[:limit] for _, tickets, finish in records)
    print(f"RESEARCH_ONLY_TOP{limit}: {hits}/{len(records)} formal_scoring=false")
for code, tickets, finish in records:
    print(code, finish, tickets.index(finish) + 1 if finish in tickets else "outside_top10")
