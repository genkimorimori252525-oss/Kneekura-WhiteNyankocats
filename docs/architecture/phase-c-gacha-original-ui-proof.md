# Phase C — Original-UI Tiny Super Kneekura Gacha Proof

Status: static/data implementation in progress for exact JP 15.7.1.

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

## Four-file mutation surface

Only these decrypted DataLocal entries may change:

- `GatyaDataSetR1.csv`
- `GatyaDataSetR2.csv`
- `GatyaDataSetR3.csv`
- `GatyaData_Option_SetR.tsv`

For the appended set:

- R1 contains the three tiny proof unit ids plus `-1`;
- R2 is `-1`;
- R3 is `-1`;
- the option row is cloned from an original BannerON row with id changed to
  1089.

All existing rows are byte-for-byte preserved at the decrypted payload level.
The DataLocal pack writer also verifies all untouched DataLocal entries retain
their original decrypted payload hashes.

## Build path

`tools/base_mod/build_owned_gacha_ui_proof.py` composes:

1. exact owned JP 15.7.1 split extraction;
2. deterministic tiny set generation;
3. DataLocal-only InstallPack rewrite;
4. inert Kneekura shim bootstrap;
5. isolated package flavor;
6. Frida-free static MyActivity bridge;
7. normal Android alignment/signing;
8. static HTTP preservation audit;
9. final encrypted DataLocal row verification.

The final data verifier is:

`tools/base_mod/verify_gacha_ui_data_proof.py`

It decrypts the original and final DataLocal containers and proves:

- original R1/R2/R3/option rows are unchanged;
- exactly one row is appended to each table;
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
