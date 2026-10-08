# Original Login / Gacha Runtime Anchors — JP 15.7.1

Anchor: exact JP 15.7.1 ARM64 `libnative-lib.so`  
SHA-256: `333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2`  
GNU build ID: `8cb3815648eb9642da10bfb039d71bff7a3519bd`

Machine-readable companion:
`original-login-gacha-runtime-anchors-jp15.7.1.json`.

## Why this matters

The project no longer needs to guess whether the original binary has a usable
login/gacha presentation path. Exact JP 15.7.1 contains direct anchors for:

- the daily-login data loaders;
- localized daily-login text;
- original login background resources;
- comeback-specific stamp resources;
- the Rare Gacha data-set loaders and option table.

This strengthens the preservation-first target: **feed/steer the original
systems rather than recreating their screens**.

## Exact login anchors

| Original string | String VA | ADRP | ADD |
| --- | ---: | ---: | ---: |
| `DailyLoginEventData.csv` | `0x1a2698` | `0x9c3424` | `0x9c3428` |
| `DailyLoginEventGrade.json` | `0x18f84a` | `0x5f70c4` | `0x5f70c8` |
| `StampData.csv` | `0x1aec53` | `0x9c5758` | `0x9c575c` |
| `DailyLoginEventText_%03d_%@.tsv` | `0x196788` | `0x5442cc` | `0x5442d0` |
| `loginbg_%03d.png` | `0x1ad6cd` | `0x548190` | `0x548194` |
| `loginbg.imgcut` | `0x1a5303` | `0x5481f0` | `0x5481f4` |
| `comeback_push_01` | `0x18f9af` | `0x73a9cc` | `0x73a9d0` |
| `comeback_stamp_push%02d` | `0x197b2c` | `0x73aec8` | `0x73aecc` |

The binary also contains RTTI/type-name strings naming lambdas inside
`MyApplication::DailyLoginUpdate`, plus `DailyLoginTextureContext`.

A normal-prologue code region beginning around `0x73a934` consumes both
`comeback_push_01` and `comeback_stamp_push%02d`. That gives Phase C a
strong original-scene observation target.

It is **not** yet declared a shipping hook. Runtime evidence still has to show
template selection, current stamp state, confirmation and reward settlement.

## Exact original comeback data

The separate exact-data audit identifies `DailyLoginEventData.csv` event
**949** as the seven-day comeback template.

That means the product plan no longer requires a custom reward table or custom
stamp art. The fallback can reuse original data and original presentation.

The native provider only stores the semantic decision:

- template = 949;
- cycle length = 7;
- feature OFF -> return original template unchanged.

Actual reward values remain in the Battle Cats data row.

## Current server-image corroboration

The project server-manifest index also contains:

`source=current-x / family=XImageServer / loginbg_019.png`

Event 949's header selects background id 19. This supports keeping the original
asset path. It does not change the provenance rule: an exact imported image
payload must exist locally before a shipping offline build claims full visual
availability.

## Exact gacha loader anchors

| Original string | String VA | ADRP | ADD |
| --- | ---: | ---: | ---: |
| `EventGatya_Setting.csv` | `0x1ac5c7` | `0x57bd80` | `0x57bd84` |
| `GatyaData_Option_ChanceAnimation.tsv` | `0x1935f5` | `0x5ec5c0` | `0x5ec5c4` |
| `GatyaDataSet%@1.csv` | `0x19469b` | `0x5ed6bc` | `0x5ed6c0` |
| `GatyaDataSet%@2.csv` | `0x1a136b` | `0x5ed8a8` | `0x5ed8ac` |
| `GatyaDataSet%@3.csv` | `0x1ac70d` | `0x5ed9ac` | `0x5ed9b0` |
| `GatyaData_Option_Set%s.tsv` | `0x19b1e3` | `0x5edab4` | `0x5edab8` |

A routine with a normal prologue at approximately `0x5ed65c` references R1,
R2, R3 and then the option table in order.

That control flow matches Battle Cats Complete's independently reconstructed
`load_gatya_data_set_csv`:

1. load set lane 1;
2. augment lane 2;
3. augment lane 3;
4. apply option rows.

This is strong support for **data-first Super Kneekura Gacha**.

The first product experiment should therefore be a tiny original-format test
set consumed by the original gacha UI, not a custom gacha screen and not an
early draw-function hook.

## Reproducibility

`tools/base_mod/arm64_string_xrefs.py` reproduces these simple exact
`ADRP + ADD` string references without Capstone/LIEF.

It intentionally recognizes only this narrow address materialization pattern.
A missing xref is not proof that a string has no callers; it means a different
instruction pattern needs a separate audited decoder.

## Promotion gate

Neither login nor gacha is connected to original runtime decisions yet.

The next acceptable runtime milestone remains:

> one Kneekura behavior is observed inside an unchanged original Battle Cats
> scene, and disabling one feature gate returns that path to original behavior.
