# Phase C — Original-UI Tiny Super Kneekura Gacha Proof

Status: deferred after static/data proof for exact JP 15.7.1.

Runtime Rare Gacha visibility work is intentionally postponed as of 2026-10-07.
The project now prioritizes a durable offline local profile bootstrap (all owned
units + capped progression currencies/materials) so future runtime verification
does not depend on repeating the tutorial or losing local test state.

## Goal

Prove the first Kneekura content change through the **original Battle Cats Rare
Gacha data path** without replacing the gacha, capsule, result, acquisition, or
save scenes.

The first proof is intentionally tiny. It appends one original-format Rare Gacha
set and reuses original banner metadata. It does not yet claim that a server
schedule will select the new set at runtime.

## Exact JP 15.7.1 anchor

The exact native binary already pins the Rare Gacha dataset loader region at:

`0x5ed65c`

with ordered original string references for:

- `GatyaDataSet%@1.csv`
- `GatyaDataSet%@2.csv`
- `GatyaDataSet%@3.csv`
- `GatyaData_Option_Set%s.tsv`

The exact local JP data has 1089 R-set rows, so the append-only proof set id is:

`1089`

No original set id is replaced.

## Independent parser corroboration

Battle Cats Complete commit
`5a5096c8fa75f837d3e9a314e8fd4ce4813ec811` independently reconstructs the
same data path:

- `emu/src/engine/load_gatya_data_set_csv.rs` loads R1 first, then aligns R2,
  R3, and the option table by row/set index;
- `emu/src/engine/parse_gatya_option_row.rs` maps option column 1 directly to
  `banner_on`;
- `emu/src/engine/load_gacha_setting_csv.rs` treats
  `EventGatya_Setting.csv` as a separate event-gacha mapping.

This corroborates the preservation design, but the exact JP binary remains the
authority for the product patch.

## Deterministic tiny pool

`tools/base_mod/super_gacha_data_prototype.py` can now derive the proof pool
directly from the exact owned export.

Selection policy:

1. unit id must already appear in the exact local R1 union;
2. rarity must be Rare, Super Rare, Uber Rare, or Legend Rare;
3. explicit test/cheat id 673 is rejected;
4. duplicates are rejected;
5. for the three-unit proof, choose the lowest deterministic id from Rare,
   Super Rare, and Uber Rare when available.

This avoids hard-coding guessed unit ids into the selection algorithm while
keeping the build reproducible from the exact JP 15.7.1 export.

### Exact owned-export derivation

Running that deterministic selection against the anchored owned export yields:

- Rare: unit **37**
- Super Rare: unit **30**
- Uber Rare: unit **34**
- first existing BannerON clone row: set **49**

The shipping-oriented proof builder pins these derived values as exact-version
postconditions. A change in the derivation fails closed instead of silently
producing a different test pool.

## Banner metadata

The proof does not invent new gacha art or UI metadata.

The builder scans the exact original option table and selects the first
well-formed existing row whose `BannerON_OFF` value is nonzero. Set 1089 clones
that row, changes only the set id, and explicitly keeps BannerON at 1.

Therefore the appended row is structurally compatible with the original Rare
Gacha parser and reuses an already proven original banner configuration.

## Four-file DownloadLocal overlay surface

The first device attempt proved that rewriting built-in `DataLocal.list/.pack`
is not acceptable for this runtime proof: after the original 615.69 MiB server
bootstrap completed, the game stopped on H01.

The H01-safe build therefore leaves both built-in DataLocal container files
**byte-identical** to the exact JP 15.7.1 source.

Only these four override files are appended to the existing DownloadLocal
overlay:

- `GatyaDataSetR1.csv`
- `GatyaDataSetR2.csv`
- `GatyaDataSetR3.csv`
- `GatyaData_Option_SetR.tsv`

Each overlay file contains the exact original table plus one appended set:

- R1 contains the three tiny proof unit ids plus `-1`;
- R2 is `-1`;
- R3 is `-1`;
- the option row is cloned from original BannerON set 49 with id changed to
  1089.

Every original DownloadLocal entry is also preserved.

## Build path

`tools/base_mod/build_owned_gacha_ui_proof.py` composes:

1. exact owned JP 15.7.1 split extraction;
2. deterministic tiny set generation;
3. append-only DownloadLocal overlay injection while DataLocal remains byte-identical;
4. inert Kneekura shim bootstrap;
5. isolated package flavor;
6. Frida-free static MyActivity bridge;
7. normal Android alignment/signing;
8. static HTTP preservation audit;
9. final encrypted DataLocal row verification.

The final data verifier is:

`tools/base_mod/verify_gacha_ui_data_proof.py`

It compares the original DataLocal tables against the final DownloadLocal
overrides and proves:

- original DataLocal.list/DataLocal.pack are byte-identical;
- all original DownloadLocal payloads are preserved;
- each override retains every original R1/R2/R3/option row;
- exactly one row is appended to each override table;
- set id is 1089;
- R1 pool equals the deterministic proof pool;
- R2/R3 are empty;
- BannerON is 1;
- every option field after the set id matches the selected original visible row.

## Scene preservation

The proof modifies no original gacha/capsule/result Java or native scene code.

The only Java runtime addition remains the already-promoted flavor
`MyActivity` subclass for the selective HTTP seam. Unknown HTTP requests still
fall through to the exact original `super.newHttpRequest`.

Therefore any gacha presentation or result flow reached by this data remains
owned by the original Battle Cats runtime.

## Hard boundary: schedule and draw rates

Two things remain intentionally unresolved:

**Visibility schedule.** A BannerON-compatible set row is necessary data, but it
is not proof that the original live/server event schedule will select set 1089.
No fake schedule is invented in this static proof.

**Rarity probability vector.** Exact local files still do not prove the live
Rare Capsule probability vector. The proof therefore defines no new rate vector.

Those are runtime/provider gates, not reasons to replace the original UI.

## Promotion criterion

This step's static/data contract is ready when:

- exact set 1089 is produced from the owned export;
- the four-file mutation surface is enforced;
- final encrypted DataLocal data passes append-only verification;
- original scene code remains untouched;
- Frida is absent;
- CI regression tests remain green.

The following runtime proof can then ask only one question: does the original
Rare Gacha scene select/display set 1089, or do we need a narrow local schedule
provider on top of the already-promoted HTTP seam?


## Runtime gate discovered: original server assets

The first owner-device set-1089 run did **not** reach the Rare Gacha scene. It
stopped at the original additional-game-data screen.

The exact JP 15.7.1 `download_0.tsv` through `download_34.tsv` archive sizes
sum to **645,599,537 bytes = 615.691697 MiB**, matching that screen. The fresh
owned export also has no preseeded files under the app's `files/` directory.

Therefore `appended_banner_visible=false` from that run is not evidence that
the gacha schedule omitted set 1089. The UI had not yet reached the point where
banner visibility could be evaluated.

The isolated research gacha proof now enables a research-only storage adapter:

```text
MyActivity.getFilesDir()
    -> app-specific external files directory
```

This does not replace the downloader. The unchanged original Battle Cats
downloader remains responsible for the one-time server-asset bootstrap. The
adapter exists only so the research package's downloaded cache is accessible
without root and survives normal same-signature `adb install -r` retries.

Personal MAX and Practice Clean never enable this storage adapter.


## H01 integrity decision

The project does not disable the native pack/list checksum path.

Historical Battle Cats modding tooling associates H01 with modified pack/list
integrity checks, while Battle Cats Complete's modern APK exporter places packed
mod files in the existing `DownloadLocal` family. The runtime proof therefore
adopts the overlay strategy instead of a native checksum bypass.

Hard rule for this proof:

- `DataLocal.list`: exact source bytes;
- `DataLocal.pack`: exact source bytes;
- `DownloadLocal.list/.pack`: only the four gacha override additions;
- native MD5 bypass: **forbidden**.

This keeps H01 useful as an integrity signal rather than suppressing it.
