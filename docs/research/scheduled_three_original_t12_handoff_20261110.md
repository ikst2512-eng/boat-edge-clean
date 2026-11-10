# Scheduled official three-original handoff (Draft, 2026-11-10)

Scope: **only the existing** `Research independent late preview evidence`
scheduled job (`.github/workflows/research-live-preview-evidence.yml`).
This document does not authorize main merging, production predictions,
a new scheduled workflow, or formal accuracy scoring.

## Why this change is necessary

Prior scheduled observations archived official `beforeinfo` for six boats
and 120 trifecta odds, but did not attempt a same-race **official racelist
original** in that same collection attempt. The #1694 / #1693 audits therefore
could not match all three original HTTP source bodies for the same race.
The official racecard collector and three-original independent auditor
**already exist in main**. This Draft reuses them; it does not clone a parser.

## Specific sequence

1. Retain the existing current-day schedule discovery and bounded maximum
   of two races (selection is a convenience, never an official deadline).
2. Capture and audit the original `beforeinfo` and `odds3t` pair, retaining
   all original statuses, error handling and immutable source filenames.
3. **If** the official `beforeinfo` deadline still leaves at least
   25 seconds ahead of T−12, call the existing
   `capture_official_racelist_receipt.capture` function, **even when the
   exhibition/odds pair is incomplete**. The official racecard may be
   published earlier than the exhibition. Save this original independently;
   the 18-second HTTP timeout is bounded and immutable names are preserved.
4. Only when the already-checked exhibition/odds pair is complete **and**
   the original racelist was received before the T−12 cutoff, call
   `audit_three_official_t12_originals.audit_three_originals` on the
   **same** three receipt directories. This existing auditor checks original
   hashes, race identity, six registrations, 120 odds,
   exhibition/entry distinction and per-source T−12 timestamps.
   The existing independent `audit_racelist_with_official_deadline`
   verifies stored racelist SHA, 6 distinct registration IDs, 6/6 agreement
   with the official beforeinfo original and receipt times **even if the
   exhibition is incomplete**. A validated early racelist + incomplete
   exhibition is reported as `racelist_verified_pair_incomplete`, never
   a verified triplet. Missing or mismatched IDs are rejected.
5. Any timeout, incomplete exhibition, invalid HTML/registration IDs,
   inconsistent source digest, or expired T−12 cutoff is reported separately.
   An official two-source success is **never** relabelled as failed or as a
   three-source success. The independent CSV capture and research archive
   remain ordered after the official attempt, as before.

The CLI's existing scheduled entrypoint opts into the third-original step.
The Python helper's default remains two-source-only for legacy callers.
No new workflow, cron schedule, dispatch, site, Render, GitHub publication,
or forecast data writes are introduced.

## Actual research validation on 2026-11-10 JST

[Live PR CI #42787319015](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42787319015)
ran the existing source code, including the independent registration parser,
and succeeded. The run collected **2 official racelist HTML originals and
2 official beforeinfo+odds120 pairs** for `202611100708` (Gamagori 8R)
and `202611101908` (Shimonoseki 8R). Independent audits verified **2/2
same-race six-registration matches before T−12**. However both beforeinfo
originals still had incomplete exhibition data and **zero** valid official
pair/triple source completions. In that run the report correctly showed
`verified_racelist_six_registration_matches=2` and
`complete_three_originals_before_t12=0`.

Earlier [PR CI #42786724704](https://github.com/ikst2512-eng/boat-edge-clean/actions/runs/42786724704)
was independently replayed from its downloaded original ZIP (artifact
#13749433042); all three file manifests matched the raw bytes for
Suminoe 7R and Gamagori 8R and the six racer identities matched. The
raw ZIP SHA and precise clocks are preserved in
`official_three_source_20261110_live_replay.md`. These are successful
**source-read-only PR experiments**, not repeated scheduled production runs.

## What it does **not** prove

Even a complete same-race three-source read-only audit is **not**
independent Git first-remote arrival evidence for a newly generated forecast,
proof the model consumed the official source before generation, proof of
final actual entry, or evidence of improved hit rate. All formal/forecast
flags remain false. Existing V2 forecasts generated before official receipt
may not be retroactively upgraded. No result/payout data is used in this
source-capture path.

Before any main merge, require exact-head CI, manual review by the official
source owner (#1694), scheduled live run artifact showing all three raw
bodies and their immutable manifests, source-timestamp review, and
independent #1693 eligible-model input consumption/first remote proof.
The #1699 owner must separately verify that GitHub schedule coverage is
actually sufficient; this change does not repair missed scheduled triggers.

## Tests (research-safe fixtures)

`python -m unittest discover -s tests -p 'test_capture_joint_preview_batch.py' -v`

Also run the pre-existing three-original audit and observation tests.
Negative controls cover too-late racelist receipt, insufficient time
to start, source failure, corrupt or mismatched audit flags,
and no unintended third-source request when disabled. Separate checks
prove an early racelist can be saved despite incomplete official exhibition
without invoking the three-source completion auditor.
No simulated success can count as an actual official HTTP observation.

Owner handoff: #1694 authoritative source audit; #1693 forward 300+300
evaluation; #1708 shared acceptance gate. **Draft only; main auto-merge
forbidden.**
