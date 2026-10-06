# Super Kneekura Data-Only Prototype — JP 15.7.1

Status: **structurally validated only**. Not installed or promoted to product.

The project can now produce a new original-format Rare Gacha set without
replacing any existing set.

## Exact test

From the anchored JP 15.7.1 local files:

- R1 rows: 1089
- R2 rows: 1089
- R3 rows: 1089
- option table: one header + 1089 rows

Therefore the first append-only set id is **1089**.

A tiny structural test was generated with:

- clone option metadata from set 0;
- `BannerON_OFF = 1` in the appended option row;
- unit ids 30, 31, 32;
- all three ids already occur in exact original local R1 data;
- all three are Super Rare in exact `unitbuy.csv`;
- R2/R3 remain empty.

Appended lines:

```text
GatyaDataSetR1.csv:
30,31,32,-1

GatyaDataSetR2.csv:
-1

GatyaDataSetR3.csv:
-1

GatyaData_Option_SetR.tsv:
1089    1    21    0    0    0    1    -1    0    -1
```

The machine-readable companion records exact output sizes and SHA-256 values.

## What this proves

- JP 15.7.1 R1/R2/R3/option tables are row-aligned.
- One new set can be appended without overwriting existing rows.
- The new option id can match the new dataset row index.
- A tiny pool can be restricted to ids already used by original local R1 sets.
- The data mutation can be produced independently from the APK patch/sign layer.

## What this does not prove

It does **not** prove that set 1089 is visible in the original gacha screen.

No exact event/schedule source currently points to the new set.

It also does not prove:

- original Rare Capsule rarity rates;
- single/11-draw result logic;
- duplicate/storage behavior;
- Cat Food transaction behavior;
- save settlement.

Those remain Phase-C runtime gates.

## New data patch pipeline

The repository now contains:

- `tools/base_mod/battlecats_pack_writer.py`
  - deterministic pack rebuild;
  - unchanged encrypted chunks copied byte-for-byte;
  - only explicit decrypted entries re-encrypted;
  - post-rebuild payload-hash verification.
- `tools/base_mod/patch_installpack_data.py`
  - changes only `assets/DataLocal.list` and `assets/DataLocal.pack`
    inside `split_InstallPack.apk`;
  - all other split payloads remain outside this data mutation stage.
- `tools/base_mod/super_gacha_data_prototype.py`
  - append-only test-set generator;
  - refuses unproven local-R1 ids;
  - refuses explicit test/cheat unit 673;
  - refuses silent duplicate weighting;
  - intentionally does not define rarity rates or event visibility.

This is the first real product-oriented path that can extend original Battle
Cats data while keeping the original UI/runtime as the host.

The next step is still conservative: expose this only through the isolated
research package after the original event/gacha lifecycle is observed.
