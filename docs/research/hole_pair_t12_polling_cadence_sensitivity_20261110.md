# 2026-11-10 — per-race T−12 polling sensitivity on REAL 150-source cutoffs (nonformal)

**Study type:** offline *counterfactual* calculations on actual Git-source JSON cutoffs, **NOT** an official-source readiness measurement or actual scheduling, network dispatch, candidate freeze, external receipt, race result inspection, or model accuracy analysis.

## Precisely anchored input and explicit assumptions

- Exact main commit `c4d39245cbc96b6c680585a68c3b9adf6ddeb921`; original Git forecast tree `f8765fdbd105c3673cde76fe9df80f10b0ad1269`; **150/150** verified forecast Git blob SHA1 + raw SHA256 in the preceding [full source audit](hole_pair_nov10_150_original_source_readiness_20261110.md). Original forecast records contain `beforeinfo=optional_not_in_snapshot` in **150/150** cases.
- `research/hole_pair_t12_polling_cadence_simulator.py` consumes the **actual 150-row JSON output** from the existing source-gate audit (does not reimplement raw source reads). It validates a closed result-blind schema, exact 150-race roster aggregate consistency, local deadline-minus-12 arithmetic, same-day JST, Git-original SHA formats, local generation chronology, and permanently false official/receipt/formal claims before simulating any clock windows.
- The common **unverified first Git-source-sighting hint** is `2026-11-10T07:44:30+09:00`, anchored to one main commit containing the original same Git forecast tree. A Git commit timestamp is **not** an independently authenticated first external receipt of source, and it says nothing about actual availability of complete official inputs.
- The simulator **pretends** complete official six-boat exhibition, odds 120/120, and racelist arrive `source_lead_seconds` **before the file-declared T−12**; no such arrival is evidenced. Each hypothetical source-to-candidate-to-server workflow requires a further **30 seconds processing/network reserve**, which is a scenario parameter, **not measured latency**. Poll slots are aligned to JST midnight plus a chosen zero- or 45-second phase offset. Real production performance, official cutoff, and actual server receipt may differ.
- The four scenarios are: 180s official-input lead with phase 0; 120s lead phase 0; 60s lead phase 0; **60s lead with phase 45s**. Each calculates potential schedule tick existence for exactly the original 150 race codes with cadence 1, 2, 3, 5, 10, 15 minutes. These figures are **clock-only hypothetical opportunities**, not successfully fetched official sources or prospective accepted candidate records.

## Actual offline calculation against the 150 original race cutoff fields

| Hypothetical official-input readiness before declared T−12 | 1m | 2m | 3m | 5m | 10m | 15m |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 180 seconds before, zero-second phase | **150** | **150** | **150** | 88 | 51 | 30 |
| 120 seconds before, zero-second phase | **150** | **150** | 105 | 59 | 34 | 21 |
| 60 seconds before, zero-second phase | **150** | 83 | 60 | 27 | 16 | 11 |
| 60 seconds before, **45-second phase shift** | **0** | 0 | 0 | 0 | 0 | 0 |

These numbers are reproduced from **actual CI**, not invented by testing a miniature sample. **Real Git source inputs are authentic, but official-input lead/phase/latency are all assumptions.** In particular, a one-minute polling cadence passing 150/150 with fortuitously aligned minute boundaries can lose **all 150** under a 45-second phase shift and only one-minute official-input lead. This explicitly refutes the unsafe interpretation that "one minute polling guarantees the T−12 capture." The safe architecture choice is to require **source-readiness-driven per-race low-latency triggering**, *with* a separately audited retriable backstop; even event-driven behavior cannot guarantee formal proof until the independent accepted first write and full source inputs are externally proven.

## What was actually implemented, not deployed

- New result-blind `research/hole_pair_t12_polling_cadence_simulator.py` consumes **only** the existing audited source JSON and optional **synthetic** lead/reserve/phase parameters. No imports of results, confirmed winners, main write methods, Cloudflare APIs, or live timers; it only writes to a unique untracked audit-report output when invoked manually in PR CI.
- New `research/test_hole_pair_t12_polling_cadence_simulator.py`: **14 deterministic offline tests** for varied polling periods, source-sighting after cutoff, phase jitter, wrong/mutated original digests, duplicate/reordered race IDs, false official fields, forged formal status, invalid hypothetical parameters, and empty-source day. A valid signature, declared cutoff or early generation alone is **never** allowed to set formal cohort counts.
- The **existing PR-only** `.github/workflows/hole-future-pair-precommit.yml` runs tests then replays the *real* pinned 150 original Git blobs, runs four lead/phase simulations, validates **zero formal eligibility** and uploads five JSON files together in existing `hole-pair-actual-nov10-main-source-audit-nonformal` artifact: one original source audit and four counterfactual reports. **No schedule, manual dispatch, Cloudflare Worker deployment or research candidate-frozen artifact was initiated.**
- [Verified GitHub Actions #42785482331](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42785482331) **SUCCESS** at implementation commit `b062a9035a9cce8694881112c218b3a3a3cc4af4`, all new **14/14 tests passed**, actual 150-blob replay and 4 simulations passed, candidate freeze/upload **SKIPPED**.

## Engineering handoff: staged event-driven design, approval only

Any real integration **requires separate manual architecture + security approval**, not changes to the existing #1702 manual gate merely based on hypothetical scheduling results:

1. A **canonical official race universe** must be externally archived; avoid cherry-picking, dropped races, cancellation/backfill ambiguity or counting source snapshot files as complete official schedule.
2. Per race, obtain original racelist, all six genuine beforeinfo/exhibition boats, and **all 120 distinct official trifecta odds**, with independently attributable original reception timestamps before **the true official** cutoff. Do not count results or already closed races. Until every source is complete, the race remains pending/missing.
3. Generate the locked three-arm hole-pair candidate **only after those inputs are actually consumed** by the generating model. The current early four-mode source has `beforeinfo=optional_not_in_snapshot` and cannot be converted into a source-complete model by updating metadata flags.
4. Immediately send exact candidate bytes to an independently controlled, *append-only and atomic per-race first-write* service with independently attested server time, fixed trusted signing key, unique race digest and conflict quarantine; idempotent exact retries may return the original receipt, but different bytes/first-times are quarantined. Do not let a later retry retroactively create a pre-cutoff first receipt.
5. Use an event-driven trigger when the final required original becomes available, with bounded retry/backoff and an observable monitoring backstop. A fixed 1/5/15-minute polling schedule may fail when availability is close to T−12; proposed trigger frequency, latency, token/API budget, weather/odds freshness and outage handling need measurements **before** deployment. Source/event traces must preserve per-race proof chain and independent key custody.
6. Only after immutable external proofs and official schedule reconciliation may the prospective protocol's first **300** pilot and subsequent untouched **300** confirmation races be admitted. No outcome knowledge before prior eligibility lock; no automatic model/main promotion.

**Strict current state:** formally eligible `0/300 + 0/300`, source-complete real independent first receipts established by these tests `0`, no demonstrated prediction improvement. #1685 is Draft; #1702 requires independent human review and remains unmerged, #1701 is closed/unmerged. **main, production predictor, Top1/3/5/10, UI, Render, Cloudflare, original frozen research and upstream collectors unchanged.**
