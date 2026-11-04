# First original ODDS bytes replicated off GitHub — 2026-11-04 JST

Issue #708/#329. This is an actual source-original-byte readback for **one** historical SITE-reference prediction's 120-combination odds; it does not authorize legacy writer shutdown or scoring/model migration.

## Fixed original source and exact-byte checks

- Race: **2026-10-08 Kiryu 5R**, `20261008-01-05`.
- Legacy pinned tree: `f38204105a979aa6ef5293d1b9cad854056faadd`; Git source `data/site_odds/20261008-01-05.json`.
- The byte content fetched via GitHub connector was restored as an exact **2,898-byte JSON file**, matching:
  - computed SHA256 `e49b68d44f27bc7cc22bc7f471a76b1372f97dbaa3925727359fe2406d28757c` — **MATCH to immutable snapshot `odds_sha256`**;
  - computed Git `blob {length}\0{bytes}` SHA1 `95637302850009d287159c2ac9caf6ecba96c2d5` — **MATCH to source Git blob**;
  - 120 **unique** valid `1..6` permutations and `PRE_RESULT_PURCHASE_ONLY` source schema/phase, result-not-seen flag.
- Initial forecast first-add Git commit `f732faed17b72233240a22e63778521b79500cb7`; source odds sidecar already present with same Git blob at that commit (verified earlier). Snapshot lead time **10.3 min** remains *outside* strict V229 2–10m; do not promote old SITE reference to formal Fresh.

## Actual independent provider preservation and recovery

- Exact odds bytes, JSON receipt and fail-closed offline `verify_legacy_odds_sample.py` were packaged into `boat_edge_legacy_original_odds_sample_20261104.zip`.
- ZIP SHA256 `d339ab5ffcd6fc4b01f7f0b6c57667f5aed79f2ea8897031ee1ad8e572a24159`.
- Uploaded as a **private** Google Drive ZIP into existing old evidence archive folder, [Drive copy](https://drive.google.com/file/d/1-0qxjKAk0F_mWILGyiWrrbeniRF0dLA5/view?usp=drivesdk) (folder: https://drive.google.com/drive/folders/1SbD5n2P5O3v3F0-g2iSU3zkdf-_w8cA7).
- Independently **downloaded this ZIP back from Drive**, checked ZIP SHA256 **MATCH** and executed `python verify_legacy_odds_sample.py <ZIP>` against the retrieved file: `PASS: exact odds original bytes=2898, SHA256 and Git blob SHA1, 120 unique odds`.
- Result: **OFF_GITHUB_ODDS_ORIGINAL_INDEPENDENT_READBACK = PASS for exactly one race**.

## Still blocked

- This ZIP contains one ODDS source; **it does not contain the original prediction snapshot** or all 1,125 P0 forecast originals, nor all original odds, exhibition/scratch receipts, results or formal Fresh proof.
- Google Drive original storage adds an independent provider copy, not guaranteed perpetual preservation. Source-of-truth Git first-add, no retrospective source edits, and privacy are retained.
- No existing production models, workflows, Pages, site UI, data rows, or source originals were altered.

**DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**
