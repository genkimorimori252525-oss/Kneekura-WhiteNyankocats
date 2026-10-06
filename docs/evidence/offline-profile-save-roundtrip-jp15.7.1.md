# Exact JP 15.7.1 SAVE_DATA round-trip and offline MAX candidate proof

Status: **parser/layout proof complete; device mutation not yet performed.**

## Exact device baseline

The research package produced a real `SAVE_DATA` of 496,340 bytes.

- SHA-256: `cad00e84f3d64910b623b8a89b57ae1a37e8947554f4b418f50efa1c6bdc1d3c`
- SAVE_DATA game version: `150700`
- JP salted-MD5 trailer: `3552ae85c3fde366d413360d27fdb76e`
- `MD5(b"battlecats" + payload)` matches the stored trailer exactly.

The uploaded rollback copy is byte-identical to the baseline.

## Full parser round-trip

Pinned BCSFE-Python 3.6.0 commit
`85fb94cbf00c6a74dbef58932610fb94ec8f7495` was used only as a disposable
research oracle. Its GPL implementation is not copied into Kneekura runtime
code.

The exact JP 15.7.1 baseline:

1. parses completely;
2. leaves 332 bytes in the parser's explicit forward-compatible
   `remaining_data` field;
3. serializes back to **exactly the original 496,340 bytes**;
4. produces zero differing bytes and the exact original SHA-256.

This upgrades the SAVE_DATA work from inferred structure to a lossless,
exact-baseline parser contract.

## Differential field binding

One field at a time was changed through the pinned parser and serialized.
The resulting byte differences were used to bind exact offsets. The field map
is stored in
`docs/evidence/offline-profile-save-roundtrip-jp15.7.1.json`.

Notable corrections found during this audit:

- `cat_unlocked_forms` count is at 310,318 and cat 0 starts at 310,322;
- the exact 15.7.1 `lucky_tickets` array contains **55**, not 54, entries.

Both corrections are now reflected in the independent transformer.

## First-form all-unit contract

The exact DataLocal selection remains:

- 835 guide-visible, roster-playable JP 15.7.1 units;
- 47 hidden/internal/test/regional rows excluded;
- asset residuals 673, 740 and 788 remain excluded;
- 255 `unit_drops` save IDs are enabled from exact
  `drop_chara.csv` mapping.

For those 835 units the candidate sets only ownership visibility:

- owned = 1;
- `gatya_seen` = 1;
- current form = 0;
- unlocked forms = 0;
- fourth form = 0.

Levels, talents and later forms are not force-maxed.

## Minimal tutorial escape

The candidate reproduces the current editor's minimal tutorial clear rather
than clearing the whole story. The independent differential confirms only the
tutorial/UI fields and first EoC stage/progress are changed.

## Offline MAX candidate

A candidate was first built through the pinned parser, then independently
rebuilt from the exact offsets without importing BCSFE. The two outputs are
**byte-for-byte identical**.

Candidate identity:

- size: 496,340 bytes;
- SHA-256:
  `afa5ee976a85d0640244393ba8326c21a5ef5b4378228fbf85e172e28c7beb18`;
- JP salted-MD5:
  `c5de35c24bb635cf1a312da0d6139120`;
- parser re-read: PASS;
- candidate parser reserialization: byte-identical PASS.

The exact-independent implementation is
`tools/base_mod/build_offline_max_save.py`.

## Resource cap boundary

XP = **99,999,999** remains the only value in this set that has already been
bound to an exact native clamp.

The other values are current BCSFE/community editor policy caps that are
storage-width-safe and parser-safe in this exact save. In particular Cat Food
45,000 is **not** claimed to be an exact native local cap.

That distinction remains in the generated report so future native-cap evidence
can revise one resource without changing SAVE_DATA layout work.

## Preservation gate

No candidate bytes have been pushed to the Android device yet.

The first mutating device run must:

1. force-stop only the isolated research package;
2. pull and hash the current remote SAVE_DATA;
3. abort if it is not the exact approved baseline;
4. retain an independent local rollback copy;
5. stage the candidate under a temporary remote name before replacement;
6. pull the installed candidate back and verify its SHA-256;
7. launch the original scene;
8. rollback automatically/manual-trigger if the original UI rejects the save.

Live-account/server synchronization is out of scope for this lane; the first
MAX-profile runtime proof should be performed with network connectivity disabled.
