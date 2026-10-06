# Kneekura-WhiteNyankocats

PC-capable, offline-first Battle Cats compatibility sandbox for personal research and custom content.

The project is designed around two goals:

1. Reconstruct the familiar mobile UI/battle experience from locally owned game data without modifying the installed Android game.
2. Allow Kneekura custom units and sandbox features to coexist with imported content through a separate local runtime.

## Safety / repository boundary

Original APKs, extracted assets, audio, images, `.pack/.list` payloads, and device exports stay outside Git. See `.gitignore`.

The Android game and its save are read-only inputs. Kneekura uses its own local save/profile.

## Current tooling

Generate a metadata-only inventory from an export ZIP, direct APK, or extracted directory:

```bash
python tools/inventory_android_export.py PATH_TO_EXPORT \
  --output reports/private/android-export
```

For the current 2026-10-06 draft release export, the expected SHA-256 is:

```text
38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56
```

So a local verification run can use:

```bash
python tools/inventory_android_export.py nyanko_battlecats_2026-10-06.zip \
  --expect-sha256 38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56 \
  --output reports/private/android-export
```

The generated report contains hashes, paths, sizes, extension counts, and candidate categories only. It does not copy game asset bytes into the report.

Install the catalog-import tooling dependency:

```bash
python -m pip install -r requirements-tooling.txt
```

Build the local unit catalog directly from the device export:

```bash
python -m tools.import_battlecats_catalog nyanko_battlecats_2026-10-06.zip \
  --expect-sha256 38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56 \
  --output reports/private/unit-catalog.json
```

The current JP 15.7.1 export is expected to produce 882 consecutive unit IDs. The catalog keeps raw stat columns and localization rows independently, records provenance/hash data for every decoded source entry, and never writes decrypted assets back into the APK.

Visual/animation completeness is a separate layer: historical content may depend on downloaded `*Server.pack` shards that were not present in the standard-ADB export. Current work has now proven the 15.7.1 X server lane can be downloaded through the public TBCML-compatible route and has added a metadata-only 882-unit audit tool.

Important ID rule: catalog unit numbers are one-based while visual asset stems are zero-based, so `unit289.csv` / 鹿目まどか maps to asset stem `288`.

Run the local completeness audit once a metadata-only server manifest index is available:

```bash
python -m tools.audit_unit_assets nyanko_battlecats_2026-10-06.zip \\
  --server-index reports/private/server-manifest-index.json \\
  --expect-sha256 38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56 \\
  --output reports/private/unit-asset-completeness.json
```

The project-development gate remains closed until the report proves the required unit assets are complete; no original game asset bytes are committed.

## Design source of truth

- `docs/architecture/current-design.md`
- `docs/architecture/runtime-contracts.md`
- `docs/foundation/README.md`
- `docs/foundation/release-access-2026-10-06.md`
- `docs/foundation/android-export-15.7.1.md`

The exact original logical canvas size, simulation tick rate, and internal data meanings remain evidence-driven until measured.