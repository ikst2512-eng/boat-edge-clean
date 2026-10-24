"""Regression: site-reference/provisional snapshots can never enter formal Fresh."""
import json
from fresh_feed_builder import convert

def check():
    # Deliberately use the observed upstream *shape*, not any race outcome.
    provisional={
        "schema_version":"boat-edge-server-site-final-v123",
        "snapshot_window":"FINAL_15M",
        "race_key":"20261023-05-01",
        "prediction_kind":"SITE_REFERENCE_V122",
        "minutes_to_deadline":3.05,
        "mode_policy":"PROVISIONAL_V254_THIRD_TAIL10_FIXED_TOP7",
        "modes":{"hit":{"tickets":[{"combo":"1-2-3","p":17.4}]}},
        "guards":{"results_seen":False,"unlock":False,"scoring":False},
    }
    try:
        convert(json.dumps(provisional).encode(),"V1.21.20-NON1-B1-DUAL-SAFE")
    except (ValueError,TypeError,KeyError):
        pass
    else:
        raise AssertionError("provisional site snapshot wrongly accepted as formal v5")
    print("Provisional upstream snapshots remain excluded from formal Fresh")

if __name__=="__main__":
    check()
