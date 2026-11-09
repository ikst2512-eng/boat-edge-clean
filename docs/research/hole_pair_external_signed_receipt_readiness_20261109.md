# 2026-11-09: external signed first-receipt authenticity READINESS (nonformal)

**Status: research Draft PR #1685, not deployed, not on main, no workflow dispatch, no production or model change, no signing key released or committed.**

## The missing link, not another D1 receiver

The pre-existing `research/hole_pair_first_receipt_worker.mjs` + D1 SQL prototype validates the candidate payload and enforces a **per-race SQLite first insert** in offline simulations. Its JSON response nevertheless is **unsigned and self-reported**: a forged `first_received_at_utc` or an independently uncontrolled D1 operator can pretend first receipt occurred earlier. The existing `research/hole_pair_d1_receipt_chain_audit.py` correctly reports internal timing consistency only and never promotes a candidate.

New `research/hole_pair_signed_first_receipt_audit.mjs` is a **separate, offline research-only Ed25519 verifier**, not a server/receiver and not an official clock. It imports the **existing pinned Worker candidate validator** (no new ticket-selection logic), binds a detached Ed25519 signature to:

- the *exact canonical original frozen candidate SHA256*, 12-digit race ID, declared T−12 and a claimed first receiver timestamp, with strict UTC millisecond spelling, candidate finish-before-receipt and more than two seconds cutoff margin;
- the claimed external witness identity, key ID, immutable receipt ID and first-write assertion under a domain-separated, fixed canonical signed JSON schema;
- a public Ed25519 key supplied separately from the signed statement, whose SPKI SHA256 must equal an explicitly pinned fingerprint supplied through the verifier's trust configuration. Arbitrary in-envelope keys, extra `formal` flags, foreign race IDs or changed candidate bytes are rejected.

**Important: a caller-supplied key, even pinned by this function, is not proof of independent custody.** An operator could generate their own key, sign backdated claims and pass pure signature verification. The module therefore always outputs `independent_key_custody_verified=false`, `trusted_receiver_first_write_and_append_only_proven=false`, `accepted_time_externally_attested=false`, `official_t12_complete_verified=false`, `formally_eligible=false`, `formal=false`, and `production_promotion_allowed=false`. There is **no code path** that elevates signature verification into eligibility or model improvement.

The batch audit refuses orphan or duplicate race IDs, and quarantines contradictory signed first-write IDs or timestamps for one race instead of using whichever message looks earlier. Duplicate *identical* signed claims never create a second observation. Signing is never performed by the production research module; test-generated Ed25519 private keys are **ephemeral test-only** and are not persisted, bundled, shipped or deployed.

## Test evidence

- New module `research/hole_pair_signed_first_receipt_audit.mjs`.
- New `research/test_hole_pair_signed_first_receipt_audit.mjs`, **16 synthetic tests** for mathematical verification under a supplied key and negative cases: forged statement, altered candidate hash/ticket, different public key or fingerprint, inserted result/formal fields, altered time/cutoff, same-race contradictory receipts, repeated identical receipts, missing receipts, orphan/duplicate race, invalid trust anchor.
- The **existing PR-only** `.github/workflows/hole-future-pair-precommit.yml` now includes these files in `pull_request.paths` and runs `node --test research/test_hole_pair_signed_first_receipt_audit.mjs`. No new scheduled workflow, capture trigger, D1 secret or GitHub write permission was added.
- Exact code-head [GitHub Actions #42622410760](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42622410760) **SUCCESS**, new **16/16 passed**, existing D1/SQLite/source roster/cross-run/gateway/selector tests also passed. Actual candidate freeze and candidate ZIP upload both **SKIPPED**. Only existing `hole-future-pair-precommit-readiness` audit artifact was created.

## Formal independent receipt acceptance still requires external work

A formal first-acceptance claim would still require **outside this Draft**, in a separately approved evidence architecture:

1. A **real independent recipient** with independently audited signing-key generation/custody, pinned public-key fingerprint and rotation/compromise rules; not a signer controlled by the model/collector or a user-supplied JSON flag.
2. A verifiably first-accepted **append-only race-ID / exact candidate digest entry**, independent authoritative timestamp and non-mutable retention/replay, with real concurrent HTTP/D1/outage/retry and conflicting-write tests. This draft verifies a signature over *claims*, not that a real service made those true or that any external log exists.
3. Same-race BOAT RACE original official racelist and fully ready beforeinfo/exhibition for all **six boats**, all **120 distinct** original trifecta odds, actual official deadline and independently evidenced pre-T−12 source arrival; the **forecast must be generated after those originals**, then frozen and independently remotely accepted before the genuine cutoff. These originals are independently owned by audit Draft #1694 and cannot be fabricated by this verifier.
4. A full day/schedule denominator, first immutable candidate cross-run quarantine, unaffected locked selector and unique first eligible **300 pilot** + subsequent untouched **300 confirmation** evaluation, paired Top10 exact-hit differences, exact McNemar test with Holm correction and explicit human approval.

**Current release decision: HOLD.** Formal pilot **0/300**, untouched confirmation **0/300**; original Nov5 106 and Nov6/7 102 shadow comparisons stay exploratory. #1702 is still a separate unmerged/manual-review-only gateway, not wired to this verifier or to deployed D1. #1701 should not be merged with #1702. No main auto merge, production-model/UI, official collector, Render, Cloudflare, deployment, real receiver, or first accepted candidate was created in this change.

## Across-race and across-batch global receipt-ID quarantine (additional research, still NONFORMAL)

**Specific vulnerability addressed:** The initial verifier checked contradictory immutable receipt IDs *within one race*, but did not catch an identical claimed receipt ID re-used across **different race IDs**. A signature can be valid for each record while the issuer falsely claims the same globally immutable first insertion identity for both. It also lacked a cross-batch conflict report for signed receipts (separate from the existing original-manifest cross-batch audit).

- `auditBatch()` now identifies the same claimed receipt ID across distinct race codes and marks **all affected rows** as `signed_receipt_id_reused_across_races_quarantined`. Existing Ed25519/Top5/source-frozen checks remain unchanged.
- New `auditAcrossBatches()` accepts at most 40 caller-supplied research batches (each `{records,envelopes}`) and at most 5,000 candidate observations. It reuses `auditBatch()` and `auditOne()` to validate signatures, binds exact candidate SHA256, and quarantines same-race candidate-byte mutations, contradictory claimed receipt IDs or claimed first times across batches, and cross-race recycled receipt IDs. Identical repeats do **not** increase the distinct-race count. It never chooses an earlier-looking claim using untrusted run order/timestamps.
- Batches and any purported GitHub run IDs remain **caller-supplied**, not independently authenticated: this pure verifier cannot certify first receipt or adjudicate a real append-only service. Existing `hole_pair_cross_batch_roster.py` handles original-manifest run provenance separately; it is not replaced by these tests.

**Test evidence:** Eleven new synthetic adverse tests cover reused signed receipt IDs across different races; legitimate distinct IDs; identical candidate repeats; mutated candidate bytes; changed claimed first clock/receipt ID across runs; absent then signed receipt; invalid/orphan inputs and bounds. [CI #42623372227](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42623372227) **SUCCESS**, `27/27` total signed-receipt tests passed, alongside existing research checks. Candidate-freeze and candidate artifact upload were **SKIPPED** on that PR event. Code head was `c37665cfb99bfffe94f489e92f5b320da99d2eff`.

**Nonformal boundary:** A self-controlled signing key can still attest a fictitious clock. No externally independently managed signing key, trusted server first-insert log, signed independent timestamp, official real T−12 six-boat originals/120 unique odds, whole-day schedule census or model consumption evidence was acquired. `formally_eligible=0`, `formal=false`, `production_promotion_allowed=false` remain mandatory. Historic Nov5–8 candidates cannot be rebranded as prospective.

**Status:** HOLD. Draft #1685 and preferred unmerged Draft #1702 unchanged at runtime; competing #1701 is closed without merging. No main/Render/Cloudflare/D1, UI, selector or Top5/Top10 production change. Formal pilot 0/300 and untouched confirmation 0/300.
