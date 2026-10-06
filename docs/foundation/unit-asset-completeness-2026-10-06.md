# Unit Asset Completeness Gate — 2026-10-06

Status: **in progress; 882/882 not yet claimed**.

## What is now proven

1. JP 15.7.1 locally contains the complete 882-unit definition/name catalog.
2. Historical server manifests preserve many old collaboration textures and animation/model filenames.
3. The catalog number and asset stem are offset by one: `asset_id = unit_no - 1`.
4. Normal/Evolved/True/Ultra asset suffixes are `f/c/s/u`.
5. The current server route is operational: Actions run `37417655457` downloaded lane 34 with HTTP 206 and exactly 15,366,935 bytes.
6. The current X lane exposed five manifests and combined with the historical archive to produce a metadata index of 93 manifests / 33,780 entries.
7. The repository now has a metadata-only per-form completeness auditor and synthetic tests.

## 15.7.1 late download lanes

From the user-owned `split_InstallPack.apk`:

- `download_33.tsv`: `WImageDataServer.list` + `WImageDataServer.pack` (79,788,272-byte pack).
- `download_34.tsv`: X ImageData/Image/Map/Number/Unit server families.
- `XImageDataServer.pack` is zero bytes in this lane; X Image/Map/Number/Unit packs are non-empty.

The current X ZIP fetch used the TBCML-compatible URL/signing logic pinned at public TBCML commit `9bb62d99b2b1e0da113c5592685a47f720bf7a4d`.

## Corrected collaboration examples

Catalog numbering is one-based; asset filenames are zero-based.

- 鹿目まどか: catalog unit 289 → asset 288.
- 暁美ほむら: catalog unit 290 → asset 289.
- セイバー: catalog unit 363 → asset 362.
- Evangelion catalog 403–415 → assets 402–414.
- catalog 488 → asset 487.
- Street Fighter catalog 511 → asset 510.
- 初音ミク catalog 536 → asset 535.
- catalog 552 → asset 551.
- Ranma catalog 597 → asset 596.
- catalog 704 / 711 → assets 703 / 710.
- catalog 815 → asset 814.

This correction supersedes earlier filename probes that searched the catalog number directly as the asset stem.

## Audit gate

For each stat-backed form, the current strict baseline checks:

- battle sheet PNG;
- `.imgcut`;
- `.mamodel`;
- standard playable motions `00..03.maanim`;
- deploy icon for playable units;
- egg/alternate-art substitution when declared by `unitbuy.csv`;
- source/family provenance for every matched filename.

Gacha art and evolution banners are reported but do not universally gate battle playability.

## Current blocker to the final declaration

The route and audit machinery now exist, but the verified local export and the combined server manifest index still need to be run together and the exact completeness report preserved. Until that result is generated and reviewed, the project must not state `882 / 882 COMPLETE`.

Original APKs, pack bodies, textures, animation payloads, and downloaded proprietary assets remain outside Git.