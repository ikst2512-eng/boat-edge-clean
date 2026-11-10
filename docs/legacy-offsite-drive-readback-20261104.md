# Independent Google Drive readback receipts — legacy evidence (2026-11-04 JST)

## Scope and method

The old site and both GitHub repositories' production original files are untouched. Historical *GitHub Actions artifact ZIP bytes* were copied into a newly created private Google Drive folder and downloaded **back from Google Drive**. Python `hashlib.sha256` was used on the independently retrieved ZIP file bytes. All three verified against the original GitHub artifact digest, and `zipfile.ZipFile.testzip()` returned no bad members.

**Drive folder**: https://drive.google.com/drive/folders/1SbD5n2P5O3v3F0-g2iSU3zkdf-_w8cA7

| Source artifact/run | Actual independent Drive copy | Bytes read back | SHA256 compared with source | ZIP internal check |
| --- | --- | ---: | --- | --- |
| Result 412 / run `40936953310`, artifact `12924304439` | [result412](https://drive.google.com/file/d/12J21YovAdPKB8pFYyTZMgRir-hOiM28g/view?usp=drivesdk) | 495430 | `9460f06cc712a87756ef4f54feb0612d63c812562b6486be12491e48be10e216` **MATCH** | PASS |
| Result 292 / run `40739572811`, artifact `12838409473` | [result292](https://drive.google.com/file/d/1JmzvxOY8ZKFSE6juH-MCo80DKMMz3aFW/view?usp=drivesdk) | 125089 | `755b694e13665ab7d66f7a2e0d03e2d47c4bf9c630025fc2215ef8cfb7fa3814` **MATCH** | PASS |
| Historical crosswalk metadata / run `41556670332`, artifact `13194783484` | [crosswalk](https://drive.google.com/file/d/1nxIy8XU9OzRpXeUa-A9nav67yHL4egz6/view?usp=drivesdk) | 673255 | `0823d71201fc51ddb9d08021a557f469bd4acbb2980205a0e916c1159aad7831` **MATCH** | PASS |

Google Drive metadata returned `shared=false` and an owner-only user permission on the result412 file when checked. No explicit public sharing permission was granted to any archive. Drive storage is a separate external provider from GitHub Actions; this is an **actual independent off-service ZIP save and retrievable byte-identical readback for exactly these three archives**. The archived 412 original result JSON members were previously individually compared to source SHA256 and Git blob SHA1 (412/412), and 292 of them overlapped the older archive exactly.

## Strict limits

- This **does not back up all 1,125 P0 historical original prediction snapshots**. The crosswalk includes indexed **metadata**, *not* 1,125 original snapshot/odds raw files.
- The 412/292 artifacts are **result-only original bytes**; they do not prove all 4,143 legacy race-key source categories have been preserved.
- A source ZIP digest match proves the Drive-restored ZIP matches the audited source ZIP; it does not imply BOAT RACE independent official payout verification.
- Drive persistence and access are under the user's Drive account. No service can guarantee perpetual retention against future account changes or file deletion; periodic backup audit and independent custody should be maintained.
- Before retirement: archive remaining forecasts, odds, pre-result receipts, formal Fresh, first-add provenance, missing 46 odds hashes, unresolved data, Pages dependencies and rollback. Review live main changes before merging PR.

**State: RESULT_ORIGINAL_412_DRIVE_RESTORED = PASS; 292_HISTORY_ARCHIVE_DRIVE_RESTORED = PASS; CROSSWALK_METADATA_DRIVE_RESTORED = PASS; P0_FORECAST_BACKUP = NOT_COMPLETE; DELETE_BLOCKED / LEGACY_WRITER_STOP_BLOCKED.**
