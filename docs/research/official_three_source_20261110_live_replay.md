# 2026-11-10 JST — actual archived three-source HTTP observations (not formal)

**Source:** [GitHub Actions PR run #42786724704](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42786724704),
[artifact #13749433042](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42786724704/artifacts/13749433042).
This run executed the opt-in racelist extension under Draft #1713.
It is a `pull_request` event, **not** proof that scheduled GitHub Cron runs
are reliable or that the new code is in main.

## Independent local ZIP recheck

The downloaded ZIP's SHA256 equals the GitHub-advertised digest
`7eddf4704635613f7d8cb18a03f07bcc1f9037efafb52ee26a3723b333a30354`.
All 28 ZIP entries pass CRC. For both races, raw official `racelist.html`,
`beforeinfo.json`, and `original.html` independently match the SHA256
and byte-length recorded in their respective immutable `manifest.json`.
The existing six-lane, anchored racer-row parsing contract was independently
applied to the ZIP's original racelist bytes and compared against six
`teiinfolist` registration numbers from the archived official beforeinfo:

| Race code / venue | Card HTTP completed JST | Beforeinfo HTTP completed | Odds120 HTTP completed | 6 registration IDs | Exhibition time/ST |
|---|---|---|---|---|---|
| `202611101207` / Suminoe 7R | 17:58:23.209880 | 17:58:03.609592 | 17:58:13.839263 | **6/6 match, 6 distinct** | **0/6, 0 start rows** |
| `202611100708` / Gamagori 8R | 17:58:53.177070 | 17:58:33.648353 | 17:58:42.838438 | **6/6 match, 6 distinct** | **0/6, 0 start rows** |

Exact six registrations by card **and** official beforeinfo:

- Suminoe 7R boats 1–6: 4205 / 4290 / 4024 / 4831 / 4908 / 4573.
- Gamagori 8R boats 1–6: 5104 / 3692 / 5259 / 4064 / 4012 / 5405.

The official deadlines from archived beforeinfo were 18:13 JST (T−12
18:01) and 18:23 JST (T−12 18:11), respectively. All three HTTP completions
were before those cutoffs; valid 120 unique trifecta odds were re-parsed in
the existing pair audit. However the original official beforeinfo
**contained no complete exhibition/ST information** when received.

Therefore `complete_pairs_before_t12=0`,
`complete_three_originals_before_t12=0`, **formal candidates=0**,
and no predictions were generated or promoted from this observation.
The newly connected independent racelist *identity* recheck is not a
complete official three-original preflight and must remain separate from
final actual entry, model consumption, first remote forecast receipt and
future independent Top1/3/5/10 accuracy validation.

## Next acceptance gates

1. The revised scheduled capture path must reproduce the official **six
   exhibition times + six valid start entries** alongside a matching
   racelist and odds120 before the *same* race's T−12 cutoff.
2. The existing #1694 auditor must independently replay the raw bytes and
   time provenance; Git initial receipt of a **new forecast generated after
   the source receipts and before T−12** needs separate proof.
3. #1693 prospective 300+300 evaluation may only start counting when its
   preregistered candidate is truly eligible. Past V2 original predictions
   cannot be rewritten as if they used these source bytes.
4. #1699 should independently audit actual schedule-event coverage. Do not
   claim background collection is restored on this single successful PR run.

**No main merge, production selector/model, saved forecast, Render, Pages,
Cron creation or formal validation in this study.**
