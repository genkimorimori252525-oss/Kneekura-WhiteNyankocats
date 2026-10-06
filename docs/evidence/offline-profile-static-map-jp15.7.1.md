# Offline profile static map — exact JP 15.7.1

Status: exact-version static evidence, 2026-10-07.

## Source anchor

This report was rebuilt directly from the owned Android export whose SHA-256 is
`38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`.

Pinned native:

- `lib/arm64-v8a/libnative-lib.so`
- SHA-256 `333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2`

Pinned built-in local data:

- `DataLocal.list` SHA-256
  `1cce55c9c9b8aaf454128d8448101fe1ed9f99931d646fa389fed5c934246a27`
- `DataLocal.pack` SHA-256
  `884d6910dc8e963768bb8ec60b0cd54c122e75cbf75c51dd44df69e7f960b3b8`

No DataLocal mutation is proposed by this save-profile phase.

## Exact playable-unit candidate boundary

The exact decrypted tables show:

- `unitbuy.csv`: 882 rows;
- `nyankoPictureBookData.csv`: 882 rows;
- Cat Guide display flag nonzero: **835 rows**;
- Cat Guide display flag zero: **47 rows**;
- highest row id: 881;
- highest `unitbuy.csv` game-version field: 150700.

This proves that a simple `for id in 0..881: unlocked=1` bootstrap is invalid.
The data itself contains hidden/non-guide rows. Known research/test id 673 is
among the 47 hidden rows.

The first ownership set will therefore be derived from exact game data, with the
835 guide-visible rows as the initial candidate set and asset completeness /
other structural checks layered on top.

The exact hidden IDs are recorded in
`offline-profile-static-map-jp15.7.1.json`.

## First-form ownership semantics

Community prior art indicates that a cat record has separate ownership, gacha
visibility, form, level, guide and talent state. The exact data corroborates why
form handling must remain independent: picture-book rows advertise 1, 2, 3 or 4
forms and `unitbuy.csv` carries separate true/fourth-form metadata.

Therefore the requested first-form bootstrap must not be implemented by maxing
the whole cat record. Initial intended semantics remain:

- own/unlock the eligible unit;
- make it visible to the original unit UI as required;
- current form = first form;
- do not force true/fourth form;
- do not max talents by accident.

The exact SAVE_DATA field order will be verified from an actual research-package
save before mutation.

## Material table evidence

Exact `Matatabi.tsv` has 29 material rows in this build. The referenced gacha
item ids are:

`30..44, 160, 161, 164, 167..171, 179..184`

This gives a version-pinned material enumeration source. It is safer than
assuming that the old five-color catfruit list still describes all evolution
materials in 15.7.1.

## SAVE_DATA family anchors in the exact native binary

Dependency-free AArch64 ADRP+ADD xref scanning found the following exact sites:

- `SAVE_DATA`: 0x71c984, 0x74b13c, 0x8b43d0, 0x8b9fdc, 0x8c5334
- `SAVE_DATA4`: 0x7edd54, 0x8ba0b0, 0x8c1d30
- `SAVE_DATA8`: 0x748e00, 0x74ad74, 0x74af48
- `BACKUP_SAVE_DATA`: 0x70c9c0, 0x737e88

The `SAVE_DATA` references at 0x8b9fdc and 0x8c5334 feed the same internal
routine at 0x8b46b0, strongly identifying a central file-operation seam.
This is a better target for static understanding than attaching a permanent
runtime currency hook.

Other exact resource/save anchors:

- `catfoodAmount`: 0x73e5c4
- `rareTicketAmount`: 0x73e61c
- `platinumTicketAmount`: 0x73e66c
- `legendTicketAmount`: 0x73e6c8
- `potential_exchange_np`: 0x819630 / 0x8196e4
- `potential_exchange_np_set`: 0x81aba4 / 0x81ac3c
- `setNekokan(%d,%f)`: 0x7619d0
- `setItem(%d, %d)`: 0x7693c0
- `getSavedRegister`: 0xad5ae8
- `getSavedFloatRegister`: 0xad4bf8
- `BcResLeadership`: 0x94257c
- `Matatabi.tsv`: 0x9bbea0

These xrefs prove that the exact binary carries the expected persistence and
resource concepts, but a string xref alone is not treated as a field offset.

## Exact XP cap proven from native code

The XP candidate from BCSFE is independently confirmed in JP 15.7.1.

At 0x4d7060-0x4d7080 the binary constructs:

- `0x05F5E0FE` = 99,999,998 for comparison;
- when the current value exceeds it, writes
  `0x05F5E0FF` = **99,999,999**.

Therefore XP = 99,999,999 is promoted from community hypothesis to
**exact-native-confirmed cap**.

## Other maximum constants

The exact native binary also contains repeated game-code clamps/constants for:

- 998 (`0x3e6`);
- 9,999 (`0x270f`);
- 299 (`0x12b`).

The 998 sites around 0x5936d8 and related material/item paths are consistent
with BCSFE's modern catfruit maximum, and 9,999 is consistent with several
item-like resource classes. However, until each site is bound to the exact
SAVE_DATA field, these values remain candidates rather than a blanket
all-material rule.

This distinction matters: a numeric constant can be reused by unrelated systems.

## Research-package storage seam

The promoted research bridge has an explicit research-only override:

`MyActivity.getFilesDir() -> super.getExternalFilesDir(null)`

when `use_external_files_dir` is enabled. Personal and Practice do not enable
it.

On normal Android storage semantics this gives the research package an
app-specific external `files` directory, allowing the next device probe to
retrieve the real research `SAVE_DATA` without root.

The next mutation step must still discover the actual resolved path from the
device rather than assuming a path string.

## What is intentionally not yet claimed

We do **not** yet claim exact save offsets for:

- Cat Food;
- tickets;
- NP;
- Leadership;
- catseyes;
- all 29 evolution-material counts;
- battle items;
- cat ownership/form arrays.

Those require one real JP 15.7.1 research SAVE_DATA sample and a lossless
round-trip test. The private original app data was unavailable in the initial
ADB export, so inventing offsets now would defeat the preservation-first
contract.

## Next gate

Before any max-value mutation, the device runner should:

1. ask Android for the research package's actual external files directory;
2. locate `SAVE_DATA` / backup variants;
3. pull an immutable baseline copy;
4. record size + SHA-256 + sibling file inventory;
5. make a second backup copy dedicated to rollback;
6. only then test a parser round-trip with **zero semantic edits**.

If the round-trip is not lossless/accepted by the original app, the bootstrap
must stop before resource edits.
