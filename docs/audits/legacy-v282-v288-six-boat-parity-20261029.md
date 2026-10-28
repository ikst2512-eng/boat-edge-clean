# Old-site V282/V288 versus CLEAN six-boat regression: assertion review

Date: 2026-10-29. Sources: legacy main `tests/test_boat_edge_v282_exhibition_evidence.cjs`, `tests/test_boat_edge_v288_official_start_html.py`; CLEAN main `tests/site-regression.cjs`, after PR #210.

## V282 source visibility
- The old V282 test executes `BoatEdgeV223Source.inspect` using deliberately incomplete five-of-six fixture arrays for exhibition time, exhibition ST/entry, and original exhibition. It asserts these have status `unknown` (not `ok`).
- Completing all six valid entries makes selected flags `ok`, while third-party flags remain `unknown` absent provider evidence.
- A third-party provider may be marked available with source URL, timestamp, digest; its numerical agreement remains explicitly **unverified**.
- Null data must stay `unknown`.

CLEAN PR #210 verifies that production script still contains six-lane uniqueness and audited source/time gates. This is *source-presence validation*, not the execution of the same partial-coverage/third-party fixtures. Therefore **V282 parity is not proven**.

## V288 source HTML
- The old test extracts its official parser from the old `auto-update.yml`, parses archived official PRE_RESULT HTML, verifies six lanes and plausible exhibition times.
- Spoofed unrelated 6.x statistics and ambiguous duplicate exhibition tables must fail closed.
- Missing exhibition time and tilt cells must not be filled from neighboring columns.
- Start exhibition ST tokens such as `.06`, `F.02` and `-0.02` must be retained, with malformed values rejected; duplicate lanes invalid.
- Uses `BeautifulSoup` offline against archived input. It does not consume race results/payouts.

CLEAN's checked regression constrains source provenance and six-boat completeness in its UI. It does **not** establish that CLEAN's independent collector/parser rejects the same spoofed HTML or preserves all these ST tokens. **V288 parity is not proven**.

## Disposition

- Retain legacy V282 and V288 for evidence until the independent CLEAN collector is separately tested with equivalent fixtures and expected classifications.
- Do not reuse old parsing or duplicate old Actions blindly; CLEAN's independent feed architecture remains authoritative.
- Next action: identify CLEAN parser function(s) and fixture interface, add focused fail-closed tests for five-of-six, spoof table, missing cells, ST variants and source provenance as applicable; confirm CI and source snapshots.
- Do not change old repo, formal Fresh or immutable forecast evidence. This document does not authorize deletion.

Evidence: [PR #210](https://github.com/ikst2512-eng/boat-edge-clean/pull/210), [PR #208](https://github.com/ikst2512-eng/boat-edge-clean/pull/208).
