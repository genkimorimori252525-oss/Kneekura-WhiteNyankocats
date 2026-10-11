# Kneekura-WhiteNyankocats

**[START HERE — CURRENT.md](CURRENT.md)** is the **only required design entry point**. It gives the source-of-truth order and links to the [active four-feature implementation plan](docs/roadmap/2026-10-09-original-battle-cats-delivery.md). Do not restart level-zero planning by independently reading all `docs/` files; past materials are scoped technical references.

## Important — User-confirmed product identity (2026-10-09)

**The owner wants the genuine gameplay experience of PONOS's にゃんこ大戦争 (The Battle Cats), not a lookalike cat game.** The complete offline environment and Kneekura customization must retain original game UI/scene transitions, battles, characters, assets and animations, stages, gacha and progression. Neither a runnable simplified Android prototype nor a network-disconnected mock game fulfills the request.

**[Authoritative PRODUCT_IDENTITY.md](PRODUCT_IDENTITY.md)** (owner's non-negotiable acceptance contract), **[product fidelity + offline release gates](docs/architecture/product-identity-gates.json)**.

**Current status:** the small independent Java Android `app/` ("Stage Fidelity Alpha") is strictly a *research harness*, **not the actual Battle Cats game** or an owner-ready full 1.01 update. Some prior replies mistakenly presented the harness as playable replacement. Do not repeat or recommend it as one. The preferred research direction is preserving as much original JP15.7.1 game engine/UI and behavior as safely possible while establishing verified complete offline independence. A separate engine remains research-only until original-game parity is demonstrated and the owner approves it.

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

The real JP 15.7.1 audit now reports **879/882 strict catalog rows complete**. The three residual rows are explained nonstandard cases (one documented single-form cheat unit plus two JP placeholder/regional slots), so the **JP reconstruction assessment is GO** while the raw strict number intentionally remains 879/882. No original game asset bytes are committed.

## Design source of truth — single current index

1. [CURRENT.md](CURRENT.md) — **one first-read / authoritative reference order and active task**.
2. [PRODUCT_IDENTITY.md](PRODUCT_IDENTITY.md) — owner non-negotiable actual Battle Cats experience.
3. [Active implementation roadmap](docs/roadmap/2026-10-09-original-battle-cats-delivery.md) — level caps, Madoka, Godzilla first form, strict offline (concurrent).

All other docs (older "current-design", design-philosophy, Phase-C, Post-EoC, harness, evidence) are historical or task-specific evidence. They do **not** override the above. Reference files only when the concrete implementation requires them.

## Android playable-stage checkpoint

The Android runtime now has a data-driven stage path in addition to the 882-unit/MAX-profile importer.

Direct inspection of the verified JP 15.7.1 InstallPack establishes:

- DataLocal: 8,955 entries.
- Concrete supported stage-definition files in DataLocal: 6,355.
- Stories of Legend (RN): 324 stage files.
- Uncanny Legends (RNA): 286.
- Zero Legends (RND): 217.
- Regular/special event (RS): 1,215.
- Collaboration (RC): 847.
- Collaboration gauntlet (RCA): 459.
- Gauntlet (RA): 1,147.
- Tower (RV): 260.
- Main-story Into the Future (W): 144 and Cats of the Cosmos (Space): 146, plus 57 numeric main-story stage files.

Map_option.csv in the same exact export retains named Crazed/Manic maps and historical collaboration maps, including Madoka Magica, Evangelion, Fate/聖杯戦争, Hatsune Miku, Ranma 1/2 and Street Fighter entries.

The Android importer reads exact stage width/base HP, enemy spawn ids/counts/timing, base-HP triggers, boss flags and magnification into a local StageDefinition catalog. The current 0.2 stage alpha can select one of those imported definitions and enter a primitive 30-tick battle simulation with base win/loss.

This is a checkpoint, not a claim of full Battle Cats battle compatibility. Exact abilities, KB state transitions, money/worker economy, restrictions/rewards and original sprite/model/animation playback remain later compatibility layers. Exact imported stage CSV data always outranks community reconstructions.