# Five-race P0 first Git-add and odds chronology receipt — 2026-11-04 JST

Read-only expansion from single race to the earliest five P0 legacy-only prediction race IDs from the pinned 2026-11-03 audit crosswalk. No source originals, live site, scoring, CI or workflows changed.

Legacy pinned tree SHA: `f38204105a979aa6ef5293d1b9cad854056faadd`. All five source JSON snapshots were refetched **at the identified Git-add commit**. Each commit's diff shows `data/site_prediction_snapshots/{race}.json` as a new file (`@@ -0,0`) and its blob SHA equals the indexed snapshot SHA at the pinned later tree.

| Race | Git-add commit | Git commit timestamp UTC | Snapshot blob SHA1 | Self-reported lead before cutoff | Observed odds sidecar |
| --- | --- | --- | --- | ---: | --- |
| `202610080103` | `1d06d01b5cae217f137e71a5a69e92c9ef7fb208` | 07:15:40 | `4758d57a765ee06c56a8f85680b7d600728677ca` | 6.33m | 404 at pinned tree; snapshot odds SHA256 null |
| `202610080104` | `0c631f193f0829f10625161a5b8e016cbfe12b96` | 07:36:49 | `93ff785f5039b0cb6ec616a01ef7480306233ac5` | 11.19m | file has 120 entries; fetched at 16:40:14 JST, **after forecast ~16:36:49 JST**; snapshot odds SHA256 null |
| `202610080105` | `f732faed17b72233240a22e63778521b79500cb7` | 08:06:42 | `e3fb2dd28f07b64511464e9b04fcae0fccc368bb` | 10.3m | file has 120 entries; fetched at 16:40:22 JST, before forecast ~17:06:42 JST; hash link not yet verified |
| `202610080106` | `eecc374eff6b965ad5cdcca21eba5976c0444a73` | 08:46:51 | `bfe4348f8de76d9a74ac83e07cd446e3c9b36cf1` | 1.16m | file has 120 entries; fetched at 17:44:34 JST, before forecast ~17:46:51 JST; hash link not yet verified |
| `202610080107` | `a36371ce87d823107171fcee690491e0798daf74` | 09:01:49 | `e0fa8f601ac33fba6c1b184a65a49f5a83f50a5f` | 15.18m | file has 120 entries; fetched at 17:44:44 JST, before forecast ~18:01:49 JST; hash link not yet verified |

**Interpretation:** These Git-add records support the historical source's presence as of the listed commits, NOT independently verified wall-clock delivery or formal forecast eligibility. The source's own declared lead times of 11.19, 10.3, 1.16 and 15.18 minutes should not be mistaken for a passed strict V229 2–10-minute window. Two are outside by a wide margin, and 10.3/11.19 exceed the upper limit. The legacy evaluation records declare `SITE_REFERENCE_POST_SETTLEMENT_ONLY_NOT_FORMAL_FRESH` for all four newly checked races. No formal Fresh promotion.

An odds JSON file with 120 keys is NOT a verified 120-odds predeadline market in the frozen model's receipt without: a same-race timestamp, source validity, original-source SHA match, unique ticket/value validation, and cutoff. In particular the **4R sidecar postdates the frozen forecast** and must not be used retroactively. 5R/6R/7R sidecars preceded forecast creation based on embedded timestamps, but source hash match is unverified. Source time and Git commit time have different trust levels.

Local handoff CSV: `boat_edge_first_git_proof_5r_20261104.csv`, SHA256 `6b6190c5574d2f50815e02051dba2d1081b9123aeceebef729cce25d536e805b`. It is NOT a backup of the original JSON bytes. No independent durable raw-byte archive / restore has been verified.

**Decision: DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**

## Additional byte-level odds SHA256 verification (2026-11-04 JST)

Using direct GitHub source-file text at pinned legacy SHA, re-encoded as UTF-8 bytes, a locally implemented SHA256 routine was first checked against standard ASCII `abc` vector (`ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`). The following *raw file byte* hashes were calculated; **all three differ** from the immutable snapshot's expected `odds_sha256`:

| Race | Computed SHA256 of tracked `site_odds` content | Frozen snapshot expected SHA256 | Result |
| --- | --- | --- | --- |
| 5R | `e88d1557c496f3e6d0155d3f097666f2e9f0954e07c254d0030792be93d549de` | `e49b68d44f27bc7cc22bc7f471a76b1372f97dbaa3925727359fe2406d28757c` | **MISMATCH** |
| 6R | `6e53cf35ba60d8e903268b51c4ed9602bdee70e0fa565491326ae73d02e7e112` | `cf6ac10fc6c11991c128a0f5eb5276cc3aae857de8bcf5812490e3c09a21fed2` | **MISMATCH** |
| 7R | `46a0f6c6606e1ca5b745f4f97643ed627bc0b358802b5bb279c9e7a33b7165fa` | `e8eee54b9dde1dc8da48e5de4b11b78893cf3d236aa94a7b8242ea35d7f2f151` | **MISMATCH** |

Independent checks: the same `data/site_odds/{race}.json` blob Git SHA1 is present already at **each forecast's own first Git-add commit**, and matches the later pinned-tree blob SHA1 (5R `95637302850009d287159c2ac9caf6ecba96c2d5`, 6R `499af20bff8743d4de9cc3d039e9981308cae106`, 7R `651dc71f5f21fb1a4450fa7c5b4e4e58a04e7a46`). Thus it is **not justified** to explain the mismatch as merely a later file mutation. It may be a distinct frozen earlier source or incorrect snapshot linkage; causal explanation **unverified**.

Checked expected SHA-named archival paths under `data/site_prediction_snapshots/odds_v214/` for 5R/6R/7R at the pinned tree: all three returned 404. That does not rule out another archive or an earlier Git object elsewhere. The only supported conclusion is **no byte-exact matching 120-way odds original found among checked paths**.

**Safety implication:** even with 120 entries, same-race keys, PRE_RESULT phase, and source timestamps before forecast creation, 5R–7R cannot be certified as odds-linked valid frozen predictions by their current raw source. This is not proof that those predictions are invalid or fabricated; it is an unresolved cryptographic provenance gap. Keep source data immutable, no formal promotion, no automatic repair.
